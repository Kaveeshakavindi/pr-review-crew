# pr-review-crew

---
you need to install redis on your pc

```bash
brew install redis
```

then run it

```bash
brew services start redis
```

check if it is running

```bash
redis-cli ping
```

OR

Start redis via docker compose
- go to project directory
- and run;

```bash
docker compose up -d
```

check if redis is running

```bash
docker compose ps
```

stop redis when finished

```bash
docker compose down
```

---

start python web application

```bash
uvicorn app.main:app --reload
```

---

create empty __init__.py file. it asks app to treat the folder as a python package. 

example:

```bash
touch app/__init__.py
```

---

Run ngrok agent endpoint from command line
```bash
ngrok http 8000 --url https://<abc123>.ngrok-free.dev
```

![Alt Text](assets/ss1.png)

---

### GitHub App settings

In your GitHub App settings:

- Webhook URL: https://<your-ngrok-domain>/webhooks
- Webhook secret: a long random string, which also goes in .env
- Permissions: Checks (read and write), Pull requests (read and write), Contents (read), Metadata (read)
- Events: Pull request
- Install the app on your test repo.

---

# Security

Added security to make sure that the webhook request really came from GitHub and wasn't modified by someone else because anyone who knows the ngrok public URL could potentially send a fake request.

Concept:
When GitHub sends a webhook, it takes the exact raw request body and calculates an HMAC-SHA256 signature using that secret.

request
   ↓
await request.body()
   ↓
verify signature
   ↓
signature valid?
   ↓ YES
json.loads()
   ↓
process webhook

--- 

Run tests

```bash
python -m pytest
```
![Alt Text](assets/ss2.png)

---

Start the worker
```bash
python -m arq app.worker.WorkerSettings
```
---

# Test : Fast API enqueue job

1. Redis

![Alt Text](assets/ss3.png)

2. Fast API

![Alt Text](assets/ss4.png)

3. Arq Worker

![Alt Text](assets/ss5.png)

3. Health Check

![Alt Text](assets/ss6.png)

4. Test webhook payload

```bash
python - <<'PY'
import json
import hmac
import hashlib
import subprocess

secret = "YOUR_WEBHOOK_SECRET"

payload = {
    "action": "opened",
    "installation": {
        "id": 12345678
    },
    "repository": {
        "owner": {
            "login": "test-owner"
        },
        "name": "test-repo"
    },
    "pull_request": {
        "number": 1,
        "head": {
            "sha": "abc123"
        }
    }
}

body = json.dumps(payload).encode()

signature = "sha256=" + hmac.new(
    secret.encode(),
    body,
    hashlib.sha256
).hexdigest()

subprocess.run([
    "curl",
    "-X", "POST",
    "http://localhost:8000/webhooks",
    "-H", "Content-Type: application/json",
    "-H", "X-GitHub-Event: pull_request",
    "-H", "X-GitHub-Delivery: test-delivery-001",
    "-H", f"X-Hub-Signature-256: {signature}",
    "-d", body
])
PY
```
![Alt Text](assets/ss7.png)

5. Run above command again to test job-ID deduplication.

![Alt Text](assets/ss8.png)

6. Run above command again to test delievery-ID deduplication.

7. Test if Arq worker received the job and attempted in arq worker running terminal

![Alt Text](assets/ss9.png)

8. GitHub Test with real repository

- create new branch in hit hub app installed test repo.
- commit and push changes.
- open a new pull request.
- at success, it will show below message.

![Alt Text](assets/ss11.png)

### So the webhook successfully:

1. Received the request.
2. Verified the HMAC signature.
3. Recognized it as a pull_request + opened event.
4. Passed the delivery deduplication check.
5. Extracted the PR information.
6. Created job ID.
7. Put the job into Redis.
8. Returned 202 Accepted immediately.

---

System Architecture

```
                         GitHub
                           │
                           │ webhook
                           ▼
                    ┌──────────────┐
                    │   FastAPI    │
                    │ /webhooks    │
                    └──────┬───────┘
                           │
                     verify signature
                           │
                     check event/action
                           │
                        deduplicate
                           │
                           ▼
                    ┌──────────────┐
                    │    Redis     │
                    │  arq queue   │
                    └──────┬───────┘
                           │
                           │ job
                           ▼
                    ┌──────────────┐
                    │ arq Worker   │
                    │              │
                    │ start_review │
                    └──────┬───────┘
                           │
                  get installation token
                           │
                           ▼
                    ┌──────────────┐
                    │ GitHub API   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Check run     Comment      Complete
          in progress  "👋 Review    green check
                        started"

```

