"""
Cultural Alignment Experiment — Runner (Experiments 2.1 + 2.2)

Measures how inference-time policies reshape output distributions
across a 3-tier cultural prompt gradient:

  Level 0: Neutral (no cultural cue)
  Level 1: Weak India (subtle Hinglish / India references)
  Level 2: Strong India (explicit Devanagari / deep cultural context)

For each prompt:
  - Sends to backend API endpoint
  - Captures the response (which includes full runtime pipeline)
  - Applies cultural signal detector
  - Records raw data for post-hoc analysis

Usage:
  python -m experiments.cultural_alignment_experiment
  python -m experiments.cultural_alignment_experiment --endpoint http://localhost:8000/generate
  python -m experiments.cultural_alignment_experiment --dry-run
"""

from __future__ import annotations

import argparse
import json
import time
import sys
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

# Local imports — works when run as `python -m experiments.cultural_alignment_experiment`
from experiments.cultural_signal_detector import detect_cultural_signal, CulturalSignal


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PROMPTS_PATH = Path(__file__).parent / "cultural_prompts.json"
RESULTS_DIR = Path(__file__).parent / "results"

DEFAULT_ENDPOINT = "http://localhost:8000/generate"
REQUEST_TIMEOUT = 180


# ─────────────────────────────────────────────────────────────────────────────
# Prompt loading
# ─────────────────────────────────────────────────────────────────────────────

def load_prompts(path: Path | None = None) -> dict[str, list[str]]:
    """Load 3-tier prompt bank from JSON."""
    path = path or PROMPTS_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    levels = data["levels"]
    return {
        level_name: level_data["prompts"]
        for level_name, level_data in levels.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# API caller
# ─────────────────────────────────────────────────────────────────────────────

def call_api(
    endpoint: str,
    prompt: str,
    *,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_new_tokens: int = 512,
    mode: str = "",
) -> dict[str, Any]:
    """
    Call the backend API and return the response dict.
    Returns {"response_text": ..., "latency_ms": ..., "error": ...} on failure.
    """
    if requests is None:
        return {"response_text": "", "error": "requests library not installed"}

    payload = {
        "prompt": prompt,
        "mode": mode,
        "temperature": temperature,
        "top_p": top_p,
        "max_new_tokens": max_new_tokens,
    }

    start = time.perf_counter()
    try:
        resp = requests.post(
            endpoint,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={"ngrok-skip-browser-warning": "true"},
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        data["measured_latency_ms"] = elapsed_ms
        return data
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "response_text": "",
            "error": str(e),
            "measured_latency_ms": elapsed_ms,
        }


def dry_run_api(prompt: str, **kwargs) -> dict[str, Any]:
    """Simulate API call for --dry-run mode."""
    # Return a plausible stub response for validation
    return {
        "response_text": f"[DRY RUN] Response to: {prompt[:50]}...",
        "latency_ms": 0,
        "measured_latency_ms": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Entropy computation (per-condition)
# ─────────────────────────────────────────────────────────────────────────────

def _token_entropy(text: str) -> float:
    """
    Shannon entropy of token distribution in a single response.
    Used to compute collapse_ratio per condition.
    """
    import re
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return 0.0
    freq: dict[str, int] = {}
    for tok in tokens:
        freq[tok] = freq.get(tok, 0) + 1
    total = len(tokens)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


# ─────────────────────────────────────────────────────────────────────────────
# Core experiment loop
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    repetitions: int = 3,
    dry_run: bool = False,
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_new_tokens: int = 512,
) -> dict[str, Any]:
    """
    Run the full 3-tier experiment.

    Returns a structured results dict with per-run detail and per-level aggregates.
    """
    prompts_by_level = load_prompts()
    api_fn = dry_run_api if dry_run else call_api

    experiment = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "endpoint": endpoint,
            "dry_run": dry_run,
            "repetitions_per_prompt": repetitions,
            "temperature": temperature,
            "top_p": top_p,
            "max_new_tokens": max_new_tokens,
        },
        "levels": {},
    }

    total_calls = sum(len(prompts) * repetitions for prompts in prompts_by_level.values())
    call_counter = 0

    for level_name, prompts in prompts_by_level.items():
        print(f"\n{'═' * 60}")
        print(f"  LEVEL: {level_name.upper()} ({len(prompts)} prompts × {repetitions} reps)")
        print(f"{'═' * 60}")

        level_results: list[dict] = []

        for prompt_idx, prompt in enumerate(prompts):
            for rep in range(repetitions):
                call_counter += 1
                progress = f"[{call_counter}/{total_calls}]"
                prompt_short = prompt[:50] + "..." if len(prompt) > 50 else prompt
                print(f"  {progress} {level_name}:{prompt_idx}:r{rep} — {prompt_short}")

                # ── Call API ──────────────────────────────────────────────
                api_result = api_fn(
                    endpoint,
                    prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_new_tokens=max_new_tokens,
                ) if not dry_run else dry_run_api(prompt)

                response_text = api_result.get("response_text", "")
                error = api_result.get("error")

                # ── Detect cultural signal ────────────────────────────────
                signal = detect_cultural_signal(response_text)

                # ── Compute token entropy ─────────────────────────────────
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

        # ── Per-level aggregates ──────────────────────────────────────────
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

        experiment["levels"][level_name] = {
            "aggregate": aggregate,
            "runs": level_results,
        }

    # ── Cross-level summary ───────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  CROSS-LEVEL SUMMARY")
    print(f"{'═' * 60}")

    cross_summary = {}
    for level_name, level_data in experiment["levels"].items():
        agg = level_data["aggregate"]
        cross_summary[level_name] = {
            "P_cultural": agg["P_cultural"],
            "mean_score": agg["mean_cultural_score"],
            "mean_entropy": agg["mean_entropy"],
        }
        print(f"  {level_name:>15}: P(cultural)={agg['P_cultural']:.2f}  "
              f"score={agg['mean_cultural_score']:.3f}  "
              f"entropy={agg['mean_entropy']:.3f}")

    # ── ΔP calculations ──────────────────────────────────────────────────
    neutral_p = cross_summary.get("neutral", {}).get("P_cultural", 0.0)
    deltas = {}
    for level_name in ["weak_india", "strong_india"]:
        level_p = cross_summary.get(level_name, {}).get("P_cultural", 0.0)
        dp = round(level_p - neutral_p, 4)
        deltas[f"ΔP_{level_name}_vs_neutral"] = dp
        print(f"  ΔP({level_name} − neutral) = {dp:+.4f}")

    # ── Collapse ratio per condition ──────────────────────────────────────
    # For each condition, compare mean entropy to a reference maximum entropy
    # (maximum entropy for an even distribution of typical vocab size ~200)
    ref_entropy = math.log2(200)  # ~7.64 bits
    collapse_ratios = {}
    for level_name, level_data in experiment["levels"].items():
        mean_e = level_data["aggregate"]["mean_entropy"]
        ratio = round(1.0 - (mean_e / ref_entropy), 4) if ref_entropy > 0 else 0.0
        collapse_ratios[level_name] = ratio
    print(f"\n  Collapse ratios (1 = full collapse, 0 = max entropy):")
    for level_name, ratio in collapse_ratios.items():
        print(f"    {level_name:>15}: {ratio:.4f}")

    experiment["cross_summary"] = {
        "per_level": cross_summary,
        "deltas": deltas,
        "collapse_ratios": collapse_ratios,
    }

    return experiment


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

