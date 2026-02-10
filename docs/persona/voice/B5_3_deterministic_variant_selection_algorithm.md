# B5.3 - Deterministic Variant Selection Algorithm

Status: LOCKED
Depends on: B4.3 (Controlled Variations - legal strings), B4.4 (Drift Telemetry - diagnostics only), B4.5 (Variant Expansion Protocol - growth), B5.1 (Variant Selection Principles - philosophy), B5.2 (Rotation Memory and Windowing - state model)
Applies to: Emotional Skeletons A / B / C / D
Languages: en / hinglish / hi

Goal: Given a fixed input state, select exactly one variant deterministically, with no randomness, no semantic reinterpretation, and no rule conflicts.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

## 1. Inputs (Complete and Closed)

The algorithm may use only the following inputs:

1.1 Required Inputs
- skeleton: A | B | C | D
- language: en | hinglish | hi
- section: opener | validation | action | closure
- variants: ordered list from B4.3 table
- rotation_memory: per B5.2 (variant IDs + timestamps)
- window_size: per skeleton (from B5.2)
- turn_index: index within emotional sequence
- escalation_state: none | escalating | latched
- latched_theme: null | family | other

1.2 Explicitly Forbidden Inputs
- Prompt semantics
- Embeddings or similarity scores
- Random numbers
- Temperature or sampling
- Drift telemetry values (diagnostic only)

If an input is not listed above, it must not affect selection.

## 2. High-Level Algorithm Overview

Selection proceeds in five ordered phases:
1. Eligibility Filtering
2. Hard Constraint Enforcement
3. Usage Scoring
4. Tie-Break Resolution
5. Final Selection

Each phase strictly reduces the candidate set or orders it.

## 3. Phase 1 - Eligibility Filtering

Start with all variants from the B4.3 table for (skeleton, language, section).

3.1 Skeleton Constraints
- If skeleton == C:
  - Disallow any variant added via B4.5 unless explicitly approved
- If skeleton == D:
  - Only action variants allowed; opener/closure fixed

3.2 Section Constraints
- If section == closure:
  - Only one legal option -> return immediately

If only one candidate remains at the end of Phase 1, return it.

## 4. Phase 2 - Hard Constraint Enforcement

These constraints remove candidates.

4.1 No Immediate Repetition

Remove any variant that was used in the immediately preceding emotional turn for the same section, if alternatives exist.

Exception:
- Skeleton C may repeat if removing would leave zero candidates.

4.2 Escalation Constraints
- If escalation_state == latched:
  - Do not allow variants marked as lighter than current skeleton
- If skeleton == C:
  - Do not allow any variant with higher lexical activity than the last C turn

4.3 Theme Constraints
- If latched_theme == family:
  - Disallow variants not approved for family context

If zero candidates remain:
- Restore last-used variant only if skeleton C
- Otherwise, fall back to first variant in table (stable failure)

## 5. Phase 3 - Usage Scoring (Deterministic)

Each remaining candidate receives a score.

5.1 Base Score

All candidates start with score 0.

5.2 Recent Usage Penalty

For each occurrence of the variant in the rolling window:

score -= (window_size - distance_from_now)

This penalizes recent usage more heavily.

5.3 Usage Cap Soft Penalty

If variant usage > 50% of window:

score -= window_size * 2

Exception:
- Skeleton C ignores this penalty unless repetition is extreme.

## 6. Phase 4 - Tie-Break Resolution

If multiple variants share the highest score, resolve ties deterministically.

Order of tie-breakers:
1. Least recently used
2. Lowest absolute usage count in window
3. Lowest variant index (as defined in B4.3 table)

This guarantees stable outcomes across runs.

## 7. Phase 5 - Final Selection

Select the single remaining variant.

7.1 Memory Update

Record:
- variant ID
- skeleton
- language
- section
- turn index

Update rotation memory per B5.2 rules.

## 8. Skeleton-Specific Overrides (Summary)

Skeleton A
- Skip Phase 3 penalties on first emotional turn
- Stability favored over freshness

Skeleton B
- Full algorithm applies
- Validation rotation weighted more than opener rotation

Skeleton C
- Phase 2 dominates
- Phase 3 penalties heavily dampened
- Tie-break almost always resolves to last-used

Skeleton D
- Action rotation only
- Closure fixed, opener minimal

## 9. Failure Modes Prevented

This algorithm explicitly prevents:
- Random jitter
- Template loops
- Over-rotation
- Skeleton C becoming chatty
- CI non-determinism
- Drift hacks at selection time

## 10. Non-Goals (Explicit)

B5.3 does NOT:
- Add new variants
- Modify drift thresholds
- Change emotional posture
- Interpret user intent
- Optimize engagement

Lock statement

If the same internal state appears twice, the same variant must be selected.

Variation comes from memory and context, not chance.

A system that cannot explain why it chose a sentence does not understand its own voice.

Version: B5.3.0
Date: 2026-02-10
Locked by: shubhankartiwari
Upstream: B4.x, B5.1, B5.2

Status: LOCKED
Changes require:
- version bump
- design rationale
- downstream coherence review
