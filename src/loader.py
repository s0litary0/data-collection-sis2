from typing import Any

import pandas as pd
from sqlalchemy import CheckConstraint, String, column, create_engine, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from src.config import DATA_DIR


DB_PATH = DATA_DIR / "db.sqlite"
engine = create_engine(f"sqlite:///{DB_PATH}")


class Base(DeclarativeBase):
    pass


class Show(Base):
    """Shows table"""

    __tablename__ = "shows"
    __table_args__ = (
        CheckConstraint(
            column("rating_average").between(0, 10), name="rating_between_0_and_10"
        ),
        CheckConstraint(column("runtime") > 0, name="runtime_positive"),
    )

    show_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    genres: Mapped[str] = mapped_column(String, nullable=False)
    runtime: Mapped[int | None]
    rating_average: Mapped[float | None]
    weight: Mapped[int | None]
    weight_log: Mapped[float | None]
    premiered: Mapped[str | None]
    ended: Mapped[str | None]
    premiere_year: Mapped[int | None]
    premiere_decade: Mapped[int | None]
    run_years: Mapped[float | None]
    network_name: Mapped[str] = mapped_column(String, nullable=False)
    network_country: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str | None]
    url: Mapped[str | None]
    rating_band: Mapped[str] = mapped_column(String, nullable=False)
    is_long_runtime: Mapped[int]
    runtime_imputed: Mapped[bool]


def to_python(value: Any) -> Any:
    """Handle pd.NA and other pandas types"""

    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def load_data(session, records: dict[str, Any]) -> int:
    """Insert records"""

    before = session.scalar(select(func.count(Show.show_id)))
    session.execute(
        insert(Show).on_conflict_do_nothing(index_elements=["show_id"]), records
    )
    session.commit()
    after = session.scalar(select(func.count(Show.show_id)))
    return after - before, after


def snapshot(session) -> tuple[tuple[str, ...]]:
    """All rows of the table as a list of tuples (to compare the table before and after)"""

    shows = session.scalars(select(Show).order_by(Show.show_id)).all()
    return [tuple(hasattr(show, col.name) for col in Show.__table__.columns) for show in shows]


def verify_database(session) -> None:
    print("\nVerification queries")

    # 1. number of rows
    total = session.scalar(select(func.count(Show.show_id)))
    print("\nNumber of rows:", total)

    # 2. duplicate ids = all rows - distinct ids (must be 0)
    distinct_ids = session.scalar(select(func.count(Show.show_id.distinct())))
    print("Duplicate ids (must be 0):", total - distinct_ids)


def run_loading(clean_df: pd.DataFrame) -> int:
    """Create database, load clean data twice, check idempotency, verify the data"""

    DATA_DIR.mkdir(exist_ok=True)

    records = [
        {key: to_python(value) for key, value in row.items()}
        for row in clean_df.to_dict("records")
    ]
    print("Processed records (after cleaning):", len(records))

    Base.metadata.drop_all(
        engine
    ) 
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        inserted_1, count_1 = load_data(session, records)
        print(f"Load 1: inserted {inserted_1} rows, rows in table: {count_1}")
        table_1 = snapshot(session)

        inserted_2, count_2 = load_data(session, records)
        print(f"Load 2: inserted {inserted_2} rows, rows in table: {count_2}")
        table_2 = snapshot(session)

        print("\nIdempotency check:")
        print("Same number of rows after both loads:", count_1 == count_2)
        print("Table content unchanged by 2nd load:", table_1 == table_2)
        print(f"Processed records: {len(records)} | stored records: {count_2}")

        verify_database(session)

    return count_2
