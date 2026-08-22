#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
REPO_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_DIR/semrankoapp"

REDIS_CONTAINER="semranko-redis"
REDIS_URL="redis://127.0.0.1:6379/0"

LOCAL_ENV_FILE="$PROJECT_DIR/fastapi_app/.env.local"

FASTAPI_LOG="/tmp/semranko-uvicorn.log"
RQ_LOG="/tmp/semranko-rq-worker.log"
FRONTEND_LOG="/tmp/semranko-frontend.log"

FASTAPI_PID=""
WORKER_SUPERVISOR_PID=""
FRONTEND_PID=""
SHUTTING_DOWN=0

echo ""
echo "=========================================="
echo "       Semranko Local Development"
echo "=========================================="
echo "Backend:  $PROJECT_DIR"
echo "Frontend: $FRONTEND_DIR"
echo ""

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

fail() {
  echo "✗ $1"
  exit 1
}

wait_for_command() {
  local command="$1"
  local attempts="${2:-30}"

  for ((i=1; i<=attempts; i++)); do
    if eval "$command" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  return 1
}

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

require_free_port() {
  local port="$1"
  local service="$2"

  if port_in_use "$port"; then
    echo ""
    echo "✗ Port $port is already in use."
    echo ""
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
    echo ""
    echo "Stop the existing $service before starting Semranko again."
    exit 1
  fi
}

cleanup() {
  echo ""
  echo "Stopping Semranko local application..."

  SHUTTING_DOWN=1

  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi

  if [ -n "${FASTAPI_PID:-}" ]; then
    kill "$FASTAPI_PID" 2>/dev/null || true
  fi

  if [ -n "${WORKER_SUPERVISOR_PID:-}" ]; then
    kill "$WORKER_SUPERVISOR_PID" 2>/dev/null || true
  fi

  # Stop only RQ workers belonging to this project.
  pkill -f "$PROJECT_DIR/.venv/bin/rq worker.*rank-check" \
    2>/dev/null || true

  echo ""
  echo "✓ FastAPI stopped"
  echo "✓ RQ worker stopped"
  echo "✓ Next.js stopped"
  echo ""
  echo "Docker Redis and Tailscale Funnel are intentionally left running."
  echo ""

  exit 0
}

trap cleanup SIGINT SIGTERM

# ---------------------------------------------------------
# Environment file
# ---------------------------------------------------------

if [ ! -f "$LOCAL_ENV_FILE" ]; then
  fail "Missing $LOCAL_ENV_FILE"
fi

export SEMRANKO_ENV_FILE="$LOCAL_ENV_FILE"

echo "✓ Environment: $LOCAL_ENV_FILE"

# ---------------------------------------------------------
# Python virtual environment
# ---------------------------------------------------------

if [ ! -d "$PROJECT_DIR/.venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$PROJECT_DIR/.venv"
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  fail "Virtual environment is invalid"
fi

source "$PROJECT_DIR/.venv/bin/activate"

if [ ! -f "$PROJECT_DIR/.venv/.dependencies_installed" ]; then
  echo "Installing Python dependencies..."
  pip install --upgrade pip

  if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
  fi

  touch "$PROJECT_DIR/.venv/.dependencies_installed"
fi

# ---------------------------------------------------------
# Docker Desktop
# ---------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker CLI is not installed"
fi

if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop..."

  open -a Docker >/dev/null 2>&1 || true

  if ! wait_for_command "docker info" 45; then
    fail "Docker Desktop did not become available"
  fi
fi

echo "✓ Docker Desktop is running"

# ---------------------------------------------------------
# Redis - Docker managed
# ---------------------------------------------------------

if docker ps -a \
  --format '{{.Names}}' \
  | grep -qx "$REDIS_CONTAINER"; then

  if ! docker ps \
    --format '{{.Names}}' \
    | grep -qx "$REDIS_CONTAINER"; then

    echo "Starting Docker Redis..."
    docker start "$REDIS_CONTAINER" >/dev/null
  fi

else
  echo "Creating Docker Redis..."

  docker run -d \
    --name "$REDIS_CONTAINER" \
    --restart unless-stopped \
    -p 6379:6379 \
    redis:7-alpine >/dev/null
fi

if ! wait_for_command \
  "docker exec $REDIS_CONTAINER redis-cli ping | grep -q PONG" \
  15; then
  fail "Redis did not become ready"
fi

echo "✓ Redis is running in Docker"

# ---------------------------------------------------------
# Tailscale Funnel - PUBLIC DataForSEO callback
# ---------------------------------------------------------

if ! command -v tailscale >/dev/null 2>&1; then
  fail "Tailscale CLI is not installed"
fi

if ! tailscale status >/dev/null 2>&1; then
  echo "Starting Tailscale..."

  open -a Tailscale >/dev/null 2>&1 || true

  if ! wait_for_command "tailscale status" 30; then
    fail "Tailscale did not connect"
  fi
fi

echo "✓ Tailscale is connected"

TAILSCALE_HOSTNAME="$(
  tailscale status --json 2>/dev/null \
    | "$PROJECT_DIR/.venv/bin/python" -c \
      'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))'
)"

