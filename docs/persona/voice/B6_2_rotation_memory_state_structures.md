# B6.2 - Rotation Memory and State Structures

Status: LOCKED
Depends on: B5.1 (Selection Principles), B5.2 (Windowing), B5.3 (Algorithm), B6.1 (Architecture Mapping)
Applies to: Emotional Skeletons A / B / C / D
Goal: Define the exact state objects and memory structures required to support deterministic variant selection - no more, no less.

Note: This spec is intentionally written to be machine-parsable. This prevents future helpful prose edits that break enforcement.

This spec defines what state exists, where it lives, and how it resets. It does not define algorithms (already locked) or code APIs.

## 1. Design Constraints (Hard)

All state defined here must obey:
1. Session-local only
   - No persistence across sessions
2. Mechanical, not semantic
   - No embeddings, no meanings, no text analysis
3. Minimal
   - If a field is not required by B5.3, it must not exist
4. Auditable
   - State must be printable/debuggable without interpretation
5. Deterministic
   - Same state -> same variant choice

## 2. Top-Level State Container

2.1 SessionVoiceState

This is the only long-lived state object for voice behavior.

SessionVoiceState
├── rotation_memory
├── escalation_state
├── latched_theme
├── emotional_turn_index
└── last_skeleton

Field definitions

Field | Type | Purpose
rotation_memory | RotationMemory | Tracks recent variant usage
escalation_state | enum | none | escalating | latched
latched_theme | enum | null | family | resignation | null
emotional_turn_index | int | Counts emotional turns only
last_skeleton | A|B|C|D|null | Used for reset logic

## 3. Rotation Memory (Core Structure)

3.1 RotationMemory

Rotation memory tracks variant usage, not text.

RotationMemory
└── pools: Dict[PoolKey, VariantUsageWindow]

3.2 PoolKey (Indexing Key)

Each independent rotation pool is keyed by:

PoolKey
├── skeleton: A | B | C | D
├── language: en | hinglish | hi
└── section: opener | validation | action | closure

Important
- Each (skeleton, language, section) has its own window
- No cross-pool influence is allowed

## 4. Variant Usage Window

4.1 VariantUsageWindow

VariantUsageWindow
├── window_size: int
├── history: List[VariantUsage]

4.2 VariantUsage

VariantUsage
├── variant_id: int
├── turn_index: int

Notes
- variant_id is the index from the B4.3 table
- turn_index is the emotional turn index, not global turn count
- No timestamps, no clocks, no wall-time

## 5. Window Semantics (B5.2 Mapping)

- History is append-only
- On read:
  - Only the last window_size entries are considered
- On write:
  - New usage is appended
- Pruning:
  - Lazy (logical windowing), not eager deletion

This guarantees:
- Deterministic scoring
- Simple debugging
- No mutation surprises

## 6. Memory Reset Rules (State Transitions)

6.1 Hard Reset (All Pools Cleared)

Trigger when any of the following occur:
- Emotional intent -> non-emotional
- New session
- Explicit session reset
- Escalation resolves fully (C -> A)

Effect:

rotation_memory = empty
emotional_turn_index = 0
last_skeleton = null
latched_theme = null

## 6.2 Partial Reset (Selective Pools)

Trigger conditions and effects:

Trigger | Reset Scope
Skeleton increases (A->B, B->C) | Clear pools for new skeleton only
Latched theme changes | Clear pools for affected skeletons
Language change | Clear pools for that language

Example
- A -> B escalation:
  - Clear (B, *, *) pools
  - Keep A history intact

## 7. Emotional Turn Index

7.1 emotional_turn_index
- Incremented only when:
  - intent == emotional
- Used for:
  - Variant scoring (recency)
  - Tie-breaking
- Reset only on:
  - Hard reset

Non-emotional turns:
- Do not increment
- Do not affect rotation memory

## 8. What Is Explicitly NOT Stored

To prevent scope creep, the following must never exist in state:
- Raw response text
- Prompt text
- Variant strings
- Drift metrics
- Scores or probabilities
- Random seeds
- User identifiers
- Cross-session counters

If it is not required by B5.3, it does not belong here.

## 9. Debug and CI Visibility (Design Requirement)

All state objects must be serializable to a plain dict for:
- CI inspection
- Debug logs
- Unit tests

No hidden state. No closures. No magic.

## 10. Coherence Check With Previous Specs

- B5.1: supports deterministic, intentional selection
- B5.2: exact windowing semantics implemented
- B5.3: all required inputs present, no extras
- B6.1: responsibilities cleanly isolated

Nothing is overloaded. Nothing is missing.


