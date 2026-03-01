from typing import List


def select_guardrail_variant(variants: List[str]) -> str:
    """
    Deterministically selects a guardrail override variant.

    Invariant:
    - Returns the first element of the provided list.
    - Raises ValueError if the list is empty.
    - Does not mutate the input list.
    """
    if not variants:
        raise ValueError("Guardrail override selection received empty variant list.")

    # Deterministic invariant: first element wins.
    return variants[0]
