import os
from inference.gguf_backend import GGUFBackend

MODEL_PATH = os.getenv("MODEL_PATH", "models/nanbeige-4.1-3b-q4kam.gguf")

backend = GGUFBackend(model_path=MODEL_PATH)

def build_prompt(mode: str, user_prompt: str) -> str:
    if mode == "factual":
        system = (
            "You are a formal educational assistant. "
            "Use professional tone. Do not use slang. "
            "Avoid casual expressions like 'buddy' or 'yaar'."
        )
    elif mode == "emotional":
        system = (
            "You are a compassionate and emotionally supportive assistant."
        )
    elif mode == "mixed":
        system = (
            "You may use a casual conversational tone."
        )
    else:
        system = ""

    if system:
        return system + "\n\nUser: " + user_prompt
    return user_prompt

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Indian Desi Multilingual LLM - Deterministic Backend",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    prompt: str
    mode: str = ""
    temperature: float = 0.0
    top_p: float = 1.0
    max_new_tokens: int = 512

@app.post("/generate")
def generate(request: GenerateRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    full_prompt = build_prompt(request.mode, request.prompt)
    
    result = backend.generate(
        prompt=full_prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        repeat_penalty=1.1,
    )
    
    return {
        "response_text": result["text"],
        "latency_ms": 0,          # Stubbed since frontend falls back to perf delta
        "input_tokens": 0,        # Stubbed
        "output_tokens": 0        # Stubbed
    }

import time
import random

@app.post("/infer")
def infer(request: GenerateRequest):
    """
    Mock endpoint providing rich structured output for the local frontend demo, ensuring 
    constant fast display of metrics without local GPU dependence.
    """
    time.sleep(1.0)
    prompt_lower = request.prompt.lower()
    
    if "yaar" in prompt_lower or "desi" in prompt_lower or "bhai" in prompt_lower:
        raw_out = "I hear you yaar, it sounds really frustrating."
        final_out = "I hear you, it sounds really frustrating."
        action = "lexical_cleansing"
        c_ratio = 0.51
    elif "upi" in prompt_lower or "startup" in prompt_lower:
        raw_out = f"India's {request.prompt} is booming. It's crazy!"
        final_out = f"India has seen substantial growth regarding: {request.prompt}."
        action = "explanatory_floor"
        c_ratio = 0.28
    else:
        raw_out = f"Response to: {request.prompt}. Quite easy."
        final_out = f"Detailed response to your query regarding {request.prompt}."
        action = "semantic_preservation"
        c_ratio = 0.85
        
    return {
        "raw_output": raw_out,
        "final_output": final_out,
        "metrics": {
            "entropy_raw": round(random.uniform(4.0, 4.5), 2),
            "entropy_final": round(random.uniform(2.0, 2.5), 2),
            "collapse_ratio": c_ratio,
            "stage_change_rate": 0.65
        },
        "metadata": {
            "latency_ms": 1000,
            "tokens": 42,
            "source": "inference_shaping_pipeline"
        },
        "intervention_type": action
    }
