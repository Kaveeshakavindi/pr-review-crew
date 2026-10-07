# PR Review Crew

PR Review Crew is a GitHub App that automatically reviews pull requests using an asynchronous processing pipeline and an AI code reviewer.

When a pull request is opened or updated, GitHub sends a signed webhook to the application. The FastAPI service verifies the request, filters relevant events, prevents duplicate processing, and queues a review job in Redis. An Arq worker then retrieves the pull request diff, authenticates with GitHub, sends the changed code to an LLM, validates the response against a structured Pydantic schema, and publishes the review through a GitHub Check.

## Demo

A pull request containing intentionally vulnerable code was reviewed automatically.

The reviewer identified:

- Hardcoded password
- Exposure of credentials through a `print` statement

The findings included severity, description, affected file/line, and remediation suggestions.

![AI Review Result](assets/ss12.png)

## What it does

```text
GitHub Pull Request
        ↓
Signed Webhook
        ↓
FastAPI
        ↓
Signature Verification
        ↓
Event Filtering
        ↓
Delivery / Job Deduplication
        ↓
Redis
        ↓
Arq Worker
        ↓
GitHub Installation Token
        ↓
Fetch Pull Request Diff
        ↓
LLM Code Review
        ↓
Structured Pydantic Output
        ↓
GitHub Check
```

The application processes reviews asynchronously so the GitHub webhook can return immediately rather than waiting for the AI review to finish.

## System Architecture

```text
                         GitHub
                           │
                           ▼
                    Pull Request
                           │
                           ▼
                     Webhook Event
                           │
                           ▼
                      FastAPI API
                           │
              ┌────────────┴────────────┐
              │                         │
      HMAC Verification          Event Filtering
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                    Redis / Arq Queue
                           │
                           ▼
                       Arq Worker
                           │
              ┌────────────┴────────────┐
              │                         │
       GitHub Authentication       PR Diff
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                      AI Reviewer
                           │
                           ▼
                  Structured JSON
                           │
                           ▼
                  Pydantic Validation
                           │
                           ▼
                    GitHub Check
```

## AI Review

The AI reviewer receives the pull request diff and is instructed to focus on issues that can meaningfully affect:

- correctness
- security
- reliability
- performance
- maintainability

The reviewer is deliberately conservative. It is instructed not to report stylistic preferences, formatting issues, speculative problems, or issues outside the changed code.

The expected output is:

```json
{
  "summary": "Short summary of the review",
  "findings": [
    {
      "file": "test.py",
      "line": 10,
      "severity": "critical",
      "title": "Hardcoded sensitive information",
      "description": "Explain the issue.",
      "suggestion": "Explain how it could be fixed."
    }
  ]
}
```

The response is validated using Pydantic before it is used by the application.

### Review Model

```text
ReviewResult
├── summary
└── findings[]
    ├── file
    ├── line
    ├── severity
    ├── title
    ├── description
    └── suggestion
```

## Security

### Webhook Verification

Webhook requests are verified using HMAC-SHA256 before the JSON payload is processed.

```text
GitHub Request
      ↓
Raw Request Body
      ↓
HMAC-SHA256
      ↓
Compare with GitHub Signature
      ↓
Valid?
   ┌──┴──┐
  YES    NO
   ↓      ↓
Process  401
```

This prevents arbitrary requests from being accepted by the webhook endpoint.

### GitHub Authentication

The application uses GitHub App authentication:

```text
GitHub App Private Key
        ↓
App JWT
        ↓
Installation ID
        ↓
Installation Access Token
        ↓
GitHub REST API
```

The installation token is then used to access the repository and create GitHub Checks and comments.

### Deduplication

Two identifiers are used to prevent unnecessary duplicate processing:

- GitHub delivery ID — stored in Redis with a 24-hour TTL
- Review job ID — generated from repository, pull request number, and head commit SHA

Example:

```text
review:owner/repository#1:<commit-sha>
```

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application and worker |
| FastAPI | Webhook API |
| Redis | Queue and deduplication |
| Arq | Asynchronous job processing |
| httpx | GitHub API client |
| GitHub Apps | Webhook and authentication |
| GitHub REST API | PRs, diffs, comments and checks |
| HMAC-SHA256 | Webhook verification |
| PyJWT | GitHub App JWT |
| Gemini API | AI code review |
| Pydantic | Structured output validation |
| Docker | Containerisation |
| Uvicorn | ASGI server |
| Pytest | Testing |
| ngrok | Local webhook development |
| Render | Deployment |
| Upstash Redis | Hosted Redis |

