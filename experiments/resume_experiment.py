"""
Resume Cultural Alignment Experiment — Completes missing levels from a partial run.

Reads an existing experiment JSON, identifies levels with all-error data,
and re-runs only those levels against the live endpoint.

Usage:
  python -m experiments.resume_experiment \
    experiments/results/experiment_20260412_111630.json \
    --endpoint https://<your-ngrok>.ngrok-free.dev/generate
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

from experiments.cultural_signal_detector import detect_cultural_signal
from experiments.cultural_alignment_experiment import (
    call_api,
    load_prompts,
    _token_entropy,
    RESULTS_DIR,
)


def resume_experiment(
    partial_path: Path,
    *,
    endpoint: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_new_tokens: int = 128,
) -> dict[str, Any]:
    """
    Load partial experiment, re-run levels that have 0 valid results.
    """
    data = json.loads(partial_path.read_text(encoding="utf-8"))
    prompts_by_level = load_prompts()
    repetitions = data["metadata"]["repetitions_per_prompt"]

    # Identify which levels need re-running
    levels_to_rerun = []
    for level_name, level_data in data["levels"].items():
        valid = [r for r in level_data["runs"] if not r.get("error")]
        if len(valid) == 0:
            levels_to_rerun.append(level_name)
            print(f"  🔄 Level '{level_name}' has 0 valid results — will re-run")
        else:
            print(f"  ✅ Level '{level_name}' has {len(valid)} valid results — keeping")

    if not levels_to_rerun:
        print("\n  All levels have valid data. Nothing to resume.")
        return data

    # Connectivity check
    print(f"\n  Checking backend connectivity... ", end="")
    try:
        test_resp = requests.post(
            endpoint,
            json={"prompt": "Hello, how are you?", "max_new_tokens": 16, "temperature": 0.0},
            timeout=60,
            headers={"ngrok-skip-browser-warning": "true"},
        )
        if test_resp.status_code < 500:
            print(f"✅ Connected (status {test_resp.status_code})")
        else:
            print(f"⚠ Status {test_resp.status_code} — proceeding anyway")
    except Exception as e:
        print(f"❌ Failed: {e}")
        print("\n  Backend must be running. Start it and retry.")
        sys.exit(1)

    # Re-run missing levels
    total_rerun = sum(
        len(prompts_by_level.get(ln, [])) * repetitions
        for ln in levels_to_rerun
    )
    call_counter = 0

    for level_name in levels_to_rerun:
        prompts = prompts_by_level.get(level_name, [])
        print(f"\n{'═' * 60}")
        print(f"  RE-RUNNING: {level_name.upper()} ({len(prompts)} prompts × {repetitions} reps)")
        print(f"{'═' * 60}")

        level_results: list[dict] = []

        for prompt_idx, prompt in enumerate(prompts):
            for rep in range(repetitions):
                call_counter += 1
                progress = f"[{call_counter}/{total_rerun}]"
                prompt_short = prompt[:50] + "..." if len(prompt) > 50 else prompt
                print(f"  {progress} {level_name}:{prompt_idx}:r{rep} — {prompt_short}")

                api_result = call_api(
                    endpoint,
                    prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_new_tokens=max_new_tokens,
                )

                response_text = api_result.get("response_text", "")
                error = api_result.get("error")

                signal = detect_cultural_signal(response_text)
                entropy = _token_entropy(response_text)

                run_record = {
                    "prompt_index": prompt_idx,
                    "prompt": prompt,
                    "repetition": rep,
                    "response_text": response_text,
                    "error": error,
                    "measured_latency_ms": api_result.get("measured_latency_ms", 0),
                    "cultural_signal": signal.to_dict(),
                    "token_entropy": round(entropy, 4),
                }

                level_results.append(run_record)

                if error:
                    print(f"         ⚠ Error: {error}")
                else:
                    status = "🟢" if signal.has_cultural_signal else "⚪"
                    print(f"         {status} score={signal.score:.3f}  entropy={entropy:.3f}")

        # Compute aggregate for this level
        valid_results = [r for r in level_results if not r.get("error")]
        cultural_scores = [r["cultural_signal"]["score"] for r in valid_results]
        has_signal_count = sum(1 for r in valid_results if r["cultural_signal"]["has_cultural_signal"])
        entropies = [r["token_entropy"] for r in valid_results]

        n = len(valid_results)
        aggregate = {
            "n": n,
            "errors": len(level_results) - n,
            "P_cultural": round(has_signal_count / n, 4) if n > 0 else 0.0,
            "mean_cultural_score": round(statistics.mean(cultural_scores), 4) if cultural_scores else 0.0,
            "std_cultural_score": round(statistics.stdev(cultural_scores), 4) if len(cultural_scores) >= 2 else 0.0,
            "mean_entropy": round(statistics.mean(entropies), 4) if entropies else 0.0,
            "std_entropy": round(statistics.stdev(entropies), 4) if len(entropies) >= 2 else 0.0,
        }

        print(f"\n  ── {level_name.upper()} Summary ──")
        print(f"     n={aggregate['n']}  P(cultural)={aggregate['P_cultural']:.2f}  "
              f"mean_score={aggregate['mean_cultural_score']:.3f}  "
              f"mean_entropy={aggregate['mean_entropy']:.3f}")

        # Replace the level data in the experiment
        data["levels"][level_name] = {
            "aggregate": aggregate,
            "runs": level_results,
        }

    # Recompute cross-level summary
    print(f"\n{'═' * 60}")
    print("  CROSS-LEVEL SUMMARY (MERGED)")
    print(f"{'═' * 60}")

    cross_summary = {}
    for level_name, level_data in data["levels"].items():
        agg = level_data["aggregate"]
        cross_summary[level_name] = {
            "P_cultural": agg["P_cultural"],
            "mean_score": agg["mean_cultural_score"],
            "mean_entropy": agg["mean_entropy"],
        }
        print(f"  {level_name:>15}: P(cultural)={agg['P_cultural']:.2f}  "
              f"score={agg['mean_cultural_score']:.3f}  "
              f"entropy={agg['mean_entropy']:.3f}")

    # ΔP calculations
    neutral_p = cross_summary.get("neutral", {}).get("P_cultural", 0.0)
    deltas = {}
    for lname in ["weak_india", "strong_india"]:
        level_p = cross_summary.get(lname, {}).get("P_cultural", 0.0)
        dp = round(level_p - neutral_p, 4)
        deltas[f"ΔP_{lname}_vs_neutral"] = dp
        print(f"  ΔP({lname} − neutral) = {dp:+.4f}")

    # Collapse ratios
    ref_entropy = math.log2(200)
    collapse_ratios = {}
    for level_name, level_data in data["levels"].items():
        mean_e = level_data["aggregate"]["mean_entropy"]
        ratio = round(1.0 - (mean_e / ref_entropy), 4) if ref_entropy > 0 and mean_e > 0 else 0.0
        collapse_ratios[level_name] = ratio
    print(f"\n  Collapse ratios (1 = full collapse, 0 = max entropy):")
    for level_name, ratio in collapse_ratios.items():
        print(f"    {level_name:>15}: {ratio:.4f}")

    data["cross_summary"] = {
        "per_level": cross_summary,
        "deltas": deltas,
        "collapse_ratios": collapse_ratios,
    }

    data["metadata"]["resumed_at"] = datetime.utcnow().isoformat() + "Z"
    data["metadata"]["resumed_levels"] = levels_to_rerun

    return data


def main():
    parser = argparse.ArgumentParser(description="Resume a partial experiment run")
    parser.add_argument("input_file", help="Path to partial experiment JSON")
    parser.add_argument("--endpoint", required=True, help="Backend API endpoint")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--output", default=None, help="Output path (default: overwrites input + saves timestamped copy)")
    args = parser.parse_args()

    if requests is None:
        print("❌ Error: 'requests' library is required.")
        sys.exit(1)

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        sys.exit(1)

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  CULTURAL ALIGNMENT EXPERIMENT — RESUME MODE           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Resuming from: {input_path}")
    print(f"  Endpoint:      {args.endpoint}")

    start_time = time.perf_counter()
    experiment = resume_experiment(
        input_path,
        endpoint=args.endpoint,
        max_new_tokens=args.max_tokens,
    )
    elapsed = time.perf_counter() - start_time
    experiment["metadata"]["resume_runtime_seconds"] = round(elapsed, 2)
    print(f"\n  ⏱ Resume runtime: {elapsed:.1f}s")

    # Save merged results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_path = RESULTS_DIR / f"experiment_merged_{timestamp}.json"
    merged_path.write_text(
        json.dumps(experiment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n  📁 Merged results saved to: {merged_path}")
    print(f"\n  Next: python -m experiments.analyze_experiment {merged_path}")
    print()


if __name__ == "__main__":
    main()
