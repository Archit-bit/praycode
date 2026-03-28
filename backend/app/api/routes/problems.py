from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.problem import Problem
from app.models.submission import Submission
from app.schemas.execution import CodeExecutionRequest, ExecutionResponse
from app.schemas.problem import (
    ProblemCreate,
    ProblemDetail,
    ProblemGenerationRequest,
    ProblemGenerationResponse,
    ProblemListResponse,
    ProblemStatusUpdate,
    ProblemSummary,
    ProblemWorkspaceUpdate,
    TestCaseCreate,
)
from app.schemas.submission import SubmissionHistoryItem
from app.services.execution import execute_code
from app.services.language_support import build_starter_codes, detect_unsupported_problem_shape, infer_runtime_shape
from app.services.problem_generation import generate_problem_draft


router = APIRouter(prefix="/problems", tags=["problems"])


def _resolved_runtime_shape(problem: Problem) -> str:
    if getattr(problem, "runtime_shape", None) and problem.runtime_shape != "plain":
        return problem.runtime_shape
    return infer_runtime_shape(problem.topic, problem.description, problem.starter_code)


def _problem_to_detail(problem: Problem) -> ProblemDetail:
    visible_test_cases = [TestCaseCreate(**item) for item in json.loads(problem.visible_test_cases)]
    runtime_shape = _resolved_runtime_shape(problem)
    starter_codes = build_starter_codes(
        problem.topic,
        problem.function_name,
        problem.starter_code,
        problem.description,
        visible_test_cases,
        runtime_shape,
    )
    return ProblemDetail(
        id=problem.id,
        title=problem.title,
        slug=problem.slug,
        topic=problem.topic,
        difficulty=problem.difficulty,
        runtime_shape=runtime_shape,
        description=problem.description,
        starter_code=starter_codes["python"],
        starter_codes=starter_codes,
        function_name=problem.function_name,
        visible_test_cases=visible_test_cases,
        hidden_test_cases=[TestCaseCreate(**item) for item in json.loads(problem.hidden_test_cases or "[]")],
        status=problem.status,
        notes=problem.notes,
        similar_questions=problem.similar_questions,
        created_at=problem.created_at,
        updated_at=problem.updated_at,
    )


def _serialize_submission(submission: Submission) -> SubmissionHistoryItem:
    return SubmissionHistoryItem(
        id=submission.id,
        mode=submission.mode,
        language=submission.language,
        code_snapshot=submission.code_snapshot,
        results=[item for item in json.loads(submission.results_json)],
        passed_count=submission.passed_count,
        total_count=submission.total_count,
        all_passed=submission.all_passed,
        error=submission.error,
        created_at=submission.created_at,
    )


