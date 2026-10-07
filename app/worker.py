# main.py
#    ↓
# puts start_review(...) into Redis
#    ↓
# worker.py
#    ↓
# arq (Asynchronous Redis Queue) picks it up

# arq: lightweight, high-performance job queue and Remote Procedure Call (RPC) library for Python

import httpx

from arq.connections import RedisSettings

from app.config import settings
from app.github_auth import get_installation_token

from app.github_client import get_pull_request_diff
from app.review.reviewer import review_pull_request

GITHUB_API = "https://api.github.com"


async def start_review(
    ctx,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    installation_id: int,
):
    print(
        f"WORKER RECEIVED JOB: "
        f"{owner}/{repo}#{pr_number} sha={head_sha}",
        flush=True,
    )

    client: httpx.AsyncClient = ctx["http"]

    token = await get_installation_token(
        client,
        installation_id,
    )
    print("Creating GitHub check run...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    check_run_id = None

    try:
        # 1. Create check run
        response = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/check-runs",
            headers=headers,
            json={
                "name": "PR Review Crew",
                "head_sha": head_sha,
                "status": "in_progress",
            },
        )

        response.raise_for_status()

        check_run_id = response.json()["id"]

        print(
            f"Started review: "
            f"{owner}/{repo}#{pr_number} "
            f"sha={head_sha}"
        )
        print("Check run created.")

        # 2. Post PR comment
        response = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}"
            f"/issues/{pr_number}/comments",
            headers=headers,
            json={
                "body": "👋 Review started"
            },
        )

        response.raise_for_status()

        # 3. Simulate review work
        # await asyncio.sleep(2)

        # ---------------------------------------
        # 3. integrate AI reviewer into worker
        # added on 2026-10-08 (phase 02)
        # 3. Get PR diff
        diff = await get_pull_request_diff(
            client,
            owner,
            repo,
            pr_number,
            token,
        )
        print("Getting PR diff...")
        print("Sending diff to Gemini...")
        # 4. Run AI review
        review = await review_pull_request(
            client,
            diff,
        )

        print(
            f"Review result for {owner}/{repo}#{pr_number}:"
        )

        print(
            review.model_dump_json(indent=2)
        )

        findings_text = "\n\n".join(
            f"**{finding.severity.upper()} — {finding.title}**\n"
            f"{finding.description}\n"
            f"**Suggestion:** {finding.suggestion or 'No suggestion provided.'}"
            for finding in review.findings
        )

        summary = (
            f"{review.summary}\n\n"
            f"Found {len(review.findings)} issue(s).\n\n"
            f"{findings_text}"
            if review.findings
            else f"{review.summary}\n\nNo significant issues found."
        )
        print("Gemini review completed.")
        # --------------------------------------

        # 5. Complete check run
        response = await client.patch(
            f"{GITHUB_API}/repos/{owner}/{repo}"
            f"/check-runs/{check_run_id}",
            headers=headers,
            json={
                "status": "completed",
                "conclusion": "success",
                "output": {
                    "title": "PR Review Crew",
                    "summary": summary,
                },
            },
        )

        response.raise_for_status()

        print(
            f"Review completed: "
            f"{owner}/{repo}#{pr_number}"
        )

    except Exception:
        # If the check was created but something failed afterwards,
        # mark the check as failed.
        if check_run_id is not None:
            try:
                await client.patch(
                    f"{GITHUB_API}/repos/{owner}/{repo}"
                    f"/check-runs/{check_run_id}",
                    headers=headers,
                    json={
                        "status": "completed",
                        "conclusion": "failure",
                        "output": {
                            "title": "PR Review Crew",
                            "summary": "Review failed.",
                        },
                    },
                )
            except Exception:
                pass

        raise


async def startup(ctx):
    print("ARQ WORKER STARTUP", flush=True)
    ctx["http"] = httpx.AsyncClient()


async def shutdown(ctx):
    await ctx["http"].aclose()

async def test_job(ctx):
    print("TEST JOB RECEIVED", flush=True)

class WorkerSettings:
    functions = [start_review, test_job]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_tries = 3
    job_timeout = 300
    on_startup = startup
    on_shutdown = shutdown