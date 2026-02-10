# B6.4 - Error Handling and Deterministic Fallback Semantics

Status: LOCKED
Depends on: B6.1 (Architecture), B6.2 (State), B6.3 (Control Flow), B5.3 (Selection Algorithm), B4.3 (Voice Contract)
Applies to: Runtime inference only
Goal: Ensure that any failure in voice selection or state handling degrades safely, deterministically, and audibly, without silent corruption or nondeterminism.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

This spec defines what happens when things go wrong without introducing randomness, hidden recovery logic, or unsafe text.

## 1. Core Principle (Hard Rule)

Errors must never create new voice behavior.

On failure:
- We fall back to known-safe strings
- We preserve determinism
- We surface the failure via meta
- We never invent phrasing

If the system cannot explain why it chose a fallback, it must not choose it.

## 2. Error Taxonomy (Closed Set)

All runtime failures are classified into one of the following types:

E1 - Contract Load Errors

Examples:
- B4.3 contract file missing
- Contract parse failure
- Skeleton/language/section missing in contract

E2 - Selection Errors

Examples:
- No eligible variants after filtering
- Rotation memory inconsistent
- Invalid variant ID referenced

E3 - State Errors

Examples:
- Corrupt rotation memory
- Invalid skeleton transition
- Missing session state fields

E4 - Assembly Errors

Examples:
- Missing section text
- Invalid section order
- Empty assembled response

No other error classes are allowed.

## 3. Global Fallback Hierarchy (Deterministic)

When an error occurs, the system must resolve the response using the first applicable fallback in this order:

Level 1 - Skeleton-local fallback
- Use first variant in the B4.3 table for:
  - same skeleton
  - same language
  - same section

This preserves emotional posture.

Level 2 - Skeleton-safe English fallback

If language-specific table is unavailable:
- Fall back to English table for same skeleton

Level 3 - Absolute safe fallback (last resort)

Used only if B4.3 is entirely unavailable.

Hardcoded constants (exact strings):
- Skeleton A
  "I hear you. If you want, you can tell me more."
- Skeleton B
  "That sounds like a lot to carry. I'm here with you."
- Skeleton C
  "That sounds exhausting. We can just stay here for a moment."
- Skeleton D
  "Let's keep this very small. That's enough for now."

These strings are immutable and live in code, not config.

## 4. Error Handling by Stage

4.1 Contract Load Stage

If B4.3 contract fails to load:
- Skip variant selection entirely
- Emit absolute safe fallback per skeleton
- Do not update rotation memory

Meta annotation required:

{
  "fallback_reason": "contract_load_failure",
  "fallback_level": "absolute"
}

## 4.2 Variant Selection Stage

If selection produces zero valid candidates:
- Apply Level 1 fallback
- Do not attempt re-filtering or retries
- Record fallback usage in rotation memory

Meta:

{
  "fallback_reason": "selection_exhausted",
  "fallback_level": "skeleton_local"
}

## 4.3 Rotation Memory Errors

If rotation memory is invalid or corrupt:
- Clear affected pool(s)
- Re-run selection once
- If failure persists, apply Level 1 fallback

Meta:

{
  "fallback_reason": "rotation_memory_reset",
  "fallback_level": "skeleton_local"
}

## 4.4 Assembly Errors

If response assembly fails:
- Skip assembly
- Emit absolute safe fallback
- Do not mutate state

Meta:

{
  "fallback_reason": "assembly_failure",
  "fallback_level": "absolute"
}

## 5. State Mutation Rules During Failure

Situation | Rotation Memory | emotional_turn_index
Fallback Level 1 | update | increment
Fallback Level 2 | update | increment
Absolute fallback | no update | no increment

Rationale:
- Absolute fallback is non-voice behavior
- It must not affect rotation dynamics

## 6. Determinism Guarantees

For the same:
- SessionVoiceState
- User input
- Contract files

The same error must always produce the same fallback string.

Forbidden:
- Random fallback choice
- Cycling through fallbacks
- Logging-based decisions

## 7. CI Enforcement

CI must verify:
- All fallbacks belong to allowed skeletons
- No fallback introduces advice (unless D)
- Absolute fallback strings are unchanged
- Fallback meta fields are present when used

CI must never suppress or auto-fix fallback usage.

Fallbacks are signals, not successes.

## 8. Explicit Non-Goals

B6.4 does NOT:
- Attempt recovery via re-generation
- Retry model calls
- Auto-correct contracts
- Silence failures
- Optimize user experience at the cost of correctness

Correctness > polish under failure.

Lock statement

A voice system that fails unpredictably will drift even faster than one that fails loudly.

B6.4 ensures that failure is safe, stable, and honest.

When things break, the system should not become creative, it should become quiet.

Version: B6.4.0
Date: 2026-02-10
Status: LOCKED
Upstream: B4.x, B5.x, B6.1- B6.3
