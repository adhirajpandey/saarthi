# Repository Guidelines

## Project Structure & Module Organization
Saarthi is a Python 3.12 project with two execution surfaces:
- `app/`: FastAPI runtime (`app/main.py`), routers under `app/api/routers/`, and domain logic in `app/services/`.
- `scripts/`: operational CLIs (`backup-dbs`, `backup-gdrive`, `schedule-scripts`).
- `shared/`: cross-cutting settings, logging, and notification clients.
- `tests/`: pytest suite for API, services, scripts, and config behavior.
- `docs/`: architecture, API, and script docs.
- `data/` and `logs/`: runtime artifacts and logs (not source modules).

## Build, Test, and Development Commands
- `uv sync --group dev`: install runtime + dev dependencies.
- `uv run uvicorn app.main:app --reload`: run API locally with hot reload.
- `uv run pytest`: run full test suite.
- `uv run pytest tests/test_geofence_engine.py -q`: run a focused test file quickly.
- `uv run backup-dbs` / `uv run backup-gdrive` / `uv run schedule-scripts`: run operational scripts.
- `docker compose up --build`: start containerized environment.

## Coding Style & Naming Conventions
- Follow existing Python style: 4-space indentation, type hints where practical, and concise docstrings/comments.
- Keep FastAPI routers thin; place business logic in `app/services/` and shared concerns in `shared/`.
- Use `snake_case` for functions/variables/modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for env/config keys.
- No dedicated formatter/linter is currently enforced in `pyproject.toml`; match surrounding code and keep imports organized.

## Testing Guidelines
- Framework: `pytest`.
- Test files use `test_*.py`; test functions use `test_*`.
- Add or update tests for every behavior change, especially service logic and script failure paths.
- Prefer targeted runs during development, then run the full suite before opening a PR.

## Commit & Pull Request Guidelines
- Use Conventional Commit style seen in history: `type(scope): imperative subject` (for example, `fix(schedule): handle permission failures gracefully`).
- Keep commits atomic and scoped to one concern.
- PRs should include: purpose, key file changes, verification commands run, and linked issue references (`#123`) when available.
- Include sample request/response or logs when API/script behavior changes materially.

## Security & Configuration Tips
- Keep secrets in `.env`; do not commit credentials or tokens.
- Use `config.example.py` / `.env.example` as templates for new configuration keys.
- Validate env/config changes with tests (`tests/test_config.py`) before merging.

## Important Notes
1. Always follow existing project patterns, architecture, and naming conventions by understanding and going through the codebase.
2. Always try to complete the tasks by making minimal code change
3. If a task appears to require a major refactor, architectural change, or convention-breaking update, stop and ask the user for explicit approval before proceeding.
4. Always list files in the `docs/` directory and read all of them before planning or making any change.
5. Do not update files in `docs/` in between tasks by default; only update docs if the user explicitly asks.
6. Once a change/task/request seems complete, or if the user explicitly asks, always prompt the user with suggested docs changes.
7. When updating docs, always follow the existing `docs/` structure and conventions.
8. Keep `README.md` thin and functional; do not change its structure.
