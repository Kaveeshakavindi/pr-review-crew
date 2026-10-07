#!/bin/sh
set -e

arq app.worker.WorkerSettings &

exec uvicorn app.main:app --host 0.0.0.0 --port 8000