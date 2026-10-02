"""CLI: python -m app.fetch"""
from .db import create_db_and_tables
from .fetcher import run_fetcher


def main() -> None:
    create_db_and_tables()
    stats = run_fetcher()
    print(
        f"Fetched {stats['fetched']} jobs, "
        f"{stats['new']} new, "
        f"{stats['errors']} errors."
    )


if __name__ == "__main__":
    main()
