from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_database


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
