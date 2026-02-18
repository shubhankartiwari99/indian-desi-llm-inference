import json
import hashlib

def get_deterministic_json(data: dict, pretty: bool = False) -> str:
    """
    Serializes a dictionary to a canonical JSON string.
    - Keys are sorted.
    - No indentation or extra whitespace unless 'pretty' is True.
    - Non-ASCII characters are not escaped.
    """
    if pretty:
        return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

def get_sha256_digest(data: str) -> str:
    """
    Computes the SHA256 hash of a string and returns it as a hex digest.
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def get_artifact_digest(data: dict) -> str:
    """
    Computes a deterministic SHA256 digest for a dictionary artifact.
    """
    json_string = get_deterministic_json(data)
    return get_sha256_digest(json_string)
