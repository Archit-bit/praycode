#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_PORT=8000
FRONTEND_PORT=5173

mkdir -p "$RUN_DIR" "$LOG_DIR"

is_pid_running() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

launch_detached() {
  local log_file="$1"
  shift

  nohup setsid "$@" >"$log_file" 2>&1 < /dev/null &
  LAUNCHED_PID=$!
}

is_port_in_use() {
  local port="$1"
  ss -ltn "( sport = :$port )" 2>/dev/null | tail -n +2 | grep -q .
}

start_backend() {
  if [ -f "$BACKEND_PID_FILE" ] && is_pid_running "$(cat "$BACKEND_PID_FILE")"; then
    echo "Backend already running on pid $(cat "$BACKEND_PID_FILE")."
    return
  fi

  if is_port_in_use "$BACKEND_PORT"; then
    echo "Backend port $BACKEND_PORT is already in use. Stop that process first."
    return
  fi

  cd "$ROOT_DIR/backend"
  launch_detached "$BACKEND_LOG" ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
  local backend_pid="$LAUNCHED_PID"
  cd "$ROOT_DIR"

  echo "$backend_pid" >"$BACKEND_PID_FILE"
  echo "Backend started on http://127.0.0.1:$BACKEND_PORT"
}

start_frontend() {
  if [ -f "$FRONTEND_PID_FILE" ] && is_pid_running "$(cat "$FRONTEND_PID_FILE")"; then
    echo "Frontend already running on pid $(cat "$FRONTEND_PID_FILE")."
    return
  fi

  if is_port_in_use "$FRONTEND_PORT"; then
    echo "Frontend port $FRONTEND_PORT is already in use. Stop that process first."
    return
  fi

  cd "$ROOT_DIR/frontend"
  launch_detached "$FRONTEND_LOG" npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
  local frontend_pid="$LAUNCHED_PID"
  cd "$ROOT_DIR"

  echo "$frontend_pid" >"$FRONTEND_PID_FILE"
  echo "Frontend started on http://127.0.0.1:$FRONTEND_PORT"
}

start_backend
start_frontend

echo
echo "PrayCode is starting."
echo "Frontend: http://127.0.0.1:$FRONTEND_PORT"
echo "Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "Logs:"
echo "  $FRONTEND_LOG"
echo "  $BACKEND_LOG"
