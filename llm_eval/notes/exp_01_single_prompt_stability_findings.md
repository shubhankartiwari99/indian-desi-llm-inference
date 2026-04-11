# Experiment 1 Findings

Prompt:

`Explain the importance of discipline for long-term success.`

Sample count:

`20`

## Manual Labels

Labels were applied to the final emitted responses.

- `tone`: `formal` in all 20 runs
- `cultural`: `none` in all 20 runs
- `type`: mixed across final outputs

## Empirical Probabilities

- `P(tone = formal) = 1.00`
- `P(cultural = strong_indian_context) = 0.00`
- `P(cultural = weak_indian_context) = 0.00`
- `P(cultural = none) = 1.00`
- `P(type = generic) = 0.10`
- `P(type = specific) = 0.30`
- `P(type = example_driven) = 0.60`

## Pre vs Post Rescue

- Raw unique responses: `19 / 20`
- Final unique responses: `9 / 20`
- Raw response entropy: `4.22`
- Final response entropy: `2.17`
- Stage change rate: `0.65`
- Unique-response delta: `10`
- Entropy delta: `2.05`

## Observations

1. The raw model layer is highly variable: 19 unique pre-rescue outputs across 20 runs.
2. The runtime layer substantially collapses that variability: final outputs drop to 9 unique responses, with one explanatory template dominating 60% of runs.
3. The final emitted behavior still stays fully non-Indian in context, so this prompt does not trigger cultural localization even after rescue.

## Hypothesis

The inference pipeline is enforcing a partially deterministic explanatory template through rescue and shaping logic. It does not eliminate all variation, but it significantly compresses the raw distribution and masks much of the underlying model stochasticity.

## Refined Conclusion

The earlier “perfect stability” interpretation was incorrect. The stronger result is that the evaluation pipeline was measuring a mixture of model behavior and runtime intervention. Valid probabilistic analysis requires separating pre-rescue model outputs from final post-processed outputs.