## Testing

The project includes tests for webhook security and the asynchronous processing flow.

Run:

```bash
python -m pytest
```

### Webhook Flow Test

The local webhook can be tested by generating a signed request:

```text
Test Payload
     ↓
HMAC-SHA256 Signature
     ↓
POST /webhooks
     ↓
FastAPI
     ↓
Redis
     ↓
Arq Worker
```

The test verifies that the application:

1. receives the webhook
2. validates the HMAC signature
3. identifies the pull request event
4. performs delivery deduplication
5. extracts repository and PR information
6. creates a deterministic review job ID
7. queues the job in Redis
8. returns `202 Accepted`

The same delivery can then be submitted again to verify deduplication.

## Local Setup

### 1. Install dependencies

Create and activate a Python environment, then install:

```bash
pip install -r requirements.txt
```

### 2. Start Redis

Redis can be run locally with Homebrew:

```bash
brew install redis
brew services start redis
redis-cli ping
```

Expected:

```text
PONG
```

Or use Docker Compose:

```bash
docker compose up -d
docker compose ps
```

Stop it with:

```bash
docker compose down
```

### 3. Configure environment variables

Create a `.env` file containing:

```text
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=
REDIS_URL=
GEMINI_API_KEY=
```

Do not commit `.env` or GitHub private keys to the repository.

### 4. Start FastAPI

```bash
uvicorn app.main:app --reload
```

Health check:

```text
http://localhost:8000/health
```

### 5. Start the Arq worker

```bash
python -m arq app.worker.WorkerSettings
```

### 6. Expose the webhook

For local GitHub webhook testing:

```bash
ngrok http 8000
```

Configure the resulting URL in the GitHub App:

```text
https://<your-ngrok-domain>/webhooks
```

## GitHub App Configuration

The GitHub App requires:

### Repository permissions

- Checks — Read and write
- Pull requests — Read and write
- Contents — Read
- Metadata — Read

### Webhook events

- Pull request

The application currently processes:

- `opened`
- `synchronize`
- `reopened`

Other events are ignored.

## Deployment

The current deployment uses a lightweight architecture suitable for demonstrating the complete pipeline without requiring a separate paid worker service.

```text
                    Render
               ┌───────────────┐
               │ Docker Web App │
               │               │
GitHub ───────►│ FastAPI       │
               │      +        │
               │ Arq Worker    │
               └───────┬───────┘
                       │
                       ▼
                 Upstash Redis
                       │
                       ▼
                  Gemini API
```

The application is containerised using Docker.

The same container starts both the FastAPI service and the Arq worker.

## Project Evolution

### Phase 01 — Async Review Infrastructure
**2026-10-05**

The initial implementation established the asynchronous GitHub review infrastructure.

Implemented:

- GitHub webhook integration
- HMAC signature verification
- pull request event filtering
- delivery deduplication
- deterministic job IDs
- Redis queue
- Arq worker
- GitHub App authentication
- GitHub Check creation
- review-started comments
- Docker support
- automated tests

The initial worker simulated the review process.

### Phase 02 — AI Reviewer
**2026-10-08**

The simulated review process was replaced with an AI-powered reviewer.

Implemented:

- pull request diff retrieval
- LLM-based code review
- structured JSON output
- Pydantic validation
- severity classification
- security/correctness/reliability-focused review
- GitHub Check output

### Phase 03 — Deployment
**2026-10-08**

The complete application was deployed using:

- Docker
- Render
- Upstash Redis
- Gemini API

The deployed application can receive GitHub webhooks and process pull requests asynchronously.

## Current Limitations

This project is currently an early-stage automated review system.

Current limitations include:

- Reviews are based on the pull request diff rather than the complete repository context.
- Finding locations depend on the LLM's ability to identify changed lines.
- The reviewer does not yet execute or test the submitted code.
- There is currently no persistent review history or analytics.
- The deployment combines the web service and worker in one container for simplicity.

## Next Steps

Potential improvements include:

- more accurate changed-line annotations
- GitHub inline review comments
- repository-aware analysis
- static analysis integration
- automated test execution
- review evaluation against a benchmark of vulnerable pull requests
- persistent review history
- improved handling of large pull requests
- multi-agent or specialised review stages
```