@router.get("", response_model=ProblemListResponse)
def list_problems(
    topic: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ProblemListResponse:
    query = select(Problem).order_by(Problem.updated_at.desc(), Problem.title.asc())

    if topic:
        query = query.where(Problem.topic == topic)
    if difficulty:
        query = query.where(Problem.difficulty == difficulty)
    if status_filter:
        query = query.where(Problem.status == status_filter)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(or_(Problem.title.ilike(search_term), Problem.slug.ilike(search_term)))

    problems = db.scalars(query).all()
    items = [
        ProblemSummary(
            id=problem.id,
            title=problem.title,
            slug=problem.slug,
            topic=problem.topic,
            difficulty=problem.difficulty,
            runtime_shape=_resolved_runtime_shape(problem),
            status=problem.status,
            updated_at=problem.updated_at,
        )
        for problem in problems
    ]
    return ProblemListResponse(items=items, total=len(items))


@router.post("/generate", response_model=ProblemGenerationResponse)
def generate_problem(
    payload: ProblemGenerationRequest,
) -> ProblemGenerationResponse:
    workdir = Path(__file__).resolve().parents[4]
    return generate_problem_draft(payload.problem_statement, workdir=workdir)


@router.get("/{slug}", response_model=ProblemDetail)
def get_problem(slug: str, db: Session = Depends(get_db)) -> ProblemDetail:
    problem = db.scalar(select(Problem).where(Problem.slug == slug))
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")
    return _problem_to_detail(problem)


@router.post("", response_model=ProblemDetail, status_code=status.HTTP_201_CREATED)
def create_problem(payload: ProblemCreate, db: Session = Depends(get_db)) -> ProblemDetail:
    existing = db.scalar(select(Problem).where(Problem.slug == payload.slug))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A problem with this slug already exists.")

    unsupported_problem_message = detect_unsupported_problem_shape(
        payload.topic,
        payload.description,
        payload.starter_code,
    )
    if unsupported_problem_message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=unsupported_problem_message)

    problem = Problem(
        title=payload.title,
        slug=payload.slug,
        topic=payload.topic,
        difficulty=payload.difficulty,
        description=payload.description,
        runtime_shape=payload.runtime_shape,
        starter_code=payload.starter_code,
        function_name=payload.function_name,
        visible_test_cases=json.dumps([case.model_dump() for case in payload.visible_test_cases]),
        hidden_test_cases=json.dumps([case.model_dump() for case in payload.hidden_test_cases]),
        status="not_started",
        notes=payload.notes,
        similar_questions=payload.similar_questions,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return _problem_to_detail(problem)


def _run_problem(
    slug: str,
    payload: CodeExecutionRequest,
    mode: str,
    db: Session,
) -> ExecutionResponse:
    problem = db.scalar(select(Problem).where(Problem.slug == slug))
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    visible_cases = [TestCaseCreate(**item) for item in json.loads(problem.visible_test_cases)]
    hidden_cases = [TestCaseCreate(**item) for item in json.loads(problem.hidden_test_cases or "[]")]
    test_cases = visible_cases if mode == "run" or not hidden_cases else visible_cases + hidden_cases

    response = execute_code(
        code=payload.code,
        language=payload.language,
        function_name=problem.function_name,
        problem_topic=problem.topic,
        runtime_shape=_resolved_runtime_shape(problem),
        test_cases=test_cases,
        mode=mode,
    )

    if mode == "submit":
        problem.status = "solved" if response.all_passed else "attempted"
        submission = Submission(
            problem_id=problem.id,
            mode=mode,
            language=payload.language,
            code_snapshot=payload.code,
            results_json=json.dumps([item.model_dump() for item in response.results]),
            passed_count=response.passed_count,
            total_count=response.total_count,
            all_passed=response.all_passed,
            error=response.error,
        )
        db.add(problem)
        db.add(submission)
        db.commit()

    return response


@router.post("/{slug}/run", response_model=ExecutionResponse)
def run_problem(
    slug: str,
    payload: CodeExecutionRequest,
    db: Session = Depends(get_db),
) -> ExecutionResponse:
    return _run_problem(slug=slug, payload=payload, mode="run", db=db)


@router.post("/{slug}/submit", response_model=ExecutionResponse)
def submit_problem(
    slug: str,
    payload: CodeExecutionRequest,
    db: Session = Depends(get_db),
) -> ExecutionResponse:
    return _run_problem(slug=slug, payload=payload, mode="submit", db=db)


@router.patch("/{slug}/status", response_model=ProblemSummary)
def update_problem_status(
    slug: str,
    payload: ProblemStatusUpdate,
    db: Session = Depends(get_db),
) -> ProblemSummary:
    problem = db.scalar(select(Problem).where(Problem.slug == slug))
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    problem.status = payload.status
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return ProblemSummary(
        id=problem.id,
        title=problem.title,
        slug=problem.slug,
        topic=problem.topic,
        difficulty=problem.difficulty,
        runtime_shape=_resolved_runtime_shape(problem),
        status=problem.status,
        updated_at=problem.updated_at,
    )


@router.patch("/{slug}/workspace", response_model=ProblemDetail)
def update_problem_workspace(
    slug: str,
    payload: ProblemWorkspaceUpdate,
    db: Session = Depends(get_db),
) -> ProblemDetail:
    problem = db.scalar(select(Problem).where(Problem.slug == slug))
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    problem.notes = payload.notes
    problem.similar_questions = payload.similar_questions
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return _problem_to_detail(problem)


@router.get("/{slug}/submissions", response_model=list[SubmissionHistoryItem])
def list_problem_submissions(
    slug: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[SubmissionHistoryItem]:
    problem = db.scalar(select(Problem).where(Problem.slug == slug))
    if problem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found.")

    submissions = db.scalars(
        select(Submission)
        .where(Submission.problem_id == problem.id)
        .order_by(Submission.created_at.desc(), Submission.id.desc())
        .limit(limit)
    ).all()
    return [_serialize_submission(item) for item in submissions]
