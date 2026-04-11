"""
Experiment Analysis — Post-hoc statistical analysis of cultural alignment results.

Reads experiment output JSON and produces:
  1. Per-condition summary table
  2. ΔP with bootstrap confidence intervals
  3. Collapse ratio comparison
  4. Prompt-gradient dose-response analysis
  5. Formatted terminal report + JSON output

Usage:
  python -m experiments.analyze_experiment experiments/results/experiment_YYYYMMDD_HHMM.json
  python -m experiments.analyze_experiment experiments/results/experiment_YYYYMMDD_HHMM.json --output report.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap confidence interval
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_ci(
    data: list[float],
    *,
    n_boot: int = 5000,
    ci: float = 0.95,
    stat_fn=statistics.mean,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for a statistic.

    Returns: (point_estimate, ci_lower, ci_upper)
    """
    if not data:
        return (0.0, 0.0, 0.0)
    if len(data) == 1:
        return (data[0], data[0], data[0])

    rng = random.Random(seed)
    point = stat_fn(data)

    boot_stats = []
    for _ in range(n_boot):
        sample = [rng.choice(data) for _ in range(len(data))]
        boot_stats.append(stat_fn(sample))

    boot_stats.sort()
    alpha = (1 - ci) / 2
    lo_idx = max(0, int(alpha * n_boot))
    hi_idx = min(n_boot - 1, int((1 - alpha) * n_boot))

    return (round(point, 4), round(boot_stats[lo_idx], 4), round(boot_stats[hi_idx], 4))


