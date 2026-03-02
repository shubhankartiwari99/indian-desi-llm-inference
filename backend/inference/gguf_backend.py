from llama_cpp import Llama
from typing import Dict, Any


class GGUFBackend:

    def __init__(self, model_path: str):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=384,
            n_threads=6,
            n_gpu_layers=8,
            verbose=False,
        )

    def generate(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        repeat_penalty: float = 1.1,
        stop: list = None
    ) -> Dict[str, Any]:

        if stop is None:
            stop = ["</s>"]

        response = self.llm(
            prompt,
            max_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            stop=stop,
        )

        return {
            "text": response["choices"][0]["text"].strip()
        }
