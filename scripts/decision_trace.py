from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Mapping, Optional

from app.guardrails.guardrail_classifier import classify_user_input
from app.guardrails.guardrail_strategy import apply_guardrail_strategy
from app.voice.contract_loader import get_contract_version, get_loader
from scripts.artifact_digest import get_deterministic_json, get_sha256_digest


DECISION_TRACE_VERSION = "14.4"
REPLAY_HASH_PREFIX = "sha256:"

LEGAL_TRANSITIONS = {
    "A": {"A", "B", "C"},
    "B": {"B", "C"},
    "C": {"C", "A"},
    "D": {"D"},
}

SIGNAL_KEYS = ("overwhelm", "resignation", "guilt", "wants_action")


def _canonical_json(obj: Mapping[str, object]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _compute_contract_fingerprint() -> str:
    contract_data = get_loader()
    canonical_contract = get_deterministic_json(contract_data)
    return get_sha256_digest(canonical_contract)


def _ordered_bool_map(keys: tuple[str, ...], raw: Optional[Mapping[str, object]]) -> OrderedDict:
    data = raw or {}
    return OrderedDict((k, bool(data.get(k, False))) for k in keys)


def _ordered_selected_indices(raw: Optional[Mapping[str, object]]) -> OrderedDict:
    data = raw or {}
    ordered = OrderedDict()
    for key in ("opener", "validation", "action", "closure"):
        if key in data:
            ordered[key] = int(data[key])
    for key in sorted(data.keys()):
        if key not in ordered:
            ordered[key] = int(data[key])
    return ordered


def _normalize_fallback(raw: Optional[Mapping[str, object]]) -> Optional[OrderedDict]:
    if raw is None:
        return None
    return OrderedDict(
        [
            ("level", int(raw.get("level", 0))),
            ("reason", str(raw.get("reason", "none"))),
            ("absolute", bool(raw.get("absolute", False))),
            ("state_restored", bool(raw.get("state_restored", False))),
        ]
    )


def _transition_legal(previous_skeleton: str, resolved_skeleton: str) -> bool:
    allowed = LEGAL_TRANSITIONS.get(previous_skeleton, set())
    return resolved_skeleton in allowed


def compute_replay_hash(trace: Mapping[str, object]) -> str:
    turn = trace.get("turn", {})
    skeleton = trace.get("skeleton", {})
    selection = trace.get("selection", {})
    fallback = trace.get("fallback")
    guardrail = trace.get("guardrail", {})

    subset = OrderedDict(
        [
            ("contract_fingerprint", trace.get("contract_fingerprint")),
            ("emotional_turn_index", turn.get("emotional_turn_index")),
            ("intent", turn.get("intent")),
            ("skeleton_after_guardrail", skeleton.get("after_guardrail")),
            ("emotional_lang", turn.get("emotional_lang")),
            ("escalation_state", turn.get("escalation_state")),
            ("latched_theme", turn.get("latched_theme")),
            (
                "guardrail",
                OrderedDict(
                    [
                        ("classifier_version", guardrail.get("classifier_version")),
                        ("strategy_version", guardrail.get("strategy_version")),
                        ("risk_category", guardrail.get("risk_category")),
                        ("severity", guardrail.get("severity")),
                        ("override", bool(guardrail.get("override", False))),
                    ]
                ),
            ),
            ("fallback", None if fallback is None else OrderedDict([("level", fallback.get("level")), ("absolute", bool(fallback.get("absolute", False)))])),
            ("selected_variant_indices", selection.get("selected_variant_indices", {})),
        ]
    )

    payload = _canonical_json(subset)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{REPLAY_HASH_PREFIX}{digest}"


def build_decision_trace(
    *,
    user_input: str,
    intent: str,
    emotional_lang: str,
    emotional_turn_index: int,
    previous_skeleton: str,
    resolved_skeleton: str,
    skeleton_after_guardrail: Optional[str] = None,
    escalation_state: str = "none",
    latched_theme: Optional[str] = None,
    signals: Optional[Mapping[str, object]] = None,
    eligible_count: int = 0,
    selected_variant_indices: Optional[Mapping[str, object]] = None,
    window_size: int = 0,
    window_fill: int = 0,
    immediate_repeat_blocked: bool = False,
    fallback: Optional[Mapping[str, object]] = None,
    cultural: Optional[Mapping[str, object]] = None,
    invariants: Optional[Mapping[str, object]] = None,
    contract_version: Optional[str] = None,
    contract_fingerprint: Optional[str] = None,
) -> OrderedDict:
    guardrail_result = classify_user_input(user_input or "")
    guardrail_action = apply_guardrail_strategy(guardrail_result)

    prev = str(previous_skeleton or "A")
    base_skeleton = str(resolved_skeleton or "A")
    after_guardrail = str(skeleton_after_guardrail or base_skeleton)
    transition = f"{prev}->{after_guardrail}"
    transition_legal = _transition_legal(prev, after_guardrail)

    turn_block = OrderedDict(
        [
            ("emotional_turn_index", int(emotional_turn_index)),
            ("intent", str(intent)),
            ("emotional_lang", str(emotional_lang)),
            ("previous_skeleton", prev),
            ("resolved_skeleton", after_guardrail),
            ("skeleton_transition", transition),
            ("transition_legal", bool(transition_legal)),
            ("escalation_state", str(escalation_state)),
            ("latched_theme", latched_theme),
            ("signals", _ordered_bool_map(SIGNAL_KEYS, signals)),
        ]
    )

    guardrail_block = OrderedDict(
        [
            ("classifier_version", guardrail_result.guardrail_schema_version),
            ("strategy_version", guardrail_action.guardrail_strategy_version),
            ("risk_category", guardrail_result.risk_category),
            ("severity", guardrail_result.severity),
            ("override", bool(guardrail_action.override)),
        ]
    )

    skeleton_block = OrderedDict(
        [
            ("base", base_skeleton),
            ("after_guardrail", after_guardrail),
        ]
    )

    selection_block = OrderedDict(
        [
            ("eligible_count", int(eligible_count)),
            ("selected_variant_indices", _ordered_selected_indices(selected_variant_indices)),
        ]
    )

    rotation_block = OrderedDict(
        [
            ("window_size", int(window_size)),
            ("window_fill", int(window_fill)),
            ("immediate_repeat_blocked", bool(immediate_repeat_blocked)),
        ]
    )

    cultural_data = cultural or {}
    cultural_block = OrderedDict(
        [
            ("family_theme_active", bool(cultural_data.get("family_theme_active", False))),
            ("pressure_context_detected", bool(cultural_data.get("pressure_context_detected", False))),
            ("collectivist_reference_used", bool(cultural_data.get("collectivist_reference_used", False))),
            ("direct_advice_suppressed", bool(cultural_data.get("direct_advice_suppressed", False))),
        ]
    )

    invariant_data = invariants or {}
    invariants_block = OrderedDict(
        [
            ("selector_called_once", bool(invariant_data.get("selector_called_once", False))),
            ("rotation_bounded", bool(invariant_data.get("rotation_bounded", False))),
            ("deterministic_selector", bool(invariant_data.get("deterministic_selector", False))),
        ]
    )

    trace = OrderedDict(
        [
            ("decision_trace_version", DECISION_TRACE_VERSION),
            ("contract_version", contract_version or get_contract_version()),
            ("contract_fingerprint", contract_fingerprint or _compute_contract_fingerprint()),
            ("turn", turn_block),
            ("guardrail", guardrail_block),
            ("skeleton", skeleton_block),
            ("selection", selection_block),
            ("rotation", rotation_block),
            ("fallback", _normalize_fallback(fallback)),
            ("cultural", cultural_block),
            ("invariants", invariants_block),
        ]
    )
    trace["replay_hash"] = compute_replay_hash(trace)
    return trace
