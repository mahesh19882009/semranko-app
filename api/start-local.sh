#!/usr/bin/env bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"

echo "RankCare API Starter"
echo "===================="
echo "Project Directory: $PROJECT_DIR"
echo ""

# Check virtual environment
if [ ! -d "$PROJECT_DIR/.venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$PROJECT_DIR/.venv"
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  echo "Virtual environment activate script not found: $PROJECT_DIR/.venv/bin/activate"
  exit 1
fi

# Activate virtual environment
source "$PROJECT_DIR/.venv/bin/activate"

# Install dependencies if needed
if [ ! -f "$PROJECT_DIR/.venv/.dependencies_installed" ]; then
  echo "Installing Python dependencies..."
  pip install --upgrade pip
  if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
  fi
  touch "$PROJECT_DIR/.venv/.dependencies_installed"
fi

# Check Redis
if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli not found. Please install Redis first."
  echo "On Ubuntu/Debian: sudo apt-get install redis-server"
  echo "On macOS: brew install redis"
  exit 1
fi

# Function to check if a port is in use
is_port_in_use() {
  nc -z localhost "$1" 2>/dev/null
  return $?
}

# Start Redis if not running
if redis-cli ping >/dev/null 2>&1; then
  echo "✓ Redis is already running"
else
  if command -v redis-server >/dev/null 2>&1; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
    if redis-cli ping >/dev/null 2>&1; then
      echo "✓ Redis started successfully"
    else
      echo "✗ Failed to start Redis"
      exit 1
    fi
  else
    echo "redis-server not found. Please install Redis first."
    exit 1
  fi
fi

echo ""
echo "Starting services (Press Ctrl+C to stop all)..."
echo ""

# Cleanup function
cleanup() {
  echo ""
  echo "Stopping all services..."

  SHUTTING_DOWN=1

  if [ -n "${FASTAPI_PID:-}" ]; then
    kill "$FASTAPI_PID" 2>/dev/null || true
  fi

  if [ -n "${WORKER_SUPERVISOR_PID:-}" ]; then
    kill "$WORKER_SUPERVISOR_PID" 2>/dev/null || true
  fi

  # Kill any RQ worker started by this local project.
  pkill -f "$PROJECT_DIR/.venv/bin/rq worker rank-check" 2>/dev/null || true

  # Redis is intentionally left running.
  echo "Services stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

# Start FastAPI in background
echo "Starting FastAPI server on http://localhost:4000..."
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/fastapi_app:$PYTHONPATH"
"$PROJECT_DIR/.venv/bin/python" -m uvicorn --app-dir fastapi_app app.main:app --reload --host 0.0.0.0 --port 4000 > /tmp/uvicorn.log 2>&1 &
FASTAPI_PID=$!
sleep 2

# Check if FastAPI started successfully
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
  echo "✗ Failed to start FastAPI server"
  exit 1
fi
echo "✓ FastAPI server started (PID: $FASTAPI_PID)"

# Start supervised RQ worker
echo "Starting supervised RQ worker..."

export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/fastapi_app:$PYTHONPATH"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

start_worker_supervisor() {
  while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting RQ worker..." >> /tmp/rq-worker.log

    "$PROJECT_DIR/.venv/bin/rq" worker \
      --url "redis://127.0.0.1:6379/0" \
      --worker-ttl 3600 \
      --maintenance-interval 60 \
      rank-check >> /tmp/rq-worker.log 2>&1
    WORKER_EXIT_CODE=$?

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] RQ worker exited with code $WORKER_EXIT_CODE" >> /tmp/rq-worker.log

    # Do not restart while the main script is shutting down.
    if [ "${SHUTTING_DOWN:-0}" = "1" ]; then
      break
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restarting RQ worker in 2 seconds..." >> /tmp/rq-worker.log
    sleep 2
  done
}

start_worker_supervisor &
WORKER_SUPERVISOR_PID=$!

sleep 2

if ! kill -0 "$WORKER_SUPERVISOR_PID" 2>/dev/null; then
  echo "✗ Failed to start RQ worker supervisor"
  exit 1
fi

echo "✓ RQ worker supervisor started (PID: $WORKER_SUPERVISOR_PID)"

echo ""
echo "=========================================="
echo "✓ All services are running!"
echo "=========================================="
echo "FastAPI: http://localhost:4000"
echo "API Docs: http://localhost:4000/docs"
echo "Server logs: /tmp/uvicorn.log"
echo "RQ worker: supervised with automatic restart"
echo "Worker logs: /tmp/rq-worker.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait