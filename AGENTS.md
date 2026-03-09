# Repository Guidelines

## Project Structure & Module Organization
- `app/`: FastAPI app code.
  - `app/main.py`: app factory + lifespan startup.
  - `app/api/routers/`: HTTP routes (`health`, `geofence`, `me`).
  - `app/services/`: business logic (notifications, geofence engine, location persistence).
  - `app/dependencies/`: request-time auth/config dependencies.
- `shared/`: cross-cutting runtime utilities (typed settings, logging, notification clients).
- `scripts/`: operational CLIs (`backup-dbs`, `backup-gdrive`, `schedule-scripts`).
- `tests/`: pytest suite for API contracts, auth behavior, and service/script logic.
- Runtime/generated artifacts:
  - `logs/` for application logs.
  - SQLite DB path and geofence mapping path are environment-configured.

## Build, Test, and Development Commands
- Install deps: `uv sync --dev`
- Run API locally (reload): `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Run all tests: `uv run pytest`
- Run focused tests:
  - `uv run pytest tests/test_geofence.py -q`
  - `uv run pytest tests/test_me_location.py -q`
- Run scripts:
  - `uv run backup-dbs`
  - `uv run backup-gdrive`
  - `uv run schedule-scripts`
- Docker local run:
  - `docker compose up --build`

## Coding Style & Naming Conventions
- Python `>=3.12`, PEP 8, 4-space indentation, and type hints for public-facing logic.
- Naming:
  - modules/functions/variables: `snake_case`
  - classes: `PascalCase`
  - constants/env keys: `UPPER_SNAKE_CASE`
- Keep routers thin; move business decisions into `app/services/*` or `shared/*`.
- Use structured API failures via `AppError` (consistent `{"error": {"code", "message"}}` shape).
- Logging:
  - use `logging.getLogger(__name__)` per module.
  - initialize global logging only once via `shared.logging.setup_logging(...)` in startup.

## Testing Guidelines
- Framework: `pytest`, with `fastapi.testclient.TestClient` and fixtures in `tests/conftest.py`.
- Test names: files `test_*.py`, functions `test_<behavior>`.
- For behavior changes, update/add tests in the same PR.
- Mock side effects (email, ntfy, SSH/WhatsApp bridge, external commands/network) to keep tests deterministic.
- Prefer contract tests for:
  - admin auth (`Authorization: Bearer <ADMIN_TOKEN>`),
  - endpoint response models,
  - geofence engine side effects and dedupe behavior.

## Commit & Pull Request Guidelines
- Use Conventional Commits:
  - `feat(scope): ...`
  - `fix(scope): ...`
  - `docs(scope): ...`
  - `refactor(scope): ...`
  - `test(scope): ...`
- Keep commits scoped and reviewable.
- PR should include:
  - purpose/problem statement,
  - what changed,
  - test evidence (or why tests were skipped),
  - config/env implications,
  - sample requests/responses for API changes.

## Documentation Voice & Audience
- Saarthi docs are for a personal project, not a multi-tenant/public product.
- Prefer a personal, practical tone over enterprise/product marketing language.
- Keep README high-level and narrative-first (what it is, why it exists, what it currently includes).
- Avoid overloading README with deep setup/runbook detail unless explicitly requested.
- Preserve the project tagline and identity: **Smart Aide for Actions, Retrieval, Tasks, Handling Information**.

## Security & Configuration
- Do not commit secrets (`.env`, tokens, credentials, private keys).
- Keep `.env.example` aligned with any new required settings.
- Validate new env vars in `shared/settings.py` to fail fast at startup.
- Protected endpoints must keep admin token guard unless intentionally changed.
- For notification channels, prefer explicit enable flags (`EMAIL_ENABLED`, `NTFY_ENABLED`, `WHATSAPP_ENABLED`) and graceful fallback when disabled.
