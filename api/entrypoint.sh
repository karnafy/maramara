#!/bin/sh
# Combined entrypoint: run gunicorn + RQ worker in one container.
# If either process dies, exit so Railway restarts the container.
set -e

: "${PORT:=5000}"
: "${GUNICORN_WORKERS:=2}"
: "${GUNICORN_THREADS:=4}"

echo "[entrypoint] starting gunicorn on 0.0.0.0:${PORT}"
gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${GUNICORN_WORKERS}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout 120 \
  --access-logfile - \
  app:app &
GUNICORN_PID=$!

echo "[entrypoint] starting RQ worker"
python worker_main.py &
WORKER_PID=$!

# Forward signals so container shuts down cleanly
trap 'kill -TERM $GUNICORN_PID $WORKER_PID 2>/dev/null; wait' TERM INT

# Exit as soon as either process dies -> Railway restarts
wait -n $GUNICORN_PID $WORKER_PID
echo "[entrypoint] a process exited; shutting down container"
kill -TERM $GUNICORN_PID $WORKER_PID 2>/dev/null || true
exit 1
