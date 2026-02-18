import pytest
from scripts.artifact_digest import get_deterministic_json, get_sha256_digest, get_artifact_digest

def test_deterministic_json_is_stable():
    """Verify that key order doesn't change the output string."""
    d1 = {"b": 2, "a": 1, "c": {"d": 4, "e": 3}}
    d2 = {"c": {"e": 3, "d": 4}, "a": 1, "b": 2}
    assert get_deterministic_json(d1) == get_deterministic_json(d2)
    assert get_deterministic_json(d1) == '{"a":1,"b":2,"c":{"d":4,"e":3}}'

def test_deterministic_json_pretty_print():
    """Verify pretty printing works as expected."""
    data = {"b": 2, "a": 1}
    expected = '''{
  "a": 1,
  "b": 2
}'''
    assert get_deterministic_json(data, pretty=True) == expected

def test_sha256_digest_is_correct():
    """Verify SHA256 hash against a known value."""
    data = "hello world"
    expected_digest = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert get_sha256_digest(data) == expected_digest

def test_artifact_digest_is_stable():
    """Verify that the full artifact digest is stable regardless of key order."""
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    assert get_artifact_digest(d1) == get_artifact_digest(d2)

def test_artifact_digest_is_valid_sha256():
    """Verify the digest format is a valid SHA256 hex string."""
    data = {"any": "thing"}
    digest = get_artifact_digest(data)
    assert len(digest) == 64
    # Should not raise an error
    int(digest, 16)
