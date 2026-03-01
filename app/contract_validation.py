from __future__ import annotations

from typing import Any


VALID_SKELETONS = {"A", "B", "C", "D"}

VALID_GUARDRAIL_CATEGORIES = {
    "self_harm",
    "abuse",
    "jailbreak",
    "extremism",
    "system_probe",
    "data_extraction",
    "manipulation",
}


def validate_contract_structure(
    contract: dict[str, Any],
    allowed_tone_profiles: set[str],
) -> None:
    if not isinstance(contract, dict):
        raise ValueError("Contract must be a dictionary.")

    skeletons = contract.get("skeletons")
    if not isinstance(skeletons, dict):
        raise ValueError("Missing or invalid 'skeletons' block.")

    for skeleton_key in skeletons:
        if skeleton_key not in VALID_SKELETONS:
            raise ValueError(f"Invalid skeleton key: {skeleton_key}")

    if "C" not in skeletons:
        raise ValueError("Skeleton C must exist.")

    if "A" not in skeletons:
        raise ValueError("Skeleton A must exist.")

    _validate_required_guardrails(skeletons)

    for skeleton_key, skeleton_block in skeletons.items():
        if not isinstance(skeleton_block, dict):
            raise ValueError(f"Skeleton '{skeleton_key}' must be a dictionary.")

        for lang_key, lang_block in skeleton_block.items():
            if not isinstance(lang_block, dict):
                raise ValueError(
                    f"Language block '{lang_key}' under skeleton '{skeleton_key}' must be a dictionary."
                )

            guardrail_block = lang_block.get("guardrail")
            if guardrail_block is None:
                continue

            if not isinstance(guardrail_block, dict):
                raise ValueError(
                    f"'guardrail' under {skeleton_key}.{lang_key} must be a dictionary."
                )

            for category_key, variants in guardrail_block.items():
                if category_key not in VALID_GUARDRAIL_CATEGORIES:
                    raise ValueError(f"Invalid guardrail category: {category_key}")

                _validate_variant_list(
                    skeleton_key,
                    lang_key,
                    category_key,
                    variants,
                    allowed_tone_profiles,
                )


def _validate_required_guardrails(skeletons: dict[str, Any]) -> None:
    try:
        _ = skeletons["C"]["en"]["guardrail"]["self_harm"]
    except Exception as exc:
        raise ValueError("Skeleton C must contain en.guardrail.self_harm.") from exc

    try:
        _ = skeletons["A"]["en"]["guardrail"]["jailbreak"]
        _ = skeletons["A"]["en"]["guardrail"]["abuse"]
    except Exception as exc:
        raise ValueError(
            "Skeleton A must contain en.guardrail.jailbreak and en.guardrail.abuse."
        ) from exc


def _validate_variant_list(
    skeleton_key: str,
    lang_key: str,
    category_key: str,
    variants: Any,
    allowed_tone_profiles: set[str],
) -> None:
    if not isinstance(variants, list) or not variants:
        raise ValueError(f"{skeleton_key}.{lang_key}.{category_key} must be a non-empty list.")

    for entry in variants:
        if isinstance(entry, str):
            continue

        if not isinstance(entry, dict):
            raise ValueError(f"Invalid variant entry in {skeleton_key}.{lang_key}.{category_key}.")

        text = entry.get("text")
        if not isinstance(text, str):
            raise ValueError(
                f"Variant entry missing valid 'text' in {skeleton_key}.{lang_key}.{category_key}."
            )

        tone_tags = entry.get("tone_tags")
        if tone_tags is None:
            continue

        if not isinstance(tone_tags, list):
            raise ValueError(
                f"'tone_tags' must be list in {skeleton_key}.{lang_key}.{category_key}."
            )

        for tag in tone_tags:
            if not isinstance(tag, str):
                raise ValueError(
                    f"Invalid tone tag type in {skeleton_key}.{lang_key}.{category_key}."
                )

            if tag not in allowed_tone_profiles:
                raise ValueError(
                    f"Unknown tone profile '{tag}' in {skeleton_key}.{lang_key}.{category_key}."
                )
