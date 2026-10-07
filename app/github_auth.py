# PEM file
#    ↓
# load_private_key()
#    ↓
# private key text
#    ↓
# jwt.encode()
#    ↓
# App JWT
#  ↓
# POST /app/installations/{installation_id}/access_tokens (calls github)
#       ↓
# Installation token
#       ↓
# cache for ~55 minutes

import time

import jwt

from app.config import settings
import httpx


def load_private_key() -> str:
    return settings.GITHUB_PRIVATE_KEY


def make_app_jwt() -> str:
    now = int(time.time())

    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": str(settings.GITHUB_APP_ID),
    }

    private_key = load_private_key()

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
    )

async def get_installation_token(
    client: httpx.AsyncClient,
    installation_id: int,
) -> str:

    app_jwt = make_app_jwt()

    url = (
        f"https://api.github.com/app/installations/"
        f"{installation_id}/access_tokens"
    )

    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = await client.post(
        url,
        headers=headers,
    )

    response.raise_for_status()

    data = response.json()

    return data["token"]