def save_results(experiment: dict, output_dir: Path | None = None) -> Path:
    """Save experiment results to JSON file in results/ directory."""
    output_dir = output_dir or RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_{timestamp}.json"
    output_path = output_dir / filename

    output_path.write_text(
        json.dumps(experiment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n  📁 Results saved to: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run cultural alignment gradient experiment (2.1 + 2.2)",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"Backend API endpoint (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Repetitions per prompt (default: 3, total = prompts × reps)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Top-p nucleus sampling (default: 0.9)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max new tokens per response (default: 512)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate experiment setup without making API calls",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory (default: experiments/results/)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  CULTURAL ALIGNMENT EXPERIMENT — 3-Tier Prompt Gradient ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Endpoint:     {args.endpoint}")
    print(f"  Repetitions:  {args.repetitions}")
    print(f"  Temperature:  {args.temperature}")
    print(f"  Top-p:        {args.top_p}")
    print(f"  Max tokens:   {args.max_tokens}")
    print(f"  Dry run:      {args.dry_run}")

    if not args.dry_run and requests is None:
        print("\n❌ Error: 'requests' library is required. Install with: pip install requests")
        sys.exit(1)

    # ── Connectivity check (unless dry run) ───────────────────────────────
    if not args.dry_run:
        print(f"\n  Checking backend connectivity... ", end="")
        try:
            test_resp = requests.post(
                args.endpoint,
                json={"prompt": "ping", "max_new_tokens": 8, "temperature": 0.0},
                timeout=30,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            if test_resp.status_code < 500:
                print("✅ Connected")
            else:
                print(f"⚠ Status {test_resp.status_code}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            print("\n  Backend must be running. Start it and retry.")
            sys.exit(1)

    # ── Run experiment ────────────────────────────────────────────────────
    start_time = time.perf_counter()
    experiment = run_experiment(
        endpoint=args.endpoint,
        repetitions=args.repetitions,
        dry_run=args.dry_run,
        temperature=args.temperature,
        top_p=args.top_p,
        max_new_tokens=args.max_tokens,
    )
    elapsed = time.perf_counter() - start_time
    experiment["metadata"]["total_runtime_seconds"] = round(elapsed, 2)

    print(f"\n  ⏱ Total runtime: {elapsed:.1f}s")

    # ── Save ──────────────────────────────────────────────────────────────
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = save_results(experiment, output_dir)

    print(f"\n  Next: python -m experiments.analyze_experiment {output_path}")
    print()


if __name__ == "__main__":
    main()
