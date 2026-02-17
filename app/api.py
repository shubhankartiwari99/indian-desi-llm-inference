import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.inference import InferenceEngine

app = FastAPI(
    title="Indian Desi Multilingual LLM",
    description="Inference API for the Indian Desi Multilingual LLM",
    version="0.1.0",
)

model_dir = os.environ["MODEL_DIR"]
engine = InferenceEngine(model_dir)

class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 128


class GenerateResponse(BaseModel):
    response: str


@app.post("/generate", response_model=GenerateResponse)
def generate_text(request: GenerateRequest):
    try:
        output = engine.generate(
            request.prompt,
            max_new_tokens=request.max_new_tokens
        )
        return GenerateResponse(response=output)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail="Inference failed")
