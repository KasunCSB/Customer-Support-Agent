
#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=/var/log
mkdir -p "$LOG_DIR"

echo "Starting services: backend (uvicorn), frontend (next) and nginx"

# Start backend
echo "Starting backend on 127.0.0.1:8000"
nohup python3 -m uvicorn api_server:app --host 127.0.0.1 --port 8000 &> $LOG_DIR/backend.log &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend (Next) on 127.0.0.1:3000"
cd /app/ui || exit 1
# Use npm run start which should call `next start` in production
nohup npm run start -- -p 3000 --hostname 127.0.0.1 &> $LOG_DIR/frontend.log &
FRONTEND_PID=$!

cd /app || exit 1

# Wait for backend to become healthy
echo "Waiting for backend (127.0.0.1:8000) to become ready..."
for i in {1..30}; do
	if curl -sS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
		echo "Backend is up"
		break
	fi
	if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
		echo "Backend process exited unexpectedly. See $LOG_DIR/backend.log"
		tail -n 200 $LOG_DIR/backend.log || true
		exit 1
	fi
	sleep 1
done

# Wait for frontend to become ready
echo "Waiting for frontend (127.0.0.1:3000) to become ready..."
for i in {1..30}; do
	if curl -sS http://127.0.0.1:3000/ >/dev/null 2>&1; then
		echo "Frontend is up"
		break
	fi
	if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
		echo "Frontend process exited unexpectedly. See $LOG_DIR/frontend.log"
		tail -n 200 $LOG_DIR/frontend.log || true
		exit 1
	fi
	sleep 1
done

echo "Launching nginx in foreground"
exec nginx -g 'daemon off;'
