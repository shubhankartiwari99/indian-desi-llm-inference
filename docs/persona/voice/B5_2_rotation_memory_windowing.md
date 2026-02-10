# B5.2 - Rotation Memory and Windowing

Status: LOCKED
Depends on: B4.3 (Controlled Variations - legal strings), B4.4 (Drift Telemetry - detection), B4.5 (Variant Expansion - growth), B5.1 (Variant Selection Principles - choice logic)
Applies to: Emotional Skeletons A / B / C / D
Languages: en / hinglish / hi

Goal: Define how long variant usage is remembered, what scope memory applies to, and when memory resets, so deterministic rotation feels human rather than mechanical.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

## 1. Why Rotation Memory Exists

Without memory:
- Deterministic selection collapses into repetition
- Drift warnings spike artificially
- No immediate repetition becomes impossible to enforce

With uncontrolled memory:
- Responses feel jittery or over-engineered
- Skeleton C becomes unsafe
- Long sessions degrade emotional coherence

B5.2 defines just enough memory.

## 2. Memory Scope (What Is Remembered)

Rotation memory tracks variant usage, not raw text and not semantics.

Tracked dimensions:
- Skeleton (A / B / C / D)
- Language (en / hinglish / hi)
- Section (opener / validation / action)
- Variant ID (index within B4.3 table)

Explicitly not tracked:
- User identity across sessions
- Emotional content meaning
- Prompt embeddings or similarity

This keeps memory mechanical, predictable, and auditable.

## 3. Memory Lifetime (Where Memory Lives)

3.1 Session-local memory (primary)

Default scope: single conversation session
- Memory exists only while the session is active
- Cleared when:
  - Session ends
  - Hard reset is triggered (see 6)

Rationale:
- Prevents cross-user bleed
- Avoids the assistant remembers how it sounded yesterday
- Keeps behavior explainable

3.2 No global memory (by design)

Global or cross-session rotation memory is forbidden.

Reason:
- Creates invisible coupling between users
- Makes CI and drift telemetry meaningless
- Breaks determinism guarantees

## 4. Rolling Window Definition

Rotation decisions use a rolling window per (skeleton, language, section).

Default window sizes

Skeleton | Window Size | Rationale
A | 6 turns | Stability-first, low variation
B | 8 turns | Balanced warmth and freshness
C | 3 turns | Safety-critical, minimal change
D | 4 turns | Prevent action repetition without drift

Notes:
- Window counts emotional turns only
- Non-emotional turns do not advance the window
- Windows are independent per section (opener != validation)

## 5. Usage Caps Within Window

Within the rolling window:

Rule:
- No variant may exceed 50% usage if alternatives exist

Clarifications:
- If only one variant exists, repetition allowed
- If two variants exist, strict alternation preferred
- If three or more, deprioritize recent, not ban

Skeleton-specific nuance:
- Skeleton C may violate the 50% rule if enforcing stability
- Skeleton A prioritizes safety over freshness

## 6. Memory Reset Conditions

Rotation memory resets when emotional continuity breaks.

6.1 Hard reset triggers

Reset all rotation memory when:
- Emotional intent changes to non-emotional
- Topic shift detected (implementation later)
- Escalation fully resolves (C -> A transition)
- New session starts

6.2 Partial reset triggers

Reset only the active skeleton pool when:
- Escalation depth increases (A -> B, B -> C)
- Latched theme changes (e.g., non-family -> family)

Example:
- Moving A -> B clears B memory, but keeps A history intact.

## 7. Skeleton-Specific Memory Behavior

Skeleton A - Gentle Acknowledgment
- Memory bias: stickiness
- Reuse is allowed unless repetition becomes obvious
- Window pressure is weak

Skeleton B - Grounded Presence
- Memory bias: active rotation
- Validations should cycle deliberately
- Avoid emotional framing repetition

Skeleton C - Shared Stillness
- Memory bias: stability
- Repetition preferred over novelty
- Window exists only to prevent accidental oscillation

Skeleton D - Micro-Action
- Memory bias: containment
- Do not repeat the same action twice if alternatives exist
- Closure never rotates

## 8. Interaction With Drift Telemetry (B4.4)

Rotation memory is preventive, not corrective.

Rules:
- Rotation must not change behavior to silence drift warnings
- Drift warnings inform B4.5 expansion, not B5.2 tuning
- Window sizes must not be adjusted dynamically

If drift persists despite correct rotation:
- That is evidence for variant expansion, not selection hacks

## 9. Failure Modes Prevented by This Design

This spec explicitly avoids:
- Random jitter
- Over-clever variation
- Skeleton C chattiness
- Repetition across unrelated conversations
- CI instability due to hidden state

## 10. Non-Goals (Explicit)

B5.2 does NOT:
- Define how variants are scored
- Decide which variant is best
- Store memory across restarts
- Introduce probabilistic behavior
- Replace drift telemetry

Those belong to B5.3 and later.

Lock statement

Rotation memory should feel like a human remembering how they just spoke, not a system trying to sound different.

When in doubt, repeat safely.

Version: B5.2.0
Date: 2026-02-10
Locked by: shubhankartiwari
Upstream: B4.x, B5.1

Status: LOCKED
Changes require:
- version bump
- design rationale
- downstream coherence review
