# python -m tests.test_reviewer

import json

import httpx

from app.review.models import ReviewResult
from app.review.prompts import (
    REVIEW_SYSTEM_PROMPT,
    build_review_prompt,
)
from app.config import settings
from google import genai
from google.genai import types


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral:7b"

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

GEMINI_MODEL = "gemini-2.5-flash"


# async def review_pull_request(
#     client: httpx.AsyncClient,
#     diff: str,
# ) -> ReviewResult:

#     response = await client.post(
#         OLLAMA_URL,
#         json={
#             "model": OLLAMA_MODEL,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": REVIEW_SYSTEM_PROMPT,
#                 },
#                 {
#                     "role": "user",
#                     "content": build_review_prompt(diff),
#                 },
#             ],
#             "stream": False,
#         },
#         timeout=300,
#     )

#     response.raise_for_status()

#     data = response.json()

#     content = data["message"]["content"]

#     result = json.loads(content)

#     return ReviewResult.model_validate(result)

async def review_pull_request(
    diff: str,
) -> ReviewResult:

    prompt = (
        f"{REVIEW_SYSTEM_PROMPT}\n\n"
        f"{build_review_prompt(diff)}"
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ReviewResult,
        ),
    )

    return ReviewResult.model_validate_json(response.text)