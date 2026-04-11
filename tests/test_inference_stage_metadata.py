from app.inference import InferenceEngine


def test_pack_populates_final_and_runtime_stage_metadata():
    engine = InferenceEngine.__new__(InferenceEngine)

    text, meta = engine._pack(
        "Response: Final answer.",
        {
            "pre_rescue_response": "raw answer",
            "post_rescue": True,
        },
        True,
    )

    assert text == "Final answer."
    assert meta["pre_rescue_response"] == "raw answer"
    assert meta["final_response"] == "Final answer."
    assert meta["runtime_intervention"] is True
    assert meta["response_stage"] == "post_rescue"


def test_inherit_stage_meta_preserves_pre_rescue_response():
    engine = InferenceEngine.__new__(InferenceEngine)

    inherited = engine._inherit_stage_meta(
        {"pre_rescue_response": "raw answer"},
        {"source": "explanatory_floor"},
    )

    assert inherited["pre_rescue_response"] == "raw answer"
    assert inherited["source"] == "explanatory_floor"
