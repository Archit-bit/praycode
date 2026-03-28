from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.routes.health import router as health_router
from app.api.routes.problems import router as problems_router
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_database


def apply_runtime_migrations() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "submissions" in table_names:
        submission_columns = {column["name"] for column in inspector.get_columns("submissions")}
        if "language" not in submission_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE submissions ADD COLUMN language VARCHAR(32) NOT NULL DEFAULT 'python'")
                )

    if "problems" in table_names:
        problem_columns = {column["name"] for column in inspector.get_columns("problems")}
        if "runtime_shape" not in problem_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE problems ADD COLUMN runtime_shape VARCHAR(64) NOT NULL DEFAULT 'plain'")
                )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_runtime_migrations()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app = FastAPI(
    title="DSA Practice MVP API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(problems_router)
