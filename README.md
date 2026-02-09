# Indian Desi Multilingual LLM — Inference

This repository contains the inference and application layer
for the Indian Desi Multilingual LLM.

The model is trained and packaged via Kaggle notebooks
and consumed here for application-level usage.

> Training notebooks live on Kaggle.  
> This repository focuses only on inference, APIs, and apps.

## Persona Safety CI

This repo enforces emotional persona invariants via CI:
- Family-related emotional sequences never invoke the base model.
- Escalation paths forbid advice or exercises.

See `scripts/ci_verify_results.py` and `tests/test_family_theme_invariant.py`.

The CI job is configured in `.github/workflows/ci.yml` and runs a short
evaluation to keep checks fast (<~3 minutes).