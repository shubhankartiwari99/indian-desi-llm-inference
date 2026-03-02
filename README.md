# AI Systems Research Platform

## Overview
A deterministic LLM evaluation and behavioral control framework designed to study inference stability, entropy effects, and regression drift in multilingual environments.

## Core Capabilities
- Dual-mode inference (Probabilistic vs Deterministic)
- Stability regression suite
- Assertion-based behavior validation
- Snapshot tracking
- Global drift severity scoring
- Structured prompt routing
- Mode isolation architecture

## Architecture

* **Frontend**: Next.js + Tailwind
* **Backend**: FastAPI + Transformers/llama.cpp
* **Inference**: Controlled generation parameters (GGUF-backed)
* **Evaluation**: Snapshot delta comparison via deterministic baseline scoring

## Research Goals
- Model reliability analysis
- Entropy behavior mapping
- Multilingual consistency enforcement
- Structured output enforcement (future)
- Semantic drift measurement (future)