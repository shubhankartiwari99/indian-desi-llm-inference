# B4.5 - Variant Expansion Protocol

Status: LOCKED
Depends on: B4.1 (Voice Principles), B4.2 (Skeleton Texts), B4.3 (Controlled Variations), B4.4 (Drift Telemetry)
Applies to: Emotional Skeletons A / B / C / D
Goal: Allow controlled growth of voice variety without breaking safety, consistency, or emotional posture.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

This protocol governs when, where, and how new voice variants may be added.

## 1. Why Variant Expansion Exists

Even with perfect enforcement (B4.3) and drift detection (B4.4), static tables will decay:
- Users feel repetition
- Emotional presence flattens
- Responses feel templated, not human

Variant Expansion is the only sanctioned way to add freshness. Any other edits are considered violations.

## 2. Expansion Is Triggered Only by Evidence

Variants are added only when drift signals persist.

Eligible triggers (from B4.4)

A skeleton + language pair becomes eligible if any of the following hold for >= 2 consecutive eval runs:
- Opener concentration > 65%
- Validation diversity <= 1 unique line
- Emotional flattening trend detected
- Structure repetition > 70%

Not enough:
- Human "feels repetitive" feedback alone

Enough:
- CI drift telemetry + human review together

## 3. Expansion Eligibility Matrix

Skeleton | Expansion Allowed | Max Variants | Notes
A | Limited | +1 per section | Stability-first
B | Yes | +2 per section | Primary flexibility zone
C | Extremely rare | +0 by default | Safety-critical
D | No | 0 | Actions are fixed

Default rule: If unsure, do not expand.

## 4. What Can Be Expanded

Variants may be added only to these fields:
- Opener
- Validation

Closures are fixed unless explicitly unlocked in a future version.

Hard limits (per skeleton + language):
- Opener: max 3
- Validation: max 4
- Closure: fixed (unless spec changes)
- Action (Skeleton D): fixed forever

Any attempt to exceed limits requires:
- Version bump
- Explicit rationale
- Human sign-off

## 5. What Is Forbidden (Always)

Variant expansion must never introduce:
- Advice language (should, try, best way)
- New metaphors (unless culturally grounded and approved)
- New actions (outside Skeleton D)
- Optimism injection into Skeleton C
- Question forms (why, probing questions)
- Mixed-language leakage

If a new line requires an explanation to justify safety, it is rejected.

## 6. Variant Quality Bar (Human Review Checklist)

Every proposed variant must pass all:
1. Emotional posture preserved
- Same emotional intent as original skeleton
2. Human naturalness
- Would a calm, caring Indian adult say this once?
3. Non-directive
- No nudging, fixing, or solving (unless D)
4. Composable
- Works with all existing openers/closures in that skeleton
5. Distinct
- Adds real variation, not synonyms

## 7. Rotation and Weighting Rules (Design Only)

When multiple variants exist:
- Rotation is deterministic, not random
- Recently used variants are deprioritized
- No variant may exceed 50% usage over a rolling window
- Skeleton C prioritizes silence stability over diversity

Implementation deferred to future track.

## 8. Expansion Workflow (Required)

1. Drift warning observed in CI (B4.4)
2. Human review confirms felt repetition
3. Candidate variants drafted (max limits respected)
4. Variants reviewed against checklist
5. Added to B4.3 tables
6. Version bumped (e.g., B4.3.1)
7. CI voice contract updated
8. Drift telemetry monitored post-merge

Skipping any step invalidates the expansion.

## 9. Versioning Rules

- B4.3.x: content-only expansions
- B4.5.x: protocol changes
- No silent edits
- Every expansion must be traceable to a drift signal

## 10. Non-Goals (Explicit)

B4.5 does not:
- Decide which strings to add
- Change inference logic
- Override safety constraints
- Optimize for engagement metrics

Its only job is controlled evolution.

Final lock statement

Voice should evolve slowly, deliberately, and with memory. B4.5 ensures growth without loss of soul.

Version: B4.5.0
Date: 2026-02-10
Locked by: shubhankartiwari
