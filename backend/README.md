# Backend Setup

## Install
```bash
pip install -r requirements.txt
```

For Apple Silicon (Metal support):
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal
```

## Model
Place GGUF model inside `backend/models/`

## Run
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
