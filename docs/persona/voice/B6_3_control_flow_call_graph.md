# B6.3 - Control Flow and Call Graph

Status: LOCKED
Depends on: B6.1 (Architecture Mapping), B6.2 (State Structures), B5.3 (Selection Algorithm)
Goal: Define the exact runtime execution order and call boundaries so voice logic is applied once, centrally, and cannot be bypassed or duplicated.

Scope: Runtime inference only
Non-goal: API shape, class names, async handling, performance tuning

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

## 1. Core Guarantee (Hard Requirement)

For any emotional response:

There is exactly one path from user input to final text, and it passes through the voice system exactly once.

If a response bypasses variant selection, that is a correctness bug.

## 2. High-Level Call Flow (Linear, No Branching)

handle_user_input()
  -> detect_intent()
    -> resolve_emotional_skeleton()
      -> update_session_state()
        -> select_voice_variants()
          -> assemble_response()
            -> return final_text

No function above may call a function below it.

## 3. Step-by-Step Control Flow

3.1 handle_user_input(user_text)

Responsibility
- Entry point only
- Orchestrates the pipeline

Must
- Pass user text forward unchanged
- Hold session context

Must NOT
- Inspect emotional content
- Generate text
- Apply rules

3.2 detect_intent(user_text)

Produces
- intent
- emotional_theme (optional)
- escalation_signal (optional)

Consumes
- Raw user text only

Must NOT
- Access session state
- Access B4/B5 specs
- Select skeleton or variants

Output is immutable after this point.

3.3 resolve_emotional_skeleton(intent, session_state, signals)

Produces
- emotional_skeleton (A/B/C/D or null)
- emotional_lang
- escalation_state
- latched_theme

Consumes
- Intent output
- Previous SessionVoiceState

Must
- Apply escalation rules
- Apply family/resignation latching
- Decide skeleton once

Must NOT
- Choose wording
- Rotate variants
- Access B4.3 tables

This is the last semantic decision point.

3.4 update_session_state(...)

Responsibility
- Mutate SessionVoiceState only

Actions
- Increment emotional_turn_index (if emotional)
- Apply hard or partial resets (B6.2 section 6)
- Update last_skeleton, latched_theme, escalation_state

Must NOT
- Read variant tables
- Choose variants
- Generate text

State changes happen before selection.

3.5 select_voice_variants(session_state, skeleton, lang)

This is the B5 system.

Sub-steps (fixed order)

load_contract_variants()
  -> for each section:
       -> deterministic_variant_selector()
         -> update_rotation_memory()

Consumes
- SessionVoiceState
- Skeleton, language
- B4.3 tables

Produces
- {section -> selected_variant_text}

Must
- Follow B5.3 phases exactly
- Be fully deterministic
- Update rotation memory only via allowed writes

Must NOT
- Read user text
- Reinterpret intent
- Add new strings
- Skip sections

3.6 assemble_response(selected_variants)

Responsibility
- Mechanical composition only

Rules
- Fixed section order per skeleton
- No rewriting
- No omission
- No insertion

Examples
- A/B/C: opener + validation + closure
- D: opener + action + closure

Must NOT
- Modify text
- Apply heuristics
- Add punctuation beyond spacing

3.7 Return Final Text

At this point:
- All decisions are complete
- CI invariants apply
- No further mutation allowed

## 4. Forbidden Control Flow Patterns (Hard Stops)

The following are never allowed:
- Variant selector called inside intent detection
- Skeleton resolver accessing B4.3 strings
- Response assembler choosing variants
- Drift telemetry influencing runtime behavior
- Rotation memory mutated outside selector
- Multiple selection passes per turn

Any of these is an architecture violation.

## 5. Call Graph (Condensed)

handle_user_input
  -> detect_intent
    -> resolve_emotional_skeleton
      -> update_session_state
        -> select_voice_variants
          -> load_contract_variants
          -> deterministic_variant_selector (per section)
          -> update_rotation_memory
            -> assemble_response

No back-edges. No shortcuts.

## 6. Determinism Boundary

Determinism is guaranteed if and only if:
- All randomness is excluded
- SessionVoiceState is the only mutable state
- B4.3 is the only string source

If output differs across runs:
- Either state leaked
- Or control flow was violated

## 7. CI Observability Alignment

CI checks observe outputs after assemble_response.

CI may:
- Validate legality (B4.3)
- Warn on drift (B4.4)
- Enforce invariants (B5)

CI must never:
- Influence control flow
- Alter state
- Patch outputs

Lock statement

Control flow is the skeleton of correctness. If the flow is right, voice stays human. If the flow is wrong, no amount of rules will save it.

Version: B6.3.0
Date: 2026-02-10
Status: LOCKED
Upstream: B6.1, B6.2, B5.x, B4.x