def bootstrap_delta_ci(
    data_a: list[float],
    data_b: list[float],
    *,
    n_boot: int = 5000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap CI for the difference (mean_a - mean_b).
    Uses paired resampling if lengths match, independent otherwise.
    """
    if not data_a or not data_b:
        return (0.0, 0.0, 0.0)

    rng = random.Random(seed)
    point = statistics.mean(data_a) - statistics.mean(data_b)

    deltas = []
    for _ in range(n_boot):
        sample_a = [rng.choice(data_a) for _ in range(len(data_a))]
        sample_b = [rng.choice(data_b) for _ in range(len(data_b))]
        deltas.append(statistics.mean(sample_a) - statistics.mean(sample_b))

    deltas.sort()
    alpha = (1 - ci) / 2
    lo_idx = max(0, int(alpha * n_boot))
    hi_idx = min(n_boot - 1, int((1 - alpha) * n_boot))

    return (round(point, 4), round(deltas[lo_idx], 4), round(deltas[hi_idx], 4))


# ─────────────────────────────────────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_experiment(data: dict) -> dict:
    """
    Perform full statistical analysis on experiment results.

    Returns a structured report dict.
    """
    levels = data.get("levels", {})
    metadata = data.get("metadata", {})

    report: dict[str, Any] = {
        "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
        "experiment_metadata": metadata,
        "per_level": {},
        "deltas": {},
        "collapse_ratios": {},
        "dose_response": {},
    }

    # ── Per-level detailed stats ──────────────────────────────────────────
    level_scores: dict[str, list[float]] = {}
    level_binary: dict[str, list[int]] = {}
    level_entropies: dict[str, list[float]] = {}

    ordered_levels = ["neutral", "weak_india", "strong_india"]
    for level_name in ordered_levels:
        if level_name not in levels:
            continue
        level_data = levels[level_name]
        runs = level_data.get("runs", [])
        valid = [r for r in runs if not r.get("error")]

        scores = [r["cultural_signal"]["score"] for r in valid]
        binary = [1 if r["cultural_signal"]["has_cultural_signal"] else 0 for r in valid]
        entropies = [r["token_entropy"] for r in valid]

        level_scores[level_name] = scores
        level_binary[level_name] = binary
        level_entropies[level_name] = entropies

        n = len(valid)
        p_cultural = sum(binary) / n if n > 0 else 0.0

        score_ci = bootstrap_ci(scores)
        p_ci = bootstrap_ci(binary)
        entropy_ci = bootstrap_ci(entropies)

        report["per_level"][level_name] = {
            "n": n,
            "P_cultural": round(p_cultural, 4),
            "P_cultural_CI_95": [p_ci[1], p_ci[2]],
            "mean_cultural_score": score_ci[0],
            "score_CI_95": [score_ci[1], score_ci[2]],
            "mean_entropy": entropy_ci[0],
            "entropy_CI_95": [entropy_ci[1], entropy_ci[2]],
        }

    # ── ΔP calculations with CIs ─────────────────────────────────────────
    neutral_binary = level_binary.get("neutral", [])
    neutral_scores = level_scores.get("neutral", [])

    for target in ["weak_india", "strong_india"]:
        if target not in level_binary:
            continue

        target_binary = level_binary[target]
        target_scores = level_scores[target]

        dp_binary = bootstrap_delta_ci(
            [float(x) for x in target_binary],
            [float(x) for x in neutral_binary],
        )
        dp_score = bootstrap_delta_ci(target_scores, neutral_scores)

        report["deltas"][f"{target}_vs_neutral"] = {
            "ΔP_binary": dp_binary[0],
            "ΔP_binary_CI_95": [dp_binary[1], dp_binary[2]],
            "ΔP_significant": (dp_binary[1] > 0 or dp_binary[2] < 0),  # CI doesn't cross zero
            "Δscore": dp_score[0],
            "Δscore_CI_95": [dp_score[1], dp_score[2]],
            "Δscore_significant": (dp_score[1] > 0 or dp_score[2] < 0),
        }

    # ── Collapse ratios ──────────────────────────────────────────────────
    import math
    ref_entropy = math.log2(200)
    for level_name, entropies in level_entropies.items():
        if not entropies:
            continue
        mean_e = statistics.mean(entropies)
        ratio = round(1.0 - (mean_e / ref_entropy), 4) if ref_entropy > 0 else 0.0
        report["collapse_ratios"][level_name] = {
            "collapse_ratio": ratio,
            "mean_entropy": round(mean_e, 4),
            "reference_entropy": round(ref_entropy, 4),
        }

    # ── Dose-response (gradient linearity check) ─────────────────────────
    dose_levels = []
    for i, level_name in enumerate(ordered_levels):
        if level_name in report["per_level"]:
            dose_levels.append({
                "level": level_name,
                "strength": i,
                "P_cultural": report["per_level"][level_name]["P_cultural"],
                "mean_score": report["per_level"][level_name]["mean_cultural_score"],
                "collapse_ratio": report["collapse_ratios"].get(level_name, {}).get("collapse_ratio", 0.0),
            })

    report["dose_response"] = {
        "levels": dose_levels,
        "interpretation": _interpret_dose_response(dose_levels),
    }

    return report


def _interpret_dose_response(levels: list[dict]) -> str:
    """Generate a human-readable interpretation of the dose-response pattern."""
    if len(levels) < 2:
        return "Insufficient data for dose-response analysis."

    p_values = [l["P_cultural"] for l in levels]
    is_monotonic = all(p_values[i] <= p_values[i + 1] for i in range(len(p_values) - 1))

    if is_monotonic and p_values[-1] > p_values[0]:
        gradient = p_values[-1] - p_values[0]
        if gradient > 0.3:
            return (
                f"Strong monotonic dose-response detected (gradient={gradient:.2f}). "
                "Cultural signal probability increases proportionally with prompt conditioning strength. "
                "This supports the hypothesis that runtime acts as a proportional cultural amplifier."
            )
        elif gradient > 0.1:
            return (
                f"Moderate monotonic dose-response detected (gradient={gradient:.2f}). "
                "Runtime shows some proportional cultural amplification, but the effect is modest. "
                "Larger sample sizes recommended to confirm linearity."
            )
        else:
            return (
                f"Weak monotonic pattern (gradient={gradient:.2f}). "
                "While technically monotonic, the effect size is too small for confident claims. "
                "This may indicate floor/ceiling effects or high variance."
            )
    elif p_values[-1] > p_values[0]:
        return (
            "Non-monotonic but positive trend detected. "
            "The relationship between prompt strength and cultural alignment is not strictly linear, "
            "suggesting that runtime amplification may be nonlinear or threshold-dependent."
        )
    else:
        return (
            "No clear dose-response pattern detected. "
            "Cultural alignment does not increase with prompt conditioning strength. "
            "This may indicate that runtime does not selectively amplify cultural signals."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Terminal report
# ─────────────────────────────────────────────────────────────────────────────

def render_report(report: dict) -> str:
    """Render the analysis report as a human-readable terminal summary."""
    lines: list[str] = []

    lines.append("")
    lines.append("╔════════════════════════════════════════════════════════════════╗")
    lines.append("║  CULTURAL ALIGNMENT ANALYSIS — EXPERIMENT 2.1 + 2.2          ║")
    lines.append("╚════════════════════════════════════════════════════════════════╝")

    # ── Per-level table ───────────────────────────────────────────────────
    lines.append("")
    lines.append("  ┌─────────────────┬──────┬────────────┬────────────────┬────────────┐")
    lines.append("  │ Level           │  n   │ P(cultural)│ Mean Score     │ Entropy    │")
    lines.append("  ├─────────────────┼──────┼────────────┼────────────────┼────────────┤")

    for level_name in ["neutral", "weak_india", "strong_india"]:
        if level_name not in report.get("per_level", {}):
            continue
        pl = report["per_level"][level_name]
        ci_lo, ci_hi = pl["P_cultural_CI_95"]
        lines.append(
            f"  │ {level_name:>15} │ {pl['n']:>4} │ "
            f"{pl['P_cultural']:>10.2f} │ "
            f"{pl['mean_cultural_score']:.3f} [{pl['score_CI_95'][0]:.3f},{pl['score_CI_95'][1]:.3f}] │ "
            f"{pl['mean_entropy']:.3f}      │"
        )

    lines.append("  └─────────────────┴──────┴────────────┴────────────────┴────────────┘")

    # ── Deltas ────────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  ΔP (Cultural Shift vs Neutral):")
    for key, delta in report.get("deltas", {}).items():
        sig = "✅ SIG" if delta.get("ΔP_significant") else "⚪ n.s."
        lines.append(
            f"    {key:>30}: ΔP={delta['ΔP_binary']:+.4f}  "
            f"CI=[{delta['ΔP_binary_CI_95'][0]:+.4f}, {delta['ΔP_binary_CI_95'][1]:+.4f}]  {sig}"
        )

    # ── Collapse ratios ──────────────────────────────────────────────────
    lines.append("")
    lines.append("  Collapse Ratios (per condition):")
    for level_name in ["neutral", "weak_india", "strong_india"]:
        cr = report.get("collapse_ratios", {}).get(level_name, {})
        if cr:
            lines.append(f"    {level_name:>15}: {cr['collapse_ratio']:.4f}")

    # ── Dose-response ────────────────────────────────────────────────────
    dr = report.get("dose_response", {})
    if dr.get("interpretation"):
        lines.append("")
        lines.append("  Dose-Response Interpretation:")
        # Wrap long text
        interp = dr["interpretation"]
        words = interp.split()
        current_line = "    "
        for word in words:
            if len(current_line) + len(word) + 1 > 80:
                lines.append(current_line)
                current_line = "    " + word
            else:
                current_line += " " + word if current_line.strip() else "    " + word
        if current_line.strip():
            lines.append(current_line)

    # ── Caveat ──────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  ⚠ Note: n≤30 per condition. Frame conclusions as:")
    lines.append('    "Preliminary evidence suggests..."')
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze cultural alignment experiment results",
    )
    parser.add_argument(
        "input_file",
        help="Path to experiment results JSON file",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for analysis report JSON (default: <input>_analysis.json)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    report = analyze_experiment(data)

    # ── Render terminal report ────────────────────────────────────────────
    print(render_report(report))

    # ── Save JSON report ──────────────────────────────────────────────────
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(input_path.stem + "_analysis.json")

    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  📁 Report saved to: {output_path}")
    print()


if __name__ == "__main__":
    main()
