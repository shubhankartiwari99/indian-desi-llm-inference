#-*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, List, Any

from app.contract_validation import validate_contract_structure
from app.tone.tone_calibration import TONE_PROFILES
from app.voice.errors import VoiceContractError

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs/persona/voice_contract.json"

ALLOWED_SKELETONS = {"A", "B", "C", "D"}
ALLOWED_LANGUAGES = {"en", "hi", "hinglish"}


def get_loader() -> Dict[str, Any]:
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        contract = json.load(f)
    validate_contract_structure(contract, set(TONE_PROFILES))
    return contract


def get_contract_version() -> str:
    return get_loader().get("contract_version", "unknown")


def _normalize_variant_entry(
    raw_variant: Any,
    *,
    skeleton: str,
    language: str,
    section: str,
    index: int,
) -> Dict[str, Any]:
    if isinstance(raw_variant, str):
        return {"text": raw_variant, "tone_tags": None}

    if not isinstance(raw_variant, dict):
        raise VoiceContractError(
            f"Variant {index} for {skeleton}/{language}/{section} must be str or object"
        )

    text = raw_variant.get("text")
    if not isinstance(text, str):
        raise VoiceContractError(
            f"Variant {index} for {skeleton}/{language}/{section} has invalid text field"
        )

    tone_tags = raw_variant.get("tone_tags", None)
    if tone_tags is not None:
        if not isinstance(tone_tags, list) or any(not isinstance(tag, str) for tag in tone_tags):
            raise VoiceContractError(
                f"Variant {index} for {skeleton}/{language}/{section} has invalid tone_tags"
            )

    return {"text": text, "tone_tags": tone_tags}


def get_variant_entries_for(skeleton: str, language: str, section: str) -> List[Dict[str, Any]]:
    if skeleton not in ALLOWED_SKELETONS:
        raise VoiceContractError(f"Skeleton '{skeleton}' is not allowed.")
    if language not in ALLOWED_LANGUAGES:
        raise VoiceContractError(f"Language '{language}' is not allowed.")

    contract = get_loader()
    try:
        raw_variants = contract["skeletons"][skeleton][language][section]
    except KeyError:
        raise VoiceContractError(f"Variants not found for {skeleton}/{language}/{section}")

    if not isinstance(raw_variants, list):
        raise VoiceContractError(f"Variants payload for {skeleton}/{language}/{section} must be a list")

    return [
        _normalize_variant_entry(
            raw_variant,
            skeleton=skeleton,
            language=language,
            section=section,
            index=index,
        )
        for index, raw_variant in enumerate(raw_variants)
    ]


def get_variants_for(skeleton: str, language: str, section: str) -> List[str]:
    entries = get_variant_entries_for(skeleton, language, section)
    return [entry["text"] for entry in entries]
