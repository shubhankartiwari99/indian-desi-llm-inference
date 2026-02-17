#-*- coding: utf-8 -*-
from typing import Dict


def assemble_response(skeleton: str, selected_variants: Dict[str, str]) -> str:
    """
    Assembles the final response from the selected variants.
    """
    # This is a simplified version of the logic.
    # In a real system, this would be more complex.
    if skeleton == "D":
        return f"{selected_variants['opener']} {selected_variants['action']} {selected_variants['closure']}"
    return f"{selected_variants['opener']} {selected_variants['validation']} {selected_variants['closure']}"
