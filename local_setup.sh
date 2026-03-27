#!/usr/bin/env bash
set -e

# ── 1. Check .env exists ──────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "ERROR: .env file not found."
  echo "Create one based on .env.docker, replacing 'db' with 'localhost' and 'minio' with 'localhost'."
  exit 1
fi

# ── 2. Start db and minio ─────────────────────────────────────────────────────
echo "Starting db and minio..."
docker compose up -d db minio

# ── 3. Wait for PostgreSQL to be ready ────────────────────────────────────────
echo "Waiting for PostgreSQL..."
until docker compose exec db pg_isready -U lupe -q; do
  sleep 1
done
echo "PostgreSQL ready."

# ── 4. Activate virtualenv if present ────────────────────────────────────────
if [ -d .venv ]; then
  source .venv/bin/activate
elif [ -d venv ]; then
  source venv/bin/activate
fi

# ── 5. Install dependencies ───────────────────────────────────────────────────
echo "Installing dependencies..."
pip install -r requirements.txt -q

# ── 6. Run migrations ─────────────────────────────────────────────────────────
echo "Running migrations..."
alembic upgrade head

# ── 7. Start the API ──────────────────────────────────────────────────────────
echo "Starting API..."
uvicorn app.main:app --reload
