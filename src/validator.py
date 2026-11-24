from typing import Any

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

from src.config import DATA_DIR

DATE_FORMAT = "%Y-%m-%d"
VALID_CSV = DATA_DIR / "valid_records.csv"
INVALID_CSV = DATA_DIR / "invalid_records.csv"

ALLOWED_TYPES = [
    "Scripted",
    "Animation",
    "Reality",
    "Talk Show",
    "Documentary",
    "Game Show",
    "News",
    "Sports",
    "Variety",
    "Award Show",
    "Panel Show",
]
ALLOWED_STATUSES = ["Running", "Ended", "To Be Determined", "In Development"]


def make_test_record(**changes):
    """Returns valid test record"""

    record = {
        "id": 9000000,
        "name": "TEST",
        "type": "Scripted",
        "language": "English",
        "genres": ["Drama"],
        "status": "Running",
        "runtime": 45,
        "averageRuntime": 45,
        "premiered": "2020-01-01",
        "ended": None,
        "rating_average": 7.5,
        "weight": 80,
        "network_name": "Test Network",
        "network_country": "US",
        "web_channel_name": None,
        "updated": 1700000000,
        "url": "https://example.com/test",
        "is_test_record": True,
    }
    record.update(changes)
    return record


def make_test_records(real_record):
    """7 invalid records to show that the schema finds errors"""

    return [
        # numbers out of range
        make_test_record(
            id=9000001,
            name="TEST numeric ranges",
            runtime=-30,
            averageRuntime=0,
            rating_average=42.5,
            weight=150,
        ),
        # missing name, wrong date, wrong language
        make_test_record(
            id=9000002, name=None, premiered="2020-13-45", language="123!!"
        ),
        # wrong category, ended before premiered, wrong url
        make_test_record(
            id=9000003,
            name="TEST category and dates",
            type="Cartoon",
            status="Cancelled",
            premiered="2015-06-01",
            ended="2010-01-01",
            url="not-a-url",
        ),
        # duplicate id (same id as a real record)
        {**real_record, "name": "TEST duplicate id", "is_test_record": True},
        # empty name and id = 0
        make_test_record(id=0, name="   "),
        # genres is not a list, updated is negative
        make_test_record(
            id=9000006, name="TEST wrong types", genres="Drama", updated=-5
        ),
        # values just outside the bounds
        make_test_record(
            id=9000007, name="TEST boundary values", rating_average=10.5, runtime=1441
        ),
    ]


def dates_in_order(df):
    """True if 'ended' is not earlier than 'premiered' (or one of them is missing)"""

    ended = pd.to_datetime(df["ended"], format=DATE_FORMAT, errors="coerce")
    premiered = pd.to_datetime(df["premiered"], format=DATE_FORMAT, errors="coerce")
    return ended.isna() | premiered.isna() | (ended >= premiered)


def make_schema():
    is_text = pa.Check(
        lambda s: s.map(lambda v: isinstance(v, str) and v.strip() != ""),
        error="must be non-empty text",
    )
    is_date = pa.Check(
        lambda s: pd.to_datetime(s, format=DATE_FORMAT, errors="coerce").notna(),
        error="must be a valid YYYY-MM-DD date",
    )
    is_genre_list = pa.Check(
        lambda s: s.map(
            lambda v: isinstance(v, list) and all(isinstance(g, str) for g in v)
        ),
        error="genres must be a list of text",
    )

    return pa.DataFrameSchema(
        {
            "id": pa.Column(
                int,
                coerce=True,
                nullable=False,
                unique=True,
                report_duplicates="exclude_first",
                checks=pa.Check.gt(0),
            ),
            "name": pa.Column(nullable=False, checks=is_text),
            "type": pa.Column(nullable=False, checks=pa.Check.isin(ALLOWED_TYPES)),
            "language": pa.Column(
                nullable=True, checks=pa.Check.str_matches(r"^[A-Za-z][A-Za-z \-]*$")
            ),
            "genres": pa.Column(nullable=False, checks=is_genre_list),
            "status": pa.Column(nullable=False, checks=pa.Check.isin(ALLOWED_STATUSES)),
            "runtime": pa.Column(
                float, coerce=True, nullable=True, checks=pa.Check.in_range(1, 1440)
            ),
            "averageRuntime": pa.Column(
                float, coerce=True, nullable=True, checks=pa.Check.in_range(1, 1440)
            ),
            "premiered": pa.Column(nullable=True, checks=is_date),
            "ended": pa.Column(nullable=True, checks=is_date),
            "rating_average": pa.Column(
                float, coerce=True, nullable=True, checks=pa.Check.in_range(0, 10)
            ),
            "weight": pa.Column(
                float, coerce=True, nullable=True, checks=pa.Check.in_range(0, 100)
            ),
            "network_name": pa.Column(nullable=True, checks=is_text),
            "network_country": pa.Column(nullable=True, checks=is_text),
            "web_channel_name": pa.Column(nullable=True, checks=is_text),
            "updated": pa.Column(
                float,
                coerce=True,
                nullable=False,
                checks=pa.Check.in_range(0, 4102444800),
            ),
            "url": pa.Column(
                nullable=False, checks=pa.Check.str_matches(r"^https?://")
            ),
            "is_test_record": pa.Column(bool, coerce=True, nullable=False),
        },
        checks=pa.Check(
            dates_in_order, error="ended date must not be earlier than premiered date"
        ),
    )


def run_validation(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate consumed records + test records. Returns valid_df and invalid_df"""

    if not records:
        raise ValueError("no records to validate")

    real_records = [{**record, "is_test_record": False} for record in records]
    df = pd.DataFrame(real_records + make_test_records(real_records[0]))
    is_test = df["is_test_record"].astype(bool)

    try:
        make_schema().validate(df, lazy=True)
        failures = pd.DataFrame(columns=["column", "check", "failure_case", "index"])
    except SchemaErrors as error:
        failures = error.failure_cases

    reasons = {}
    for _, row in failures.dropna(subset=["index"]).iterrows():
        text = f"{row['column']}: {row['check']} (value={row['failure_case']})"
        reasons.setdefault(int(row["index"]), []).append(text)

    invalid_mask = df.index.isin(list(reasons))

    print("Test records (deliberately invalid):")
    for i in df.index[is_test]:
        print("DETECTED" if i in reasons else "NOT DETECTED", "- id =", df.at[i, "id"])
        for text in reasons.get(i, []):
            print("     -", text)

    DATA_DIR.mkdir(exist_ok=True)

    invalid_df = df[invalid_mask].copy()
    invalid_df["validation_errors"] = [" | ".join(reasons[i]) for i in invalid_df.index]
    invalid_df["genres"] = invalid_df["genres"].map(
        lambda g: "|".join(g) if isinstance(g, list) else g
    )
    invalid_df.to_csv(INVALID_CSV, index=False)


    valid_df = (
        df[~invalid_mask & ~is_test]
        .drop(columns=["is_test_record"])
        .reset_index(drop=True)
    )
    valid_to_save = valid_df.copy()
    valid_to_save["genres"] = valid_to_save["genres"].map("|".join)
    valid_to_save.to_csv(VALID_CSV, index=False)

    test_detected = int((is_test & invalid_mask).sum())
    print("\nValidation summary")
    print("Real records received:", len(real_records))
    print(f"Test records detected: {test_detected} of {int(is_test.sum())}")
    print("Valid records:", len(valid_df))
    print(
        "Invalid records:",
        len(invalid_df),
        f"({test_detected} test + {len(invalid_df) - test_detected} real)",
    )

    return valid_df, invalid_df
