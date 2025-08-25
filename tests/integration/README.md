# Integration tests

What this covers:
- Boots the real FastAPI app with lifespan.
- Overrides DB to SQLite in-memory, disables Redis and Weaviate, and injects a fake OIDC user.
- Calls real endpoints using httpx.AsyncClient.

How to run:
- Use the existing task runner: `poetry run task test` or only integration: `poetry run pytest -q tests/integration`.

Notes:
- Cortex requests are patched per-test to avoid network calls.
- The DB is re-created in-memory for the session; tests should be order-agnostic.
