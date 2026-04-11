# Experiment 2 Findings

Prompts:

- Baseline: `Explain discipline for success.`
- India-conditioned: `Explain discipline for success in India.`

Sample count:

- `10` runs per prompt

## Cultural Probability By Prompt And Stage

Baseline prompt:

- `P(cultural != none | baseline, raw) = 0.00`
- `P(cultural != none | baseline, final) = 0.00`

India-conditioned prompt:

- `P(cultural = strong_indian_context | India, raw) = 0.30`
- `P(cultural != none | India, raw) = 0.30`
- `P(cultural = strong_indian_context | India, final) = 0.30`
- `P(cultural = weak_indian_context | India, final) = 0.10`
- `P(cultural != none | India, final) = 0.40`

## Observations

1. The baseline prompt stayed fully non-cultural in both raw and final stages.
2. The India-conditioned prompt introduced Indian context at the raw stage, so the conditioning signal is present in model behavior.
3. The runtime did not suppress that localization in this sample. Final Indian-context rate increased from `0.30` to `0.40`.

## Interpretation

For an explicit India-conditioned prompt, the runtime still acts as a shaping operator, but not by removing localization. In this small sample it preserved strong Indian references and slightly increased total Indian-context rate by adding one weakly localized final answer.

## Caveat

This experiment used `10` runs per prompt and manual cultural labeling. Treat the result as directional, not final.
