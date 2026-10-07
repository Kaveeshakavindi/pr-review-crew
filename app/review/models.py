from typing import Literal

from pydantic import BaseModel


class Finding(BaseModel):
    file: str
    line: int | None
    severity: Literal["low", "medium", "high", "critical"]
    title: str
    description: str
    suggestion: str | None


class ReviewResult(BaseModel):
    summary: str
    findings: list[Finding]