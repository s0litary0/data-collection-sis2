import pandas as pd
from sqlalchemy import select

from src.loader import engine, Show


def run_read() -> pd.DataFrame:
    """Read data from db.sqlite"""

    return pd.read_sql(select(Show), engine)
