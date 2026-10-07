# python -m tests.test_reviewer

import json

import httpx

from app.review.models import ReviewResult
from app.review.prompts import (
    REVIEW_SYSTEM_PROMPT,
    build_review_prompt,
)


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral:7b"


async def review_pull_request(
    client: httpx.AsyncClient,
    diff: str,
) -> ReviewResult:

    response = await client.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": REVIEW_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": build_review_prompt(diff),
                },
            ],
            "stream": False,
        },
        timeout=300,
    )

    response.raise_for_status()

    data = response.json()

    content = data["message"]["content"]

    result = json.loads(content)

    return ReviewResult.model_validate(result)