# main.py
#    ↓
# puts start_review(...) into Redis
#    ↓
# worker.py
#    ↓
# arq picks it up

import asyncio

import httpx

from arq.connections import RedisSettings

from app.config import settings
from app.github_auth import get_installation_token


GITHUB_API = "https://api.github.com"


async def start_review(
    ctx,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    installation_id: int,
):
    client: httpx.AsyncClient = ctx["http"]

    token = await get_installation_token(
        client,
        installation_id,
    )

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
        await asyncio.sleep(2)

        # 4. Complete check run
        response = await client.patch(
            f"{GITHUB_API}/repos/{owner}/{repo}"
            f"/check-runs/{check_run_id}",
            headers=headers,
            json={
                "status": "completed",
                "conclusion": "success",
                "output": {
                    "title": "PR Review Crew",
                    "summary": "Automated review completed successfully.",
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
    ctx["http"] = httpx.AsyncClient()


async def shutdown(ctx):
    await ctx["http"].aclose()


class WorkerSettings:
    functions = [start_review]

    redis_settings = RedisSettings.from_dsn(
        settings.REDIS_URL
    )

    max_tries = 3

    job_timeout = 300

    on_startup = startup
    on_shutdown = shutdown