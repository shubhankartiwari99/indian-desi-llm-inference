Indian Desi LLM Inference Engine

Public API Contract — Version 1.0.0 (B20)

⸻

1. Overview

This document defines the frozen public API surface of the engine core (v1.0.0).

The engine guarantees:
	•	Deterministic responses for identical inputs.
	•	Deterministic replay hash generation.
	•	Multilingual guardrail parity (English and Hindi).
	•	Contract-backed guardrail override enforcement.
	•	Strict input validation.
	•	Sealed response shape.
	•	No internal state leakage.

This contract is considered stable for engine v1.0.0.

⸻

2. Endpoint: /generate

Method

POST

⸻

Request Body

{
  "prompt": "string (1–10000 characters)",
  "emotional_lang": "en" | "hi"
}

Field Definitions
	•	prompt (required)
	•	Must be string.
	•	Must not be empty or whitespace-only.
	•	Maximum length: 10000 characters.
	•	emotional_lang (optional)
	•	Allowed values: "en" or "hi".
	•	Defaults to "en" if omitted.
	•	Any other value results in 400 error.

Invalid Input Behavior

Invalid requests return:

{
  "error": "Error message",
  "code": "INVALID_INPUT"
}

HTTP Status: 400

⸻

3. Response Body

On success:

{
  "response_text": "string",
  "trace": {
    "turn": { ... },
    "guardrail": { ... },
    "skeleton": { ... },
    "tone_profile": "string (optional)",
    "selection": { ... },
    "replay_hash": "sha256:..."
  }
}

Top-Level Fields
	•	response_text
	•	trace

No additional fields are exposed.

⸻

4. Determinism Guarantee

For identical input payloads:
	•	response_text will be identical.
	•	trace will be identical.
	•	replay_hash will be identical.

The engine does not:
	•	Use randomness.
	•	Use timestamps.
	•	Inject request IDs.
	•	Inject nondeterministic metadata.

⸻

5. Guardrail Behavior

Guardrail overrides:
	•	May replace response_text.
	•	May escalate skeleton.
	•	Are deterministic.
	•	Are contract-backed.

Self-harm (HIGH / CRITICAL) is always resolved via skeleton C.

⸻

6. Multilingual Support

Supported languages:
	•	English (“en”)
	•	Hindi (“hi”)

Guardrail resolution occurs in requested language.
If language block missing:
	•	English fallback is used.
	•	If English missing → runtime failure (hard error).

⸻

7. Replay Hash

replay_hash is:
	•	Deterministic
	•	Canonical
	•	Stable across identical inputs
	•	Sensitive to:
	•	Guardrail category
	•	Severity
	•	Skeleton
	•	Tone profile
	•	Emotional language

⸻

8. Endpoint: /version

Method

GET

Response

{
  "engine_name": "indian-desi-llm-inference-core",
  "engine_version": "1.0.0",
  "release_stage": "B20"
}

This endpoint is deterministic and contains no dynamic fields.

⸻

9. Error Handling

Two error types exist:

400 — INVALID_INPUT

{
  "error": "Message",
  "code": "INVALID_INPUT"
}

500 — INFERENCE_FAILED

{
  "error": "Inference failed.",
  "code": "INFERENCE_FAILED"
}

No internal stack traces are exposed.

⸻

10. Engine Freeze Status

This document reflects engine version 1.0.0 (B20).

Changes to request or response shape constitute a breaking change and require version increment.
