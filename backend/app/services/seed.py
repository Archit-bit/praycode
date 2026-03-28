import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.seed_problems import SEED_PROBLEMS
from app.models.problem import Problem


def seed_database(db: Session) -> None:
    existing = db.scalar(select(Problem.id).limit(1))
    if existing is not None:
        return

    for item in SEED_PROBLEMS:
        problem = Problem(
            title=item["title"],
            slug=item["slug"],
            topic=item["topic"],
            difficulty=item["difficulty"],
            description=item["description"],
            starter_code=item["starter_code"],
            function_name=item["function_name"],
            visible_test_cases=json.dumps(item["visible_test_cases"]),
            hidden_test_cases=json.dumps(item.get("hidden_test_cases", [])),
            status="not_started",
            notes=item.get("notes", ""),
            similar_questions=item.get("similar_questions", ""),
        )
        db.add(problem)

    db.commit()
