# Architecture Overview

## Two-Plane System Design
The platform is intentionally split into two distinct operational planes:

1. **Exploration Plane (Probabilistic)**: A traditional LLM chat interface configured to measure entropy effects under dynamic sampling (`top_p`, `temperature`). Used primarily for baseline discovery.
2. **Regression Core (Deterministic)**: A heavily locked inference state where generation parameters default to maximal determinism (`top_p = 1`, `temperature = 0`). Used to systematically isolate semantic drift.

## Latency Scoring Exclusion
Latency fluctuations are primarily governed by localized hardware conditions rather than model degeneration. While tracked as a tertiary metric for operational monitoring, it is strictly excluded from driving the `stabilityDriftFlag` to prevent false positive regression alerts. We strictly score against output token consistency and text bounds.

## Behavioral Assertions
Pure token-exactness metrics fail to protect against linguistic bleed (e.g. slang bleeding into factual generation) even when length parity is achieved. The Assertion Engine enforces deterministic rules over generated text at runtime (e.g., verifying `[\u0900-\u097F]` constraint blocks vs pure Latin). Any behavior assertion failure natively overrides structural similarity checks.

## Snapshot System
Provides an irrefutable JSON-based log (`stability_snapshots.jsonl`) of execution loops across different checkpoints. Crucial for tracing fine-tuning regressions and model context window stability across time boundaries.

## Engine Abstraction
The inference logic (`gguf_backend.py`) is deliberately detached from the overarching conversational context arrays found in typical applications. This guarantees the LLM respects constrained execution isolation—system prompt and generation loop exist explicitly defined per-call, preventing memory bleeds between test subjects. Weight artifacts (`models/*`) are strictly excluded from source control.
