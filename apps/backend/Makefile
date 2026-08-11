.PHONY: dev test generate-jwt-keys

dev:
	PYTHONPATH=src ENVIRONMENT=development DEBUG=false \
	JWT_ALGORITHM=RS256 \
	uv run uvicorn common.interfaces.http.app:create_app --factory --host 127.0.0.1 --port 8765

test:
	PYTHONPATH=src uv run pytest

generate-jwt-keys:
	PYTHONPATH=src uv run python scripts/generate-jwt-keys.py --output-dir ./secrets

seed-demo:
	PYTHONPATH=src uv run python scripts/seed_demo.py

seed-mock:
	PYTHONPATH=src uv run python scripts/seed_demo.py --mock
