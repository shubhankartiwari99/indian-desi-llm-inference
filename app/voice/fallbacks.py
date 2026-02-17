#-*- coding: utf-8 -*-
from typing import Dict

ABSOLUTE_FALLBACK = {
    "A": "I hear you.",
    "B": "I hear you.",
    "C": "I hear you.",
    "D": "I hear you.",
}

SKELETON_SAFE_EN_FALLBACK = {
    "A": "I hear you.",
    "B": "I hear you.",
    "C": "I hear you.",
    "D": "I hear you.",
}

def build_skeleton_local_fallback(skeleton: str, language: str) -> str:
    return "I hear you."

def sections_for_skeleton(skeleton: str) -> tuple[str, ...]:
    if skeleton == "D":
        return ("opener", "action", "closure")
    return ("opener", "validation", "closure")