if [ -z "$TAILSCALE_HOSTNAME" ]; then
  fail "Could not determine Tailscale hostname"
fi

TAILSCALE_URL="https://$TAILSCALE_HOSTNAME"

# DataForSEO is external to the tailnet.
# Tailscale Serve is tailnet-only, so callbacks must use Funnel.
FUNNEL_STATUS="$(tailscale funnel status 2>&1 || true)"

if ! printf '%s\n' "$FUNNEL_STATUS" \
  | grep -q "127.0.0.1:4000"; then

  echo "Configuring public Tailscale Funnel..."

  # Remove an old tailnet-only Serve mapping if one exists.
  tailscale serve --https=443 off >/dev/null 2>&1 || true

  if ! tailscale funnel \
    --bg \
    http://127.0.0.1:4000 >/dev/null 2>&1; then

    fail "Could not enable Tailscale Funnel"
  fi

  sleep 2
fi

FUNNEL_STATUS="$(tailscale funnel status 2>&1 || true)"

if ! printf '%s\n' "$FUNNEL_STATUS" \
  | grep -q "Funnel on"; then

  echo ""
  echo "$FUNNEL_STATUS"
  echo ""

  fail "Tailscale Funnel is not publicly enabled"
fi

if ! printf '%s\n' "$FUNNEL_STATUS" \
  | grep -q "127.0.0.1:4000"; then

  echo ""
  echo "$FUNNEL_STATUS"
  echo ""

  fail "Tailscale Funnel is not proxying to FastAPI port 4000"
fi

echo "✓ Public Tailscale Funnel: $TAILSCALE_URL"

# ---------------------------------------------------------
# Application environment
# ---------------------------------------------------------

export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/fastapi_app:${PYTHONPATH:-}"

echo ""
echo "Checking application configuration..."

cd "$PROJECT_DIR"

"$PROJECT_DIR/.venv/bin/python" - <<'PY'
import sys

sys.path.insert(0, "fastapi_app")

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal

s = get_settings()

print("  ENV:", s.ENV)
print("  Redis:", s.REDIS_URL)
print("  Pingback:", s.PINGBACK_URL)
print("  CSRF domain:", repr(s.CSRF_COOKIE_DOMAIN))

if not s.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")

if not s.PINGBACK_URL:
    raise RuntimeError("PINGBACK_URL is not configured")

db = SessionLocal()

try:
    value = db.execute(text("SELECT 1")).scalar()

    if value != 1:
        raise RuntimeError("Unexpected database response")
finally:
    db.close()

print("  Neon DB: connected")
PY

if [ $? -ne 0 ]; then
  fail "Environment or Neon database verification failed"
fi

CONFIGURED_PINGBACK="$(
  "$PROJECT_DIR/.venv/bin/python" - <<'PY'
import sys

sys.path.insert(0, "fastapi_app")

from app.core.config import get_settings

print((get_settings().PINGBACK_URL or "").rstrip("/"))
PY
)"

if [ "$CONFIGURED_PINGBACK" != "${TAILSCALE_URL%/}" ]; then
  echo ""
  echo "Configured PINGBACK_URL:"
  echo "  $CONFIGURED_PINGBACK"
  echo ""
  echo "Current public Funnel:"
  echo "  $TAILSCALE_URL"
  echo ""

  fail "PINGBACK_URL does not match the current Tailscale Funnel URL"
fi

echo "✓ DataForSEO pingback matches public Funnel"
echo "✓ Application configuration is valid"

# ---------------------------------------------------------
# FastAPI
# ---------------------------------------------------------

echo ""

require_free_port 4000 "FastAPI process"

echo "Starting FastAPI..."

: > "$FASTAPI_LOG"

cd "$PROJECT_DIR"

"$PROJECT_DIR/.venv/bin/python" \
  -m uvicorn \
  --app-dir fastapi_app \
  app.main:app \
  --host 0.0.0.0 \
  --port 4000 \
  > "$FASTAPI_LOG" 2>&1 &

FASTAPI_PID=$!

sleep 1

if ! kill -0 "$FASTAPI_PID" 2>/dev/null; then
  echo ""
  tail -40 "$FASTAPI_LOG"
  fail "FastAPI process exited during startup"
fi

if ! wait_for_command \
  "curl -fsS http://127.0.0.1:4000/docs" \
  20; then

  echo ""
  tail -40 "$FASTAPI_LOG"
  fail "FastAPI did not start"
fi

echo "✓ FastAPI running (PID $FASTAPI_PID)"

# ---------------------------------------------------------
# RQ worker with automatic restart
# ---------------------------------------------------------

