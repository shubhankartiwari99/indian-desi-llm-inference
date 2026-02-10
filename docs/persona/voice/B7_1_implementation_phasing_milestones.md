# B7.1 - Implementation Phasing and Milestones

Status: LOCKED
Depends on: B4.x (Voice Contract), B5.x (Selection and Memory), B6.x (Architecture, Control Flow, CI)
Applies to: Runtime inference, CI, and supporting infrastructure
Goal: Define a safe, incremental path to implement the full voice system without partial states, regressions, or hidden behavior changes.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

## 1. Core Principle (Hard Rule)

No phase may introduce behavior that is not fully enforceable by CI at that phase.

If a feature cannot be tested, it cannot ship.

Implementation proceeds in monotonic capability increases:
- Each phase is complete in itself
- No phase relies on future cleanup
- Rolling back a phase must leave the system in a valid state

## 2. Phasing Philosophy

Implementation is split by responsibility boundaries, not features.

Why:
- Prevents entanglement between meaning, voice, and memory
- Makes failures attributable
- Keeps determinism intact at every step

Each phase must answer one question clearly: what new responsibility is now live in the system?

## 3. Phase Overview (Ordered, Mandatory)

Phase 0 - Scaffolding and Invariants (Foundational)

Goal: Make violations impossible, even before behavior exists.

Deliverables:
- SessionVoiceState structure (B6.2)
- Empty RotationMemory with reset logic
- CI hooks wired (but selectors stubbed)
- Static enforcement:
  - No randomness imports
  - No ad-hoc string emission paths

Runtime behavior:
- Still uses existing static responses or baseline
- No variant selection yet

CI requirements:
- State objects serialize cleanly
- No tests rely on voice output yet

Exit criteria:
- Code compiles
- CI passes
- No behavior change visible to users

Phase 1 - Skeleton Resolution Integration

Goal: Make skeleton selection authoritative and observable.

Deliverables:
- Emotional skeleton resolver fully wired
- emotional_skeleton, emotional_lang, escalation_state emitted in meta
- SessionVoiceState updates (turn index, resets)

Runtime behavior:
- Responses still static or baseline
- Skeleton selection is correct and logged

CI requirements:
- Skeleton legality enforced
- Family/escalation invariants enforced
- No wording changes yet

Exit criteria:
- Skeleton is correct for all eval cases
- No voice selection logic exists yet

Phase 2 - Voice Contract Loading (B4.3)

Goal: Centralize all allowed strings.

Deliverables:
- B4.3 contract loader
- Variant tables exposed by skeleton/lang/section
- Variant IDs stable and index-based

Runtime behavior:
- Responses may still be static
- Contract data is loaded and validated

CI requirements:
- Contract parse tests
- Contract completeness checks
- Illegal strings rejected at CI time

Exit criteria:
- Contract is the only string source
- No runtime selection yet

Phase 3 - Deterministic Variant Selection (Core Voice)

Goal: Select exactly one legal variant per section.

Deliverables:
- B5.3 deterministic selector
- Rotation memory read/write (B5.2)
- Section-level selection (opener, validation, etc.)

Runtime behavior:
- First real voice behavior change
- Deterministic, rotation-aware responses

CI requirements:
- Replay determinism tests
- No immediate repetition checks
- Single-variant guarantee enforced

Exit criteria:
- Same state -> same output
- No drift telemetry yet

Phase 4 - Response Assembly and Control Flow Lock (B6.3)

Goal: Eliminate all bypass paths.

Deliverables:
- Response assembler
- Single execution path enforced
- Forbidden flow tests added

Runtime behavior:
- Full emotional responses assembled from variants
- No extra text, no omissions

CI requirements:
- Static call-graph checks
- Selector invoked exactly once
- No direct string emission elsewhere

Exit criteria:
- Voice selection cannot be bypassed

Phase 5 - Error Handling and Fallback Semantics (B6.4)

Goal: Make failure safe and loud.

Deliverables:
- Error classification
- Deterministic fallback logic
- Fallback meta emission

Runtime behavior:
- Safe fallback on any failure
- No silent corruption

CI requirements:
- Forced failure tests
- Absolute fallback snapshot tests
- State mutation rules verified

Exit criteria:
- Failure never invents voice
- Determinism preserved under error

Phase 6 - Drift Telemetry (Advisory) (B4.4)

Goal: Observe without influence.

Deliverables:
- Drift report script wired to CI
- Warning output standardized

Runtime behavior:
- No change

CI requirements:
- Drift warnings visible
- No build failures caused

Exit criteria:
- Drift visible but non-blocking

Phase 7 - Variant Expansion (Human-Gated) (B4.5)

Goal: Controlled evolution.

Deliverables:
- Expansion workflow documented
- Version bump checks enforced
- Max variant limits enforced

Runtime behavior:
- New variants only via contract updates

CI requirements:
- Expansion limit enforcement
- Version discipline checks

Exit criteria:
- Expansion possible without decay

## 4. Phase Invariants (Never Violated)

Across all phases:
- No randomness
- No semantic reinterpretation during selection
- No cross-session memory
- No CI-runtime coupling
- No temporary hacks

If a phase requires an exception, the phase is invalid.

## 5. Rollback Guarantees

Each phase must be revertible independently.

Rollback rules:
- Reverting a phase must not require reverting later phases
- State structures must remain backward-compatible
- CI must still pass after rollback

## 6. What B7.1 Does NOT Do

B7.1 does not:
- Assign engineers
- Define timelines
- Optimize performance
- Decide priority of features outside voice
- Replace code review

It defines order, not speed.

Version: B7.1.0
Date: 2026-02-10
Status: LOCKED
Upstream: B4.x, B5.x, B6.x
