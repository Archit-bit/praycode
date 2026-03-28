from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, status

from app.schemas.problem import ProblemGenerationResponse, TestCaseCreate
from app.services.language_support import (
    build_starter_codes,
    build_python_starter_code,
    detect_unsupported_problem_shape,
    infer_runtime_shape,
    resolve_parameter_names,
)


CODEX_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "topic": {"type": "string"},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "description": {"type": "string"},
        "runtime_shape": {"type": "string", "enum": ["plain", "linked_list", "random_pointer_linked_list"]},
        "function_name": {"type": "string"},
        "starter_code": {"type": "string"},
        "visible_test_cases": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "input_json": {"type": "string"},
                    "expected_output_json": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["input_json", "expected_output_json", "explanation"],
                "additionalProperties": False,
            },
        },
        "hidden_test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "input_json": {"type": "string"},
                    "expected_output_json": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["input_json", "expected_output_json", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "title",
        "topic",
        "difficulty",
        "description",
        "runtime_shape",
        "function_name",
        "starter_code",
        "visible_test_cases",
        "hidden_test_cases",
    ],
    "additionalProperties": False,
}


GENERATION_PROMPT_TEMPLATE = """You are generating a structured draft for a personal DSA practice app.

Given the problem statement below, infer the metadata needed to run solutions locally.

Requirements:
- Return only schema-valid JSON.
- Keep the title concise.
- Use one topic string such as Arrays, Hashing, Stack, Binary Search, Trees, Graphs, Dynamic Programming, Sliding Window, Two Pointers, Greedy.
- Difficulty must be easy, medium, or hard.
- description should be a clean markdown problem statement with sections such as Overview, Example, Constraints when useful.
- runtime_shape must be one of:
  - plain
  - linked_list
  - random_pointer_linked_list
- function_name must be a valid Python snake_case function name.
- starter_code must be plain Python code only, with exactly one function definition matching function_name and a pass statement.
- For Linked List problems, starter_code should follow the usual ListNode/head style used in interview practice. Keep test cases as JSON arrays of node values; the runtime will convert them into linked lists automatically.
- For random pointer linked-list problems such as Copy Random List, use runtime_shape `random_pointer_linked_list`. Test cases should represent the list as JSON arrays of `[value, random_index]` pairs.
- visible_test_cases should contain 3 to 5 strong cases.
- hidden_test_cases can contain 0 to 3 extra edge cases.
- Each input_json must be valid JSON representing the positional argument list passed into the function.
- Each expected_output_json must be valid JSON.
- Do not wrap code in markdown fences.
- Do not mention Codex, NeetCode, or LeetCode.

Problem statement:
{problem_statement}
"""


def _slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.strip().lower())).strip("-")


def _sanitize_function_name(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip())
    sanitized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", sanitized).lower()
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "solve"


def _strip_code_fences(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_+-]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    return stripped.strip()


def _parse_case_list(raw_cases: list[dict[str, str]]) -> list[TestCaseCreate]:
    cases: list[TestCaseCreate] = []
    for item in raw_cases:
        try:
            parsed_input = json.loads(item["input_json"])
            parsed_expected = json.loads(item["expected_output_json"])
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Codex generated invalid JSON test data: {exc}",
            ) from exc

        cases.append(
            TestCaseCreate(
                input=parsed_input,
                expected_output=parsed_expected,
                explanation=item.get("explanation", ""),
            )
        )
    return cases


def generate_problem_draft(problem_statement: str, workdir: Path, timeout_seconds: int = 90) -> ProblemGenerationResponse:
    prompt = GENERATION_PROMPT_TEMPLATE.format(problem_statement=problem_statement.strip())

    with tempfile.TemporaryDirectory(prefix="codex-problem-draft-") as temp_dir:
        temp_path = Path(temp_dir)
        schema_path = temp_path / "schema.json"
        output_path = temp_path / "draft.json"
        schema_path.write_text(json.dumps(CODEX_OUTPUT_SCHEMA), encoding="utf-8")

        try:
            completed = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--skip-git-repo-check",
                    "--ephemeral",
                    "--output-schema",
                    str(schema_path),
                    "-o",
                    str(output_path),
                    prompt,
                ],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Codex generation timed out. Try again with a shorter problem statement.",
            ) from exc

        if completed.returncode != 0 or not output_path.exists():
            detail = completed.stderr.strip() or completed.stdout.strip() or "Codex did not return a valid draft."
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        try:
            raw_output = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Codex returned malformed JSON output.",
            ) from exc

    title = raw_output["title"].strip() or "Untitled Problem"
    function_name = _sanitize_function_name(raw_output["function_name"])
    visible_test_cases = _parse_case_list(raw_output["visible_test_cases"])
    hidden_test_cases = _parse_case_list(raw_output["hidden_test_cases"])
    topic = raw_output["topic"].strip() or "General"
    description = raw_output["description"].strip()
    runtime_shape = raw_output.get("runtime_shape") or infer_runtime_shape(topic, description)
    raw_starter_code = _strip_code_fences(raw_output["starter_code"])
    unsupported_problem_message = detect_unsupported_problem_shape(topic, description, raw_starter_code)
    if unsupported_problem_message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=unsupported_problem_message)

    parameter_names, generation_warnings = resolve_parameter_names(
        topic,
        function_name,
        raw_starter_code,
        description,
        visible_test_cases,
        runtime_shape,
    )
    starter_code = build_python_starter_code(function_name, parameter_names, raw_starter_code, topic, runtime_shape)
    starter_codes = build_starter_codes(topic, function_name, starter_code, description, visible_test_cases, runtime_shape)

    return ProblemGenerationResponse(
        title=title,
        slug=_slugify(title),
        topic=topic,
        difficulty=raw_output["difficulty"],
        description=description,
        runtime_shape=runtime_shape,
        starter_code=starter_code,
        starter_codes=starter_codes,
        function_name=function_name,
        visible_test_cases=visible_test_cases,
        hidden_test_cases=hidden_test_cases,
        generation_warnings=generation_warnings,
    )
