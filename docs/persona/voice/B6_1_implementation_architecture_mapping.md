# B6.1 - Implementation Architecture Mapping

Status: LOCKED
Depends on: B4.3, B4.4, B4.5, B5.1, B5.2, B5.3
Goal: Map the locked voice and variant system into concrete, auditable components without yet writing production code.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

This spec answers one question only: where does each responsibility live in the codebase so nothing leaks, duplicates, or fights itself?

## 1. Architectural Principles (Non-Negotiable)

These principles guide every implementation decision:
1. Single responsibility per layer
   - No component both decides intent and chooses wording
2. Voice logic is centralized
   - No ad-hoc phrasing in inference paths
3. Determinism is end-to-end
   - Same inputs -> same output, always
4. CI is authoritative
   - Anything not enforced by CI will drift
5. Design specs are upstream of code
   - Code must conform to specs, never reinterpret them

## 2. High-Level Pipeline (Conceptual)

User Input
  -> Intent Detection
  -> Emotional Skeleton Selection
  -> Voice Variant Selection (B5)
  -> Response Assembly
  -> Post-hoc Verification (CI only)

Important: Voice selection is not interleaved with intent detection or generation.

## 3. Component Breakdown (Concrete Mapping)

3.1 Intent Detection Layer (Existing)

Responsibility
- Classify user input into emotional, factual, refusal, etc.

Produces
- intent
- emotional_theme (optional)
- escalation signals

Consumes
- Raw user text only

Must NOT
- Choose wording
- Reference B4/B5 specs
- Perform rotation logic

This layer feeds B6.2 later, unchanged by voice work.

3.2 Emotional Skeleton Resolver

Responsibility
- Decide A / B / C / D
- Apply escalation rules (B3, B4)
- Latch themes (family, resignation, etc.)

Produces
- emotional_skeleton
- emotional_lang
- escalation_state
- latched_theme

Consumes
- intent
- session state
- escalation history

Must NOT
- Select variants
- Modify wording
- Perform rotation

This is the bridge between meaning and voice.

3.3 Voice Contract Loader (B4.3)

Responsibility
- Load only allowed strings
- Expose tables by skeleton, language, section

Produces
- Ordered variant lists
- Variant IDs (index-based)

Consumes
- Static contract files (B4_3_controlled_variations.md)

Must NOT
- Apply logic
- Filter variants
- Perform selection

Pure data. No intelligence.

3.4 Rotation Memory Store (B5.2)

Responsibility
- Track recent variant usage

State dimensions
- skeleton
- language
- section
- variant_id
- turn_index

Scope
- Session-local only

Operations
- read_window()
- record_usage()
- reset_on_conditions()

Must NOT
- Know drift rules
- Choose variants
- Access user text

Mechanical memory, nothing else.

3.5 Deterministic Variant Selector (B5.3)

Responsibility
- Select exactly one variant

Consumes
- skeleton
- language
- section
- variant list
- rotation memory
- window size
- escalation state
- latched theme
- turn index

Produces
- selected_variant_id
- selected_variant_text

Must
- Follow all 5 phases in B5.3
- Be fully deterministic
- Be side-effect free (except memory update)

Must NOT
- Generate text
- Modify variants
- Read prompt semantics

This is the brain of voice selection.

3.6 Response Assembler

Responsibility
- Stitch opener, validation, closure, and action (if D)

Consumes
- Selected variants per section

Produces
- Final response string

Must NOT
- Alter wording
- Add new sentences
- Reorder sections

Assembly only. No creativity.

3.7 CI Verification Layer (Offline Only)

Responsibility
- Enforce invariants: B4.3 contract legality, B4.4 drift telemetry, B5 compliance

Consumes
- Eval outputs
- Contract files

Produces
- PASS / FAIL / WARN

Must NOT
- Influence runtime behavior
- Patch results
- Auto-correct output

CI observes. Runtime acts.

## 4. Explicit Non-Couplings (Critical)

The following couplings are forbidden:
- Variant selector reading user text
- Intent detector accessing B4.3 tables
- Drift telemetry affecting runtime choice
- Memory persisting across sessions
- Skeleton resolver selecting wording

If any of these appear in code review, it is a hard stop.

## 5. Data Flow Summary (Minimal)

intent -> skeleton -> (language, escalation, theme)
       -> variant pool (B4.3)
       -> rotation memory (B5.2)
       -> variant selector (B5.3)
       -> response assembler

No shortcuts. No side channels.

## 6. What B6.1 Does NOT Do

B6.1 does not:
- Define class names
- Pick file paths
- Specify APIs
- Optimize performance
- Handle concurrency

Those belong to B6.2 and later.

## 7. Lock Readiness Check

B6.1 is ready to lock after:
- You agree with this separation
- No component feels overloaded
- Nothing feels missing conceptually


Version: B6.1.0
Date: 2026-02-10
Status: LOCKED
Upstream: B4.x, B5.1, B5.2, B5.3
