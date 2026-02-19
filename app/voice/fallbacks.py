#-*- coding: utf-8 -*-
from typing import Dict

from app.voice.assembler import assemble_response
from app.voice.contract_loader import get_variants_for
from app.voice.errors import VoiceContractError


ALLOWED_SKELETONS = {"A", "B", "C", "D"}
ALLOWED_LANGUAGES = {"en", "hi", "hinglish"}


def sections_for_skeleton(skeleton: str) -> tuple[str, ...]:
    if skeleton == "D":
        return ("opener", "action", "closure")
    return ("opener", "validation", "closure")


def _resolve_skeleton(skeleton: str) -> str:
    return skeleton if skeleton in ALLOWED_SKELETONS else "A"


def _resolve_language(language: str) -> str:
    return language if language in ALLOWED_LANGUAGES else "en"


def _first_contract_variant(skeleton: str, language: str, section: str) -> str:
    try:
        return get_variants_for(skeleton, language, section)[0]
    except (VoiceContractError, IndexError):
        return get_variants_for(skeleton, "en", section)[0]


def _contract_fallback_text(skeleton: str, language: str) -> str:
    resolved_skeleton = _resolve_skeleton(skeleton)
    resolved_language = _resolve_language(language)
    selected: Dict[str, str] = {}
    for section in sections_for_skeleton(resolved_skeleton):
        selected[section] = _first_contract_variant(resolved_skeleton, resolved_language, section)
    return assemble_response(resolved_skeleton, selected)

ABSOLUTE_FALLBACK = {skeleton: _contract_fallback_text(skeleton, "en") for skeleton in sorted(ALLOWED_SKELETONS)}

SKELETON_SAFE_EN_FALLBACK = {skeleton: _contract_fallback_text(skeleton, "en") for skeleton in sorted(ALLOWED_SKELETONS)}

def build_skeleton_local_fallback(skeleton: str, language: str) -> str:
    return _contract_fallback_text(skeleton, language)
