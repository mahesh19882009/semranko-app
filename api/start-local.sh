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
  if [ ! -z "$FASTAPI_PID" ]; then
    kill $FASTAPI_PID 2>/dev/null || true
  fi
  if [ ! -z "$WORKER_PID" ]; then
    kill $WORKER_PID 2>/dev/null || true
  fi
  # Don't stop Redis as it might be used by other applications
  echo "Services stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

# Start FastAPI in background
echo "Starting FastAPI server on http://localhost:4000..."
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/fastapi_app:$PYTHONPATH"
"$PROJECT_DIR/.venv/bin/python" -m uvicorn --app-dir fastapi_app app.main:app --reload --host 0.0.0.0 --port 4000 &
FASTAPI_PID=$!
sleep 2

# Check if FastAPI started successfully
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
  echo "✗ Failed to start FastAPI server"
  exit 1
fi
echo "✓ FastAPI server started (PID: $FASTAPI_PID)"

# Start RQ worker in background
echo "Starting RQ worker..."
export PYTHONPATH="$PROJECT_DIR:$PROJECT_DIR/fastapi_app:$PYTHONPATH"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
"$PROJECT_DIR/.venv/bin/rq" worker rank-check &
WORKER_PID=$!
sleep 1

# Check if worker started successfully
if ! kill -0 $WORKER_PID 2>/dev/null; then
  echo "✗ Failed to start RQ worker"
  exit 1
fi
echo "✓ RQ worker started (PID: $WORKER_PID)"

echo ""
echo "=========================================="
echo "✓ All services are running!"
echo "=========================================="
echo "FastAPI: http://localhost:4000"
echo "API Docs: http://localhost:4000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait