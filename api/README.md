# Semranko FastAPI Migration

This folder contains a full FastAPI migration of the original Node.js API.

## Features

- Equivalent route surface under `/api`
- JWT auth (`Authorization: Bearer <token>`)
- SQLAlchemy ORM mapped to existing Prisma/Postgres tables
- Redis queue + RQ worker for rank-check jobs
- Same response style: `{ success, message, data }`

## Setup

1. Create a virtual environment and install packages:

```bash
cd fastapi_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy environment variables:

```bash
cp .env.example .env
```

3. Ensure Postgres + Redis are running (you can use root `docker-compose.yml`).

## Run API

```bash
cd fastapi_app
source .venv/bin/activate
python run.py
```

## Run Worker

```bash
cd fastapi_app
source .venv/bin/activate
python -m app.workers.rank_worker
```

## Notes

- Existing database schema is reused; no destructive DB changes are applied.
- Random rank lookup behavior from the Node worker is preserved.
