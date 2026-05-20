from app.database import SessionLocal, init_db
from app.schemas.job import ScrapeRequest
from app.services.jobs import run_scrape


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = run_scrape(db, request=ScrapeRequest(send_alerts=True))
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
