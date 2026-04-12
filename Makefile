.PHONY: dev backend frontend

dev:
	@echo "Starting full-stack evaluation environment..."
	@make -j 2 backend frontend

backend:
	uvicorn backend.app:app --reload --port 8000

frontend:
	cd frontend && npm run dev
