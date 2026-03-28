from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.execution import ExecutionCaseResult, SupportedLanguage


class SubmissionHistoryItem(BaseModel):
    id: int
    mode: str
    language: SupportedLanguage
    code_snapshot: str
    results: list[ExecutionCaseResult]
    passed_count: int
    total_count: int
    all_passed: bool
    error: str | None = None
    created_at: datetime