echo "Starting supervised RQ worker..."

: > "$RQ_LOG"

export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

start_worker_supervisor() {
  while true; do

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting RQ worker" \
      >> "$RQ_LOG"

    "$PROJECT_DIR/.venv/bin/rq" worker \
      --url "$REDIS_URL" \
      --worker-ttl 3600 \
      --maintenance-interval 60 \
      rank-check \
      >> "$RQ_LOG" 2>&1

    WORKER_EXIT_CODE=$?

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] RQ exited: $WORKER_EXIT_CODE" \
      >> "$RQ_LOG"

    if [ "${SHUTTING_DOWN:-0}" = "1" ]; then
      break
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restarting RQ in 2 seconds" \
      >> "$RQ_LOG"

    sleep 2
  done
}

start_worker_supervisor &

WORKER_SUPERVISOR_PID=$!

sleep 2

if ! kill -0 "$WORKER_SUPERVISOR_PID" 2>/dev/null; then
  fail "RQ supervisor failed to start"
fi

echo "✓ RQ supervisor running (PID $WORKER_SUPERVISOR_PID)"

if ! wait_for_command \
  "grep -q 'Listening on rank-check' '$RQ_LOG'" \
  15; then

  echo ""
  tail -40 "$RQ_LOG"
  fail "RQ worker did not start listening on rank-check"
fi

echo "✓ RQ worker is listening on rank-check"

# ---------------------------------------------------------
# Next.js frontend
# ---------------------------------------------------------

if [ ! -d "$FRONTEND_DIR" ]; then
  fail "Frontend directory not found: $FRONTEND_DIR"
fi

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  fail "Frontend package.json not found"
fi

require_free_port 3000 "Next.js process"

echo "Starting Next.js frontend..."

: > "$FRONTEND_LOG"

cd "$FRONTEND_DIR"

if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

npm run dev > "$FRONTEND_LOG" 2>&1 &

FRONTEND_PID=$!

sleep 1

if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo ""
  tail -40 "$FRONTEND_LOG"
  fail "Next.js process exited during startup"
fi

if ! wait_for_command \
  "curl -fsS http://127.0.0.1:3000" \
  30; then

  echo ""
  tail -40 "$FRONTEND_LOG"
  fail "Next.js frontend did not start"
fi

echo "✓ Next.js running (PID $FRONTEND_PID)"

# ---------------------------------------------------------
# Verify public Funnel -> FastAPI
# ---------------------------------------------------------

if curl -fsS "$TAILSCALE_URL/docs" >/dev/null 2>&1; then
  echo "✓ Public Tailscale Funnel → FastAPI route works"
else
  echo ""
  tailscale funnel status || true
  echo ""
  fail "Public Tailscale Funnel cannot reach FastAPI"
fi

# ---------------------------------------------------------
# Final safety checks
# ---------------------------------------------------------

if ! docker exec "$REDIS_CONTAINER" redis-cli ping \
  | grep -q PONG; then
  fail "Redis health check failed after startup"
fi

if ! grep -q "Listening on rank-check" "$RQ_LOG"; then
  fail "RQ worker is not listening after startup"
fi

if ! curl -fsS http://127.0.0.1:4000/docs >/dev/null; then
  fail "FastAPI final health check failed"
fi

if ! curl -fsS http://127.0.0.1:3000 >/dev/null; then
  fail "Frontend final health check failed"
fi

if ! curl -fsS "$TAILSCALE_URL/docs" >/dev/null; then
  fail "Public DataForSEO callback route final health check failed"
fi

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

echo ""
echo "=========================================="
echo "        ✓ Semranko is running"
echo "=========================================="
echo ""

echo "Frontend:"
echo "  http://localhost:3000"
echo ""

echo "Backend:"
echo "  http://localhost:4000"
echo "  http://localhost:4000/docs"
echo ""

echo "DataForSEO public callback base:"
echo "  $TAILSCALE_URL"
echo ""

echo "DataForSEO webhook:"
echo "  $TAILSCALE_URL/api/webhooks/dataforseo"
echo ""

echo "Tailscale:"
echo "  Public Funnel enabled"
echo ""

echo "Redis:"
echo "  Docker container: $REDIS_CONTAINER"
echo "  $REDIS_URL"
echo ""

echo "Logs:"
echo "  FastAPI  : $FASTAPI_LOG"
echo "  RQ Worker: $RQ_LOG"
echo "  Frontend : $FRONTEND_LOG"
echo ""

echo "Useful commands:"
echo "  tail -f $FASTAPI_LOG"
echo "  tail -f $RQ_LOG"
echo "  tail -f $FRONTEND_LOG"
echo "  tailscale funnel status"
echo ""

echo "Press Ctrl+C to stop FastAPI, RQ and Next.js."
echo "Docker Redis and Tailscale Funnel will remain running."
echo ""

wait