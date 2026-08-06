.PHONY: dev test

dev:
	PYTHONPATH=src ENVIRONMENT=development DEBUG=false \
	JWT_ALGORITHM=HS256 \
	JWT_SECRET="dev-only-jwt-secret-change-me-in-prod-please-32chars" \
	uv run uvicorn common.interfaces.http.app:create_app --factory --host 127.0.0.1 --port 8765

test:
	PYTHONPATH=src uv run pytest
