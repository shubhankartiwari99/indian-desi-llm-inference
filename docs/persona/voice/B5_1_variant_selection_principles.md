# B5.1 - Variant Selection Principles

Status: LOCKED
Depends on: B4.3 (Controlled Variations - what is allowed), B4.4 (Drift Telemetry - when variation is needed), B4.5 (Variant Expansion Protocol - how new variants enter)
Applies to: Emotional Skeletons A / B / C / D
Languages: en / hinglish / hi

Goal: Choose which allowed variant to emit on each turn in a way that feels human, avoids repetition, preserves emotional posture, and resists drift - without randomness.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

## 1. Core Philosophy

Variant selection must feel:
- Intentional, not random
- Stable, not jittery
- Human, not templated
- Predictable to the system, invisible to the user

If two users say the same thing twice in a row, the assistant should usually not sound identical, but it also must not try too hard to be different.

## 2. Determinism Over Randomness

Rule: Variant selection is deterministic, not RNG-based.

Why:
- Randomness breaks reproducibility
- CI and drift telemetry become meaningless
- Debugging becomes impossible

Allowed sources of variation:
- Turn index
- Session-local history
- Recent variant usage counts
- Escalation depth (A -> B -> C)

Explicitly forbidden:
- random.choice
- temperature-based phrasing changes
- sampling outside the B4.3 tables

## 3. Selection Inputs (Signal Stack)

Variant selection may use only the following inputs:
1. Skeleton type (A / B / C / D)
2. Language (en / hinglish / hi)
3. Turn position in emotional sequence
4. Recent variants used (rolling window)
5. Escalation state
6. Latched themes (e.g., family)

No semantic reinterpretation is allowed at this stage.

## 4. Rotation Rules (Global)

4.1 No Immediate Repetition
- The same opener / validation / action must not be used twice in a row if alternatives exist.

4.2 Usage Cap
- No single variant may exceed 50% usage over the rolling window (default window defined in B5.2).

4.3 Recency Bias (Negative)
- Recently used variants are deprioritized until others are used.

## 5. Skeleton-Specific Selection Behavior

Skeleton A - Gentle Acknowledgment
- Priority: emotional safety > freshness
- Variation: minimal
- Rules:
  - Prefer stability on first contact
  - Rotate only if repetition is detected
  - Never sound clever

Skeleton B - Grounded Presence
- Priority: warmth and presence
- Variation: moderate
- Rules:
  - Actively rotate validations
  - Avoid repeating emotional framing
  - Match escalation depth (pressure should feel heavier than A)

Skeleton C - Shared Stillness
- Priority: safety > silence > stability
- Variation: extremely limited
- Rules:
  - Do not rotate unless repetition becomes oppressive
  - Stability beats diversity
  - Silence-like responses preferred

Skeleton D - Micro-Action
- Priority: clarity and containment
- Variation: structured only
- Rules:
  - Rotate actions only when the same request repeats
  - Never introduce new action forms
  - Closure always fixed

## 6. Escalation-Aware Selection

When escalation is active:
- Do not rotate upwards (A-style warmth inside C)
- Do not soften C
- Do not inject optimism

Escalation changes which pool is active, not just the variant.

## 7. Language Purity Enforcement

Variant selection must:
- Use only variants from the detected language table
- Never mix scripts
- Never translate between languages

If language detection is uncertain:
- Fall back to English
- Log ambiguity (future telemetry)

## 8. Interaction With Drift Telemetry (B4.4)

Variant selection is preventive, drift telemetry is diagnostic.

Expected behavior:
- Proper rotation should reduce drift warnings over time
- Drift warnings trigger expansion, not selection hacks

Selection logic must never:
- Inject new phrasing to fix drift
- Bend B4.3 rules to avoid warnings

## 9. Non-Goals (Explicit)

B5.1 does not:
- Define storage format
- Define memory window size
- Add new variants
- Change emotional intent
- Optimize engagement

Those belong to later B5 steps.

## 10. Lock Statement

Variant selection is not about being creative. It is about choosing restraint intelligently.

A good system does not sound new every time. It sounds right, and not the same.

Version: B5.1.0
Date: 2026-02-10
Locked by: shubhankartiwari
Upstream: B4.x series

Status: LOCKED
Changes require:
- version bump
- design rationale
- downstream coherence review
