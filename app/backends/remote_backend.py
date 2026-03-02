import os

import requests

REMOTE_URL = os.environ.get("REMOTE_MODEL_URL", "")


def remote_generate(prompt: str, max_new_tokens: int = 96) -> str:
    if not REMOTE_URL:
        raise RuntimeError(
            "REMOTE_MODEL_URL environment variable must be set for remote backend."
        )
    response = requests.post(
        REMOTE_URL.rstrip("/") + "/generate",
        json={"prompt": prompt, "max_new_tokens": max_new_tokens},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return (data.get("response_text") or data.get("response") or "").strip()


class RemoteBackend:
    def __init__(self, url: str = ""):
        self.url = (url or REMOTE_URL).rstrip("/")
        if not self.url:
            raise RuntimeError(
                "REMOTE_MODEL_URL environment variable must be set for remote backend."
            )
        self.endpoint = self.url if self.url.endswith("/generate") else self.url + "/generate"

    def generate(self, prompt: str, max_new_tokens: int = 96) -> str:
        response = requests.post(
            self.endpoint,
            json={"prompt": prompt, "max_new_tokens": max_new_tokens},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return (data.get("response_text") or data.get("response") or "").strip()
