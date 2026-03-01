import pytest

from app.guardrails.guardrail_override_selector import select_guardrail_variant


def test_b18_returns_first_element():
    variants = ["A", "B", "C"]
    assert select_guardrail_variant(variants) == "A"


def test_b18_raises_on_empty_list():
    with pytest.raises(ValueError):
        select_guardrail_variant([])


def test_b18_empty_error_message_is_stable():
    with pytest.raises(ValueError) as exc:
        select_guardrail_variant([])
    assert str(exc.value) == "Guardrail override selection received empty variant list."


def test_b18_does_not_mutate_input():
    variants = ["X", "Y"]
    original = list(variants)
    select_guardrail_variant(variants)
    assert variants == original


def test_b18_deterministic_across_calls():
    variants = ["one", "two", "three"]
    assert select_guardrail_variant(variants) == select_guardrail_variant(variants)


def test_b18_stable_under_identical_lists():
    v1 = ["alpha", "beta"]
    v2 = ["alpha", "beta"]
    assert select_guardrail_variant(v1) == select_guardrail_variant(v2)


def test_b18_single_element_list():
    variants = ["solo"]
    assert select_guardrail_variant(variants) == "solo"


def test_b18_ignores_tail_values():
    variants = ["first", "second", "third", "fourth"]
    assert select_guardrail_variant(variants) == "first"


def test_b18_no_sorting_behavior():
    variants = ["zebra", "alpha", "beta"]
    assert select_guardrail_variant(variants) == "zebra"


def test_b18_duplicate_values_keep_first_position():
    variants = ["repeat", "x", "repeat"]
    assert select_guardrail_variant(variants) == "repeat"


def test_b18_preserves_whitespace_in_first_variant():
    variants = ["  keep-me  ", "trim-me"]
    assert select_guardrail_variant(variants) == "  keep-me  "


def test_b18_accepts_empty_string_first():
    variants = ["", "fallback"]
    assert select_guardrail_variant(variants) == ""


def test_b18_long_list_still_first():
    variants = [f"v{i}" for i in range(100)]
    assert select_guardrail_variant(variants) == "v0"


def test_b18_repeated_calls_do_not_change_input_order():
    variants = ["a", "b", "c"]
    expected = list(variants)
    for _ in range(10):
        select_guardrail_variant(variants)
    assert variants == expected


def test_b18_numeric_like_strings():
    variants = ["10", "2", "1"]
    assert select_guardrail_variant(variants) == "10"
