from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.execution import SupportedLanguage


Difficulty = Literal["easy", "medium", "hard"]
ProblemStatus = Literal["not_started", "attempted", "solved"]
RuntimeShape = Literal["plain", "linked_list", "random_pointer_linked_list"]


class TestCaseCreate(BaseModel):
    input: Any
    expected_output: Any
    explanation: str = ""


class TestCaseDraft(BaseModel):
    input_json: str
    expected_output_json: str
    explanation: str = ""


class ProblemBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    topic: str = Field(min_length=1, max_length=100)
    difficulty: Difficulty
    description: str = Field(min_length=1)
    runtime_shape: RuntimeShape = "plain"
    starter_code: str = Field(min_length=1)
    function_name: str = Field(min_length=1, max_length=120)
    visible_test_cases: list[TestCaseCreate]
    hidden_test_cases: list[TestCaseCreate] = []
    notes: str = ""
    similar_questions: str = ""

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("topic", "title", "function_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ProblemCreate(ProblemBase):
    pass


class ProblemGenerationRequest(BaseModel):
    problem_statement: str = Field(min_length=20)


class ProblemGenerationResponse(BaseModel):
    title: str
    slug: str
    topic: str
    difficulty: Difficulty
    description: str
    runtime_shape: RuntimeShape
    starter_code: str
    starter_codes: dict[SupportedLanguage, str]
    function_name: str
    visible_test_cases: list[TestCaseCreate]
    hidden_test_cases: list[TestCaseCreate]
    generation_warnings: list[str] = []


class ProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    topic: str
    difficulty: Difficulty
    runtime_shape: RuntimeShape
    status: ProblemStatus
    updated_at: datetime


class ProblemDetail(ProblemSummary):
    description: str
    starter_code: str
    starter_codes: dict[SupportedLanguage, str]
    function_name: str
    visible_test_cases: list[TestCaseCreate]
    hidden_test_cases: list[TestCaseCreate]
    notes: str
    similar_questions: str
    created_at: datetime


class ProblemStatusUpdate(BaseModel):
    status: ProblemStatus


class ProblemWorkspaceUpdate(BaseModel):
    notes: str = ""
    similar_questions: str = ""


class ProblemListResponse(BaseModel):
    items: list[ProblemSummary]
    total: int
