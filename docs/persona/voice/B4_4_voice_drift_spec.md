# B4.4 — Voice Drift Resistance & Naturalness Checks

Status: DESIGN
Depends on: B4.1, B4.2, B4.3
Goal: Prevent the persona from becoming robotic, templated, emotionally flat, over-safe, or repetitive in feel.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

## What Voice Drift Is

Voice drift happens when outputs pass B4.3 and CI is green, but humans feel:
- "This sounds the same every time"
- "It is emotionally correct but dead"
- "It feels like a template responding to me"

Drift is qualitative, not syntactic. B4.4 uses signals, not hard rules.

## Drift Risk Categories

A. Template fatigue
- Reuses the same opener too often
- Favors one validation sentence
- Defaults to the safest closure every time

B. Emotional flattening
- Polite and correct but emotionally neutral
- Especially risky in Skeleton C and long emotional sequences

C. Over-stabilization
- Avoids warmth, specificity, and resonance
- Feels like HR, not a human

D. Escalation stalling
- Skeleton transitions happen, but emotional depth does not change

## Strategy Overview

Layer 1 — Drift signals (passive)
Layer 2 — Naturalness heuristics (evaluative)
Layer 3 — CI warnings (non-blocking at first)

## Drift Signals (Metrics, not failures)

4.1 Opener concentration
- Per skeleton + language
- Rolling window (default: last 50 emotional turns)
- Signal if one opener > 65% usage

4.2 Validation diversity
- Count unique validation lines used
- Signal if only 1 validation used across many turns

4.3 Emotional lexical density
- Track emotion words (heavy, tired, overwhelmed, drained)
- Track relational words (carry, hold, with you, here)
- Signal if density trends downward across turns

4.4 Escalation depth delta
- Compare A vs B vs C responses
- Signal if C responses are indistinguishable from A/B in structure

## Naturalness Heuristics (Human-aligned)

5.1 "Would a caring human say this twice?"
- Flag repeated structure even if words differ

5.2 "Does this respond to this sentence?"
- Flag generic validation with low semantic overlap

5.3 Silence respect (Skeleton C)
- Flag optimism or redirection

## CI Integration Plan

Phase 1 — Advisory mode
- Print VOICE_DRIFT_WARNING
- Do not fail builds

Phase 2 — Soft gates
- Fail only on extreme drift (e.g., 80% same opener for A)

Phase 3 — Locked invariants
- Promote subset to hard rules after human review

## Deliverables

1. B4_4_voice_drift_spec.md (this doc, locked)
2. ci_voice_drift_report.py (warn-only report)
3. Sample drift report checked in

---
Version: B4.4.0
Last updated: 2026-02-10
Upstream dependencies: B4.1, B4.2, B4.3
