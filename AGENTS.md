# Repository Guidelines

## Project Structure & Module Organization
- `app/`: FastAPI application code (entrypoint in `app/main.py`, routers in `app/api/routers/`, dependencies/services by feature).
- `shared/`: cross-cutting modules used by both API and scripts (settings, logging, notifications).
- `scripts/`: operational CLIs (`backup_dbs`, `backup_gdrive`, `schedule_scripts`).
- `tests/`: pytest suite (`test_*.py`) for config, API behavior, and geofence flows.
- Runtime artifacts live in `logs/`; environment templates are in `.env.example`.

## Build, Test, and Development Commands
- `uv sync --dev`: install runtime + dev dependencies from `pyproject.toml`/`uv.lock`.
- `uv run uvicorn app.main:app --reload`: run API locally with auto-reload.
- `uv run pytest`: run all tests.
- `uv run pytest tests/test_geofence.py -q`: run a focused test file.
- `uv run backup-dbs` / `uv run backup-gdrive` / `uv run schedule-scripts`: run packaged automation scripts.

## Coding Style & Naming Conventions
- Target Python `>=3.12`; follow PEP 8 with 4-space indentation and type hints where practical.
- Module/function names: `snake_case`; classes: `PascalCase`; constants/env keys: `UPPER_SNAKE_CASE`.
- Keep routers thin (`app/api/routers/*`), move logic into `app/services/*` or `shared/*`.
- Use concise docstrings for non-obvious behavior and structured error responses via `AppError`.
- Prefer per-module `logging.getLogger(__name__)` and only call `shared.logging.setup()` for global configuration; do not import a singleton logger from `shared.logging`.

## Testing Guidelines
- Framework: `pytest` with `fastapi.testclient.TestClient` and fixtures in `tests/conftest.py`.
- Name files `test_*.py` and test functions `test_<behavior>`.
- Mock external side effects (email, network, backup commands) to keep tests deterministic.
- Add/adjust tests with every behavior change, especially auth (`Authorization: Bearer <ADMIN_TOKEN>`) and endpoint contracts.
- Include focused service/script unit tests (e.g., geofence notification result paths, script config generation) before merging behavior changes.

## Commit & Pull Request Guidelines
- Follow Conventional Commits seen in history: `feat(scope): ...`, `fix(scope): ...`, `refactor(scope): ...`, `test(scope): ...`.
- Keep commits focused; use imperative, scoped subjects (example: `fix(backup.py): handle rclone timeout`).
- PRs should include: purpose, key changes, test evidence (`uv run pytest` output summary), config/env updates, and linked issue/PR when applicable.
- For API changes, include sample request/response or screenshots of docs/testing client.

## Security & Configuration Tips
- Never commit `.env` secrets; start from `.env.example`.
- Rotate `ADMIN_TOKEN` and notification credentials before sharing environments.
- Validate all new env vars in shared settings to fail fast on startup.
