from fastapi import FastAPI, Request, HTTPException
import json

from app.config import settings
from app.security import verify_signature

from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings

from app.worker import start_review

# ----------------------------------------------
# when uvicorn starts;
# Uvicorn
#    ↓
# FastAPI starts
#    ↓
# lifespan()
#    ↓
# create Redis pool
#    ↓
# app.state.redis
#    ↓
# yield
#    ↓
# Application runs

# when uvicorn stops
# Application stops
#        ↓
# lifespan continues after yield
#        ↓
# Redis pool closes

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_pool(
        RedisSettings.from_dsn(settings.REDIS_URL)
    )

    yield

    await app.state.redis.close()

app = FastAPI(lifespan=lifespan)

# -------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------

# GitHub
#    │
#    │ POST /webhooks
#    ▼
# FastAPI
#    │
#    ├── verify signature
#    │
#    ├── check event/action
#    │
#    ├── deduplicate delivery
#    │
#    ├── extract PR information
#    │
#    └── enqueue_job()
#           │
#           ▼
#         Redis
#           │
#           ▼
#       Arq Worker
#           │
#           ▼
#     start_review()

@app.post("/webhooks", status_code=202)
async def webhook(request: Request):

    # 1. Get the exact bytes GitHub sent
    raw_body = await request.body()

    # 2. Get GitHub's signature
    signature = request.headers.get("X-Hub-Signature-256")

    # 3. Verify BEFORE parsing JSON
    if not verify_signature(
        raw_body,
        signature,
        settings.GITHUB_WEBHOOK_SECRET
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid signature"
        )

    # 4. Read GitHub webhook headers
    event = request.headers.get("X-GitHub-Event")
    delivery = request.headers.get("X-GitHub-Delivery")

    # 5. Parse JSON after verification
    payload = json.loads(raw_body)
    action = payload.get("action")

     # 6. Ignore irrelevant events
    if event != "pull_request" or action not in {
        "opened",
        "synchronize",
        "reopened",
    }:
        return {"ignored": True}
    
     # 7. Deduplicate delivery
    seen = await request.app.state.redis.set(
        f"delivery:{delivery}",
        1,
        nx=True,
        ex=86400,
    )

    if seen is None:
        print("duplicate, skipped")
        return {"duplicate": True}

    # 8. Extract information needed by the worker
    installation_id = payload["installation"]["id"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr = payload["pull_request"]["number"]
    head_sha = payload["pull_request"]["head"]["sha"]
    
    job_id = f"review:{owner}/{repo}#{pr}:{head_sha}" #create unique job ID

    # 10. Add job to the queue
    print(f"QUEUEING JOB: {job_id}", flush=True)

    await request.app.state.redis.enqueue_job(
        "start_review",
        owner,
        repo,
        pr,
        head_sha,
        installation_id,
        _job_id=job_id,
    )

    print(f"JOB QUEUED: {job_id}", flush=True)

    # 11. Return immediately
    return {
        "status": "queued",
        "job_id": job_id,
    }

# -----------------------------------------------

# 2 layers of deduplication
#               GitHub
#                   │
#           ┌───────┴───────┐
#           │               │
#       Delivery A       Delivery B
#           │               │
#           │               │
#           ▼               ▼
#      Delivery ID      Delivery ID
#       duplicate?       different
#           │               │
#           ▼               ▼
#        Redis           Job ID
#      delivery:A      same commit?
#           │               │
#           ▼               ▼
#        skip             arq
#                          │
#                          ▼
#                    duplicate job?
#                          │
#                     skip if same

