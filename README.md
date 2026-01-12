# Saarthi - Smart Aide for Actions, Retrieval, Tasks, Handling Information

Saarthi is a smart aide designed to assist with various tasks through a conversational interface. It can perform actions, retrieve information, and handle tasks, making it a powerful tool for enhancing productivity.

## Getting Started

Follow these steps to get the Saarthi API up and running on your local machine.

### 1. Configure Environment Variables

Create a `.env` file in the root directory by copying the example file:

```bash
cp .env.example .env
```

Now, open the `.env` file and update the variables with your specific configurations.

### 2. Install Dependencies

This project uses `uv` for package management. To install the required dependencies, run:

```bash
uv sync
```

### 3. Create Log Directory

Create a directory to store logs:

```bash
mkdir logs
```

### 4. Run the Application

You can now start the Saarthi API using `uvicorn`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-config log-conf.yml
```

The API will be accessible at `http://localhost:8000`.

## Project Structure

The project is organized as follows:

```
├── app/                # Main application directory
│   ├── routers/        # API endpoint definitions
│   ├── services/       # Business logic and services
│   ├── utils/          # Utility functions
│   ├── auth.py         # Authentication logic
│   ├── config.py       # Application configuration
│   ├── main.py         # FastAPI application entry point
│   └── models.py       # Pydantic models
├── scripts/            # Utility scripts
│   ├── backup-dbs/     # Database backup scripts
│   ├── backup-gdrive/  # Google Drive backup scripts
│   └── schedule-scripts/ # Systemd timer generation
├── logs/               # Log files
├── .env                # Environment variables
├── .env.example        # Example environment variables
├── config.yml          # General configuration
├── docker-compose.yml  # Docker Compose configuration
├── Dockerfile          # Dockerfile for building the image
├── pyproject.toml      # Project metadata and dependencies
└── README.md           # This file
```

## API Endpoints

The following are the main API endpoints available:

- **`/health`**: Health check endpoint.
- **`/login`**: User authentication.
- **`/chat`**: Main chat interface for interacting with Saarthi.

