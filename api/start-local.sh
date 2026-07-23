#!/usr/bin/env bash
set -e

PROJECT_DIR="/Users/maheshsharma/development/rankcare-api/api"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "Project directory not found: $PROJECT_DIR"
  exit 1
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  echo "Virtual environment activate script not found: $PROJECT_DIR/.venv/bin/activate"
  exit 1
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli not found. Install Redis first."
  exit 1
fi

open_tab() {
  local title="$1"
  local command_to_run="$2"
  osascript <<EOF
tell application "Terminal"
    activate
    do script "cd ${PROJECT_DIR}; source .venv/bin/activate; ${command_to_run}"
end tell
EOF
}

if redis-cli ping >/dev/null 2>&1; then
  echo "Redis is already running."
else
  if command -v redis-server >/dev/null 2>&1; then
    echo "Starting Redis in a new Terminal window..."
    open_tab "Redis" "redis-server"
    sleep 2
  else
    echo "redis-server not found. Install Redis first."
    exit 1
  fi
fi

echo "Starting FastAPI in a new Terminal window..."
open_tab "FastAPI" "python3 -m uvicorn --app-dir fastapi_app app.main:app --reload --port 4000"
sleep 2

echo "Starting RQ worker in a new Terminal window..."
open_tab "RQ Worker" "export PYTHONPATH=${PROJECT_DIR}/fastapi_app; OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES /Users/maheshsharma/development/rankcare-api/api/.venv/bin/rq worker rank-check"

echo "Done."
echo "If Terminal asks for permission, click Allow."
echo "Use Ctrl+C in each Terminal window to stop the processes."