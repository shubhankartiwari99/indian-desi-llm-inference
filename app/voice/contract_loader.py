#-*- coding: utf-8 -*-
import json
from pathlib import Path
from typing import Dict, List, Any

from app.voice.errors import VoiceContractError

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs/persona/voice_contract.json"

ALLOWED_SKELETONS = {"A", "B", "C", "D"}
ALLOWED_LANGUAGES = {"en", "hi", "hinglish"}


def get_loader() -> Dict[str, Any]:
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_contract_version() -> str:
    return get_loader().get("contract_version", "unknown")


def get_variants_for(skeleton: str, language: str, section: str) -> List[str]:
    if skeleton not in ALLOWED_SKELETONS:
        raise VoiceContractError(f"Skeleton '{skeleton}' is not allowed.")
    if language not in ALLOWED_LANGUAGES:
        raise VoiceContractError(f"Language '{language}' is not allowed.")
    
    contract = get_loader()
    try:
        return contract["skeletons"][skeleton][language][section]
    except KeyError:
        raise VoiceContractError(f"Variants not found for {skeleton}/{language}/{section}")
