#!/bin/sh
set -e

echo "Starting Arq worker..."
python -m arq app.worker.WorkerSettings &

echo "Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000