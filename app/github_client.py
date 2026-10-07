# 2026-10-08
# GitHub API Operations

import httpx


GITHUB_API = "https://api.github.com"


async def get_pull_request_diff(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    pr_number: int,
    token: str,
) -> str:

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = await client.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
        headers=headers,
    )

    response.raise_for_status()

    return response.text