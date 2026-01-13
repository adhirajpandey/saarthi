# Saarthi - Smart Aide for Actions, Retrieval, Tasks, Handling Information

Saarthi is a personal, ever-evolving project that unites different tools, scripts, APIs, and experiments in one place. Currently it has a web application and a set of utility scripts. It will grow over time as I build things to solve problems, automate stuff, and try out new ideas.

---
## Project Structure

```
├── app/                  # Main Web Application
│   ├── routers/          # API endpoints (Health, Auth, Chat)
│   ├── services/         # Business logic (Agents, Tools)
│   ├── utils/            # Utilities (Logging, Config)
│   └── main.py           # App Entrypoint
├── scripts/              # Utility Scripts
│   ├── backup-dbs/       # Database Backups
│   ├── backup-gdrive/    # Google Drive Sync
│   └── schedule-scripts/ # Systemd Timer Generator
├── .env.example          # Environment variables template
├── log-conf.yml          # Logging configuration
└── pyproject.toml        # Dependencies (uv)
```

---

## Part 1: Web Application

### 1. Description
The core of Saarthi is a **FastAPI** web application that acts as the intelligent interface. It provides health monitoring, handles user interactions, manages authentication, and orchestrates AI agents to perform tasks. It is designed to be extensible, allowing new capabilities to be plugged in via services and tools.

### 2. Contents & Services
The web application allows interaction through the following main interfaces:
- **Health Monitoring**: Endpoints to ensure the system is operational.
- **Authentication**: Secure entry points for user verification.
- **Chat Interface**: A conversational endpoint to interact with Saarthi's agents.

### 3. Setup Steps

Follow these steps to get the API running locally.

**Step 1: Configure Environment Variables**
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Update the `.env` file with your specific configurations (API keys, Database URLs, etc.).

**Step 2: Install Dependencies**
This project uses `uv` for fast package management.
```bash
uv sync
```

**Step 3: Run the Application**
Start the server using `uvicorn`:
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-config log-conf.yml
```
The API will be available at `http://localhost:8000`.

### 4. Service Details

The application is structured into modular services located in `app/`:

- **Routers** (`app/routers/`):
  - Handles the HTTP request/response cycle.
  - Defines endpoints for `/health`, `/login`, and `/chat`.
  
- **Agent Service** (`app/services/agents.py`):
  - Contains the core logic for AI agent instantiation and orchestration.
  - Manages the lifecycle of agent interactions.

- **Tools Service** (`app/services/tools.py`):
  - Defines the capabilities available to the agents (e.g., searching, calculation, specific data retrieval).
  - Acts as the bridge between the AI and external systems.

- **Instructions Service** (`app/services/instructions.py`):
  - Manages system prompts and behavioral instructions for different agent personas.

---

## Part 2: Utility Scripts

### 1. Description
Saarthi includes a suite of standalone Python scripts designed for background automation, system maintenance, and data preservation. These scripts often run independently of the web server (e.g., via cron or systemd).

### 2. Contents & Services
- **Database Backups**: Automated dumping and S3 uploading for Postgres databases.
- **Drive Sync**: Syncing Google Drive folders to S3 for redundant storage.
- **Task Scheduler**: A manager to generate and control systemd timers for the above scripts.

### 3. Service Details

#### A. Database Backup (`scripts/backup-dbs/`)
- **Purpose**: Dumps and uploads Postgres databases to S3 for backup.
- **Features**:
  - Runs `pg_dump` for multiple databases (`vidwiz`, `trackcrow`).
  - Uploads timestamped SQL artifacts to AWS S3.
  - Performs sanity checks and cleans up local files.
- **Config**: Requires `AWS_ACCESS_KEY`, `AWS_SECRET_ACCESS_KEY`, and DB URLs in `.env`.
- **Usage**: `python scripts/backup-dbs/backup.py`

#### B. Google Drive Backup (`scripts/backup-gdrive/`)
- **Purpose**: Creates cloud redundancy for personal files using rclone.
- **Features**:
  - Syncs "PERSONAL" and "PROFESSIONAL" folders to S3.
  - Performs incremental updates using `rclone` wrapper.
  - Lightweight and optimized for background execution.
- **Config**: Requires pre-configured rclone remotes (`personal-drive` and `dwaar-s3`).
- **Usage**: `python scripts/backup-gdrive/backup.py`

#### C. Schedule Scripts (`scripts/schedule-scripts/`)
- **Purpose**: Automates script execution via systemd timers "Set it and forget it".
- **Features**:
  - Generates `.service` and `.timer` files from JSON config.
  - Automatically handles systemd daemon reload and enablement.
  - Centralized management of run frequencies.
- **Config**: Define tasks and schedules in `scripts/schedule-scripts/config.json`.
- **Usage**: `sudo python scripts/schedule-scripts/main.py`

