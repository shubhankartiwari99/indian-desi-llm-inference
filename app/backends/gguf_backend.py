from llama_cpp import Llama

class GGUFBackend:

    def __init__(self, model_path: str):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=384,        # reduce KV cache to avoid swap on 8GB M1
            n_threads=6,      # leave 2 cores for macOS
            n_gpu_layers=8,   # reduce Metal buffers on 8GB
            verbose=False,
        )

    def generate(self, prompt: str, max_new_tokens: int = 128, stop: list[str] = None) -> str:
        stop_list = stop if stop else ["</s>"]
        response = self.llm(
            prompt,
            max_tokens=max_new_tokens,
            temperature=0.0,
            top_p=1.0,
            repeat_penalty=1.1,
            stop=stop_list
        )

        return response["choices"][0]["text"].strip()
