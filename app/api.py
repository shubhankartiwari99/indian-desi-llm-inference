from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.guardrails.guardrail_classifier import classify_user_input
from app.guardrails.guardrail_escalation import compute_guardrail_escalation
from app.guardrails.guardrail_strategy import apply_guardrail_strategy
from app.inference import InferenceEngine
from app.tone.tone_calibration import calibrate_tone

app = FastAPI(
    title="Indian Desi Multilingual LLM",
    description="Inference API for the Indian Desi Multilingual LLM",
    version="0.1.0",
)

MAX_PROMPT_LENGTH = 10000
ALLOWED_LANGS = {"en", "hi"}
_REQUEST_KEYS = {"prompt", "emotional_lang"}
_TRACE_KEYS = ("turn", "guardrail", "skeleton", "tone_profile", "selection", "replay_hash")

engine: InferenceEngine | None = None


def _get_engine() -> InferenceEngine:
    global engine
    if engine is None:
        model_dir = os.environ.get("MODEL_DIR")
        if not model_dir:
            raise RuntimeError("MODEL_DIR environment variable must be set.")
        engine = InferenceEngine(model_dir)
    return engine


def _validate_generate_request(payload: dict[str, Any]) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid request body.")

    if set(payload.keys()) - _REQUEST_KEYS:
        raise ValueError("Unexpected fields in request.")

    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be a string.")

    if not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError("Prompt exceeds maximum length.")

    lang = payload.get("emotional_lang", "en")
    if lang is None:
        lang = "en"

    if not isinstance(lang, str):
        raise ValueError("Invalid emotional_lang.")

    if lang not in ALLOWED_LANGS:
        raise ValueError("Unsupported emotional_lang.")

    return {"prompt": prompt, "emotional_lang": lang}


def _build_api_trace(prompt: str, emotional_lang: str) -> dict[str, Any]:
    guardrail_result = classify_user_input(prompt)
    guardrail_action = apply_guardrail_strategy(guardrail_result)
    base_skeleton = "A"
    skeleton_after_guardrail = compute_guardrail_escalation(guardrail_result, base_skeleton)
    if guardrail_result.risk_category == "SELF_HARM_RISK":
        skeleton_after_guardrail = "C"

    trace: dict[str, Any] = {
        "turn": {
            "emotional_turn_index": 1,
            "intent": "emotional",
            "emotional_lang": emotional_lang,
            "previous_skeleton": base_skeleton,
            "resolved_skeleton": skeleton_after_guardrail,
            "skeleton_transition": f"{base_skeleton}->{skeleton_after_guardrail}",
            "transition_legal": True,
            "escalation_state": "none",
            "latched_theme": None,
            "signals": {
                "overwhelm": False,
                "resignation": False,
                "guilt": False,
                "wants_action": False,
            },
        },
        "guardrail": {
            "classifier_version": guardrail_result.guardrail_schema_version,
            "strategy_version": guardrail_action.guardrail_strategy_version,
            "risk_category": guardrail_result.risk_category,
            "severity": guardrail_result.severity,
            "override": bool(guardrail_action.override),
        },
        "skeleton": {
            "base": base_skeleton,
            "after_guardrail": skeleton_after_guardrail,
        },
        "selection": {
            "eligible_count": 0,
            "selected_variant_indices": {},
        },
    }

    if not guardrail_action.override:
        try:
            trace["tone_profile"] = calibrate_tone(
                skeleton_after_guardrail,
                guardrail_result.severity,
                guardrail_result.risk_category,
            )
        except ValueError:
            pass

    replay_subset: dict[str, Any] = {
        "emotional_lang": emotional_lang,
        "skeleton_after_guardrail": skeleton_after_guardrail,
        "guardrail": trace["guardrail"],
        "selection": trace["selection"],
    }
    if "tone_profile" in trace:
        replay_subset["tone_profile"] = trace["tone_profile"]
    canonical = json.dumps(replay_subset, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    trace["replay_hash"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    sealed_trace: dict[str, Any] = {}
    for key in _TRACE_KEYS:
        if key in trace:
            sealed_trace[key] = trace[key]
    return sealed_trace


@app.post("/generate")
async def generate_text(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid request body.", "code": "INVALID_INPUT"})

    try:
        validated = _validate_generate_request(payload)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc), "code": "INVALID_INPUT"})

    try:
        runtime_engine = _get_engine()
        response_text, _meta = runtime_engine.generate(validated["prompt"], return_meta=True)
        response_payload = {
            "response_text": response_text,
            "trace": _build_api_trace(validated["prompt"], validated["emotional_lang"]),
        }
        return JSONResponse(status_code=200, content=response_payload)
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Inference failed.", "code": "INFERENCE_FAILED"})
