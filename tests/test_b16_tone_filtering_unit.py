from copy import deepcopy

from app.inference import _filter_variants_by_tone


def test_exact_match_includes_tagged_variant():
    variants = [{"id": "v1", "tone_tags": ["warm_engaged"]}]
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert filtered == variants


def test_different_tone_excludes_tagged_variant_when_universal_exists():
    variants = [
        {"id": "v1", "tone_tags": ["firm_boundary"]},
        {"id": "v2"},
    ]
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert filtered == [{"id": "v2"}]


def test_missing_tone_tags_is_universal():
    variants = [{"id": "v1"}]
    filtered = _filter_variants_by_tone(variants, "grounded_calm")
    assert filtered == variants


def test_none_tone_tags_is_universal():
    variants = [{"id": "v1", "tone_tags": None}]
    filtered = _filter_variants_by_tone(variants, "grounded_calm")
    assert filtered == variants


def test_empty_tone_tags_is_universal():
    variants = [{"id": "v1", "tone_tags": []}]
    filtered = _filter_variants_by_tone(variants, "grounded_calm")
    assert filtered == variants


def test_mixed_pool_keeps_matching_and_universal_only():
    variants = [
        {"id": "v1", "tone_tags": ["warm_engaged"]},
        {"id": "v2"},
        {"id": "v3", "tone_tags": ["firm_boundary"]},
        {"id": "v4", "tone_tags": ["warm_engaged", "grounded_calm"]},
    ]
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert filtered == [
        {"id": "v1", "tone_tags": ["warm_engaged"]},
        {"id": "v2"},
        {"id": "v4", "tone_tags": ["warm_engaged", "grounded_calm"]},
    ]


def test_fallback_to_full_pool_when_only_mismatched_tags():
    variants = [
        {"id": "v1", "tone_tags": ["firm_boundary"]},
        {"id": "v2", "tone_tags": ["grounded_calm"]},
    ]
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert filtered == variants
    assert filtered is variants


def test_empty_input_returns_same_list_object():
    variants = []
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert filtered == []
    assert filtered is variants


def test_determinism_same_input_same_output():
    variants = [
        {"id": "v1", "tone_tags": ["warm_engaged"]},
        {"id": "v2"},
        {"id": "v3", "tone_tags": ["firm_boundary"]},
    ]
    first = _filter_variants_by_tone(variants, "warm_engaged")
    second = _filter_variants_by_tone(variants, "warm_engaged")
    assert first == second


def test_no_mutation_of_input_pool():
    variants = [
        {"id": "v1", "tone_tags": ["warm_engaged"]},
        {"id": "v2"},
        {"id": "v3", "tone_tags": ["firm_boundary"]},
    ]
    original = deepcopy(variants)
    _ = _filter_variants_by_tone(variants, "warm_engaged")
    assert variants == original


def test_order_preserved_after_filtering():
    variants = [
        {"id": "a", "tone_tags": ["warm_engaged"]},
        {"id": "b", "tone_tags": ["firm_boundary"]},
        {"id": "c"},
        {"id": "d", "tone_tags": ["warm_engaged"]},
    ]
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert [v["id"] for v in filtered] == ["a", "c", "d"]


def test_multiple_tags_match_any():
    variants = [{"id": "v1", "tone_tags": ["empathetic_soft", "grounded_calm"]}]
    filtered = _filter_variants_by_tone(variants, "grounded_calm")
    assert filtered == variants


def test_non_empty_filter_returns_new_list_reference():
    variants = [
        {"id": "v1", "tone_tags": ["warm_engaged"]},
        {"id": "v2"},
        {"id": "v3", "tone_tags": ["firm_boundary"]},
    ]
    filtered = _filter_variants_by_tone(variants, "warm_engaged")
    assert filtered == [
        {"id": "v1", "tone_tags": ["warm_engaged"]},
        {"id": "v2"},
    ]
    assert filtered is not variants
