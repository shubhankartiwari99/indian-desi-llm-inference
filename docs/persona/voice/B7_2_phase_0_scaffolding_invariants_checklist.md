# B7.2 - Phase 0 (Scaffolding and Invariants) Implementation Checklist

Status: LOCKED
Depends on: B6.2 (State), B6.3 (Control Flow), B6.5 (CI Coverage), B7.1 (Phasing)
Applies to: Runtime codebase and CI
Goal: Make all future voice behavior structurally unavoidable before any selection or wording logic ships.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

Phase 0 introduces no new user-visible behavior. Its only purpose is to make violations impossible later.

## 1. Phase 0 Definition (Non-Negotiable)

Phase 0 is complete only when:
- All required state exists
- All forbidden behaviors are mechanically blocked
- CI can prove nothing voice-related is happening yet

If anything sounds different after Phase 0, Phase 0 is invalid.

## 2. New Structures That MUST Exist

2.1 SessionVoiceState (B6.2)

Create the structure exactly as specified.

Fields (must exist, even if unused):
- rotation_memory
- escalation_state
- latched_theme
- emotional_turn_index
- last_skeleton

Rules
- Serializable to plain dict
- Session-local only
- Initialized on session start
- Resettable via explicit calls

Must NOT contain:
- Text
- Variants
- Drift metrics
- Random seeds

2.2 RotationMemory (Empty, but Real)

Create the data structure with:
- Pool indexing by (skeleton, language, section)
- Window size stored per pool
- Append-only history

Phase 0 constraint:
- No variant IDs are ever written
- Reads return empty windows

This ensures later code plugs in without refactors.

## 3. Control-Flow Scaffolding That MUST Exist

3.1 Single Voice Entry Point (Stubbed)

Introduce the function boundary that will later become:

select_voice_variants(...)

Phase 0 behavior:
- Must be callable
- Must return a placeholder object or raise NotImplementedError
- Must NOT select variants
- Must NOT load contracts

This establishes the only legal entry point.

3.2 Explicit No-Bypass Guards

Add mechanical guards so that:
- No function outside the voice path can emit emotional text
- Any attempt to:
  - hardcode strings
  - bypass the selector
  - assemble responses inline

Fails fast (assert / exception).

This is intentional friction.

## 4. Forbidden Behavior Checks (Static)

Phase 0 must add checks that fail CI immediately if violated.

4.1 Randomness Ban

CI must fail if:
- random
- numpy.random
- sampling APIs
- temperature parameters

are imported in any voice-related module.

4.2 Ad-Hoc String Emission Ban

CI must fail if:
- New emotional strings appear outside:
  - baseline system
  - future B4.3 loader (not yet active)

Simple heuristic is fine:
- Grep-based allowlist
- Static scan

False positives are acceptable in Phase 0.

## 5. CI Requirements (Hard Gates)

Phase 0 CI must assert:
- SessionVoiceState can be created, reset, serialized
- RotationMemory exists and is empty
- No randomness imports
- No voice strings added
- Selector entry point exists and is unused
- No behavior change in eval outputs

If any check is missing, Phase 0 is incomplete.

## 6. Explicitly Deferred (Must NOT Be Started)

Phase 0 must NOT include:
- B4.3 contract loading
- Variant selection logic
- Rotation scoring
- Drift telemetry
- Any wording changes
- Any temporary logic

If a comment says we will clean this up later, Phase 0 has failed.

## 7. Exit Criteria (Binary)

Phase 0 is DONE if and only if:
- Code compiles
- CI is green
- Outputs are byte-for-byte identical to pre-Phase-0 behavior
- Voice scaffolding exists and is unavoidable
- Future phases can plug in without touching unrelated code

Otherwise, do not proceed.

## 8. Lock Statement

Phase 0 is successful when the system becomes harder to misuse than to use correctly.

If someone tries to add voice behavior without following B5/B6:
- The code should fight them
- CI should stop them
- Architecture should make it uncomfortable

That is the entire purpose of Phase 0.




Version: B7.2.0
Date: 2026-02-10
Status: LOCKED
Upstream: B6.x, B7.1
