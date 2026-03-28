from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


SupportedLanguage = Literal["python", "javascript", "java", "cpp"]


class CodeExecutionRequest(BaseModel):
    code: str
    language: SupportedLanguage = "python"


class ExecutionCaseResult(BaseModel):
    input: Any
    expected_output: Any
    actual_output: Any | None = None
    passed: bool
    stdout: str = ""
    error: str | None = None
    explanation: str = ""


class ExecutionResponse(BaseModel):
    status: Literal["success", "error", "timeout"]
    mode: Literal["run", "submit"]
    language: SupportedLanguage
    passed_count: int
    total_count: int
    all_passed: bool
    results: list[ExecutionCaseResult]
    error: str | None = None
