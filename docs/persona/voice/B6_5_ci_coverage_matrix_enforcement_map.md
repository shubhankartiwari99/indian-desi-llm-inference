# B6.5 - CI Coverage Matrix and Enforcement Map

Status: LOCKED
Depends on: B4.3, B4.4, B4.5, B5.1- B5.3, B6.1- B6.4
Applies to: Offline evaluation and CI only
Goal: Make explicit what is enforced, what is warned, and what is merely observed, so no invariant silently drifts.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

This spec answers one question only: Which rule is enforced where, and how loudly?

No new rules are introduced here. This is a map, not a policy.

## 1. CI Philosophy (Non-Negotiable)

CI exists to:
- Prevent silent voice drift
- Catch illegal behavior early
- Make violations obvious and attributable

CI must never:
- Patch outputs
- Influence runtime logic
- Introduce heuristics not present in specs

If a rule matters, CI must say so explicitly.

## 2. Enforcement Levels (Closed Set)

Every invariant falls into exactly one category:

Level | Meaning | CI Behavior
HARD FAIL | Violates correctness or safety | Build fails
SOFT FAIL | Violates design intent but not safety | Build fails only after lock
WARN | Indicates drift risk | Build passes with warning
OBSERVE | Telemetry only | Logged, no signal

No invariant may be unenforced.

## 3. Coverage Matrix

3.1 B4.3 - Controlled Voice Contract

Rule | CI Script | Level
Only allowed strings used | ci_verify_voice_contract.py | HARD FAIL
Skeleton legality (A/B/C/D) | same | HARD FAIL
Advice only in D | same | HARD FAIL
No actions in C | same | HARD FAIL
Language purity | same | HARD FAIL
Family theme -> B/C only | same | HARD FAIL
Escalation shape legality | same | HARD FAIL
Contract version mismatch | same | HARD FAIL

Rationale: B4.3 defines what may be said. Violations are correctness bugs.

3.2 B4.4 - Voice Drift Telemetry

Signal | CI Script | Level
Opener concentration | ci_voice_drift_report.py | WARN
Validation diversity | same | WARN
Emotional flattening | same | WARN
Structure repetition | same | WARN

Rationale: Drift is qualitative. CI surfaces risk but does not block iteration.

3.3 B4.5 - Variant Expansion Protocol

Rule | CI Coverage | Level
Expansion only after drift | Manual + CI evidence | OBSERVE
Max variants per section | ci_verify_voice_contract.py | HARD FAIL
No closure expansion | same | HARD FAIL
No new actions | same | HARD FAIL
Version bump required | Review + CI check | SOFT FAIL (post-lock)

Rationale: Expansion is human-gated. CI enforces limits, not judgment.

3.4 B5.1 / B5.2 - Selection and Memory Principles

Rule | CI Coverage | Level
No randomness | Static scan + tests | HARD FAIL
No immediate repetition | Eval diff check | SOFT FAIL
Usage <= 50% per window | Eval telemetry | WARN
Session-local memory only | Code review + tests | HARD FAIL
Window sizes respected | Unit tests | HARD FAIL

Rationale: Determinism and isolation are correctness properties. Rotation quality is design-level.

3.5 B5.3 - Deterministic Selection Algorithm

Rule | CI Coverage | Level
Same state -> same output | Replay test | HARD FAIL
Single variant selected | Eval assertion | HARD FAIL
Tie-break order respected | Unit tests | HARD FAIL
Skeleton overrides honored | Targeted tests | HARD FAIL

Rationale: B5.3 is the brain. Any deviation is a logic bug.

3.6 B6.1- B6.3 - Architecture and Control Flow

Rule | CI Coverage | Level
Single selection path | Static analysis | HARD FAIL
No bypass of selector | Tests + code scan | HARD FAIL
Memory mutated in one place | Tests | HARD FAIL
No intent -> wording coupling | Review + tests | SOFT FAIL

Rationale: Architecture violations cause long-term decay.

3.7 B6.4 - Fallback Semantics

Rule | CI Coverage | Level
Fallback hierarchy respected | Eval tests | HARD FAIL
Absolute fallback strings exact | Snapshot test | HARD FAIL
Meta emitted on fallback | Eval assertion | HARD FAIL
No state mutation on absolute fallback | Tests | HARD FAIL

Rationale: Failures must be safe and visible.

## 4. CI Execution Order (Recommended)

1. Unit tests (state, memory, determinism)
2. Short eval run
3. B4.3 contract verification (hard gate)
4. B6.4 fallback checks
5. Drift telemetry (warn-only)
6. Artifact upload (optional)

Earlier failures stop later stages.

## 5. Lock Implications

Once B6.5 is locked:
- Any new invariant must declare its CI level
- No temporary unenforced rules allowed
- CI becomes the canonical truth of correctness

Design without CI backing is considered incomplete.

## 6. What B6.5 Does NOT Do

B6.5 does not:
- Add new checks
- Decide thresholds
- Replace human review
- Tune sensitivity

It only makes enforcement explicit.
