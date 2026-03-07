# AGENTS.md

## SYSTEM PROMPT
You are a **Senior Software Engineer**. You prioritize **correctness** and **maintainability** to ensure long term success of the project.

---

## 1. Project Context
- **Project Name:** Saarthi
- **Project Description:** Saarthi is a personal project containing a **FastAPI Web Application** and a collection of **Utility Scripts** for automation.
- **Components:**
  - **Web App:** FastAPI, Health/Monitoring, Admin Token Auth, Geofence.
  - **Scripts:** Database backups, Google Drive sync, Systemd scheduling.
- **Frameworks:** FastAPI, Pydantic, Boto3 (AWS)
- **Language:** Python (Requires-python >= 3.12)
- **Package Manager:** uv

---

## 2. Executable Commands
Strictly use these commands. **Do not guess flags.**

- **Install:**
  `uv sync`

- **Run Web App (Dev):**
  `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`

- **Run Scripts:**
  Run from project root:
  - `uv run backup-dbs`
  - `uv run backup-gdrive`
  - `uv run schedule-scripts` (use `sudo` for systemd writes)

- **Test:**
  Run tests using pytest `uv run pytest -v`

---

## 3. Interaction Rules
- **Stop & Read:** If you do not see a function definition or file content, ask to read it.
  Do **not** guess imports or arguments.
- **Chain of Thought:** Before writing code for complex logic, explain your plan in **3 bullet points**.
- **No Breaking Changes:** Do not remove existing features or change public APIs without explicit permission.

---

## 4. Coding Standards (Boundaries)

### Always Do
- Maintain clear separation between **Web Application** (`app/`) and **Scripts** (`scripts/`).
- Use **async/await** for asynchronous operations in web app.
- Add **strict type annotations** using **Pydantic models** (no `Any`) in web app.
- Ensure there is no edge case of bug specially in the scripts.
- Use `.env` for secrets (AWS keys, DB URLs) - never hardcode them.
- Update `.env.example` file whenever a new environment variable is added.
- Always check if any updates are required in `README.md` and `AGENTS.md` files.
- Always run tests cases to do sanity check after some major change.

### Never Do
- Never introduce **new dependencies** without asking.
- Never leave `print` or unnecessary `logger.debug` in production code.
- Never mix script logic directly into the web app handlers without a proper service abstraction.
- Never make too long functions which perform multiple tasks.

---

## 5. Directory Map
### Web Application (`app/`)
- `app/api/routers/` - API endpoints (Health, Geofence).
- `app/dependencies/` - FastAPI dependencies (Admin token auth).
- `app/config/` - Application configuration assembly.
- `app/services/` - Business logic:
  - `email.py`: Email notifications.
- `app/utils/` - App-only utility helpers (Limiter, Timezone, compatibility wrappers).
- `app/models.py` - Pydantic data models.

### Shared Infrastructure (`shared/`)
- `shared/config/` - Env loading and env var helpers.
- `shared/logging/` - Centralized logging setup.
- `shared/notifications/` - Notification providers (Email, Ntfy).

### Utility Scripts (`scripts/`)
- `scripts/backup_dbs/` - Postgres backup to S3 (`main.py`).
- `scripts/backup_gdrive/` - Google Drive sync to S3 (`main.py`, requires `rclone`).
- `scripts/schedule_scripts/` - Systemd timer generator (`main.py`, `config.json`).
