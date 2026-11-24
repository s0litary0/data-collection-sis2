import numpy as np
import pandas as pd

from src.config import DATA_DIR

CLEAN_CSV = DATA_DIR / "clean_data.csv"


def run_cleaning(df: pd.DataFrame):
    """Clean and transform validated data. Returns clean dataframe and saves it to csv"""

    df = df.copy()
    print("Rows at start:", len(df))

    # 1. Missing values
    missing = df.isna().sum()
    print("\nMissing values:")
    print(missing[missing > 0])

    # 2. Duplicates
    before = len(df)
    df = df.drop_duplicates(subset="id")
    print("\nDuplicates removed:", before - len(df))

    # 3. Text normalization
    for col in ["name", "type", "status", "language", "network_name", "url"]:
        df[col] = df[col].str.strip().str.replace(r"\s+", " ", regex=True)
    for col in ["type", "status", "language"]:
        df[col] = df[col].str.title()
    df["network_country"] = df["network_country"].str.strip().str.upper()
    df["genres"] = df["genres"].map(lambda g: sorted({x.strip().title() for x in g}))

    # 4. Handle missing values
    df["runtime_imputed"] = df["runtime"].isna()
    df["runtime"] = df["runtime"].fillna(df["averageRuntime"])
    df["runtime"] = df["runtime"].fillna(
        df.groupby("type")["runtime"].transform("median")
    )
    df["runtime"] = df["runtime"].fillna(df["runtime"].median())
    df["network_name"] = df["network_name"].fillna(df["web_channel_name"])
    for col in ["language", "network_name", "network_country"]:
        df[col] = df[col].fillna("Unknown")
    df["genres"] = df["genres"].map(lambda g: g if len(g) > 0 else ["Unknown"])
    df = df.drop(columns=["averageRuntime", "web_channel_name"])

    # 5. Data types
    df["id"] = df["id"].astype(int)
    df["premiered"] = pd.to_datetime(df["premiered"], format="%Y-%m-%d")
    df["ended"] = pd.to_datetime(df["ended"], format="%Y-%m-%d")
    df["updated_at"] = pd.to_datetime(df["updated"], unit="s")
    df["runtime"] = df["runtime"].round().astype("Int64")
    df["weight"] = df["weight"].round().astype("Int64")

    # 6. NumPy operations
    rating = df["rating_average"].to_numpy(dtype=float)
    runtime = df["runtime"].to_numpy(dtype=float, na_value=np.nan)
    weight = df["weight"].to_numpy(dtype=float, na_value=np.nan)

    df["rating_band"] = np.select(
        [np.isnan(rating), rating < 6, rating < 7.5],
        ["Unrated", "Low", "Medium"],
        default="High",
    )
    df["weight_log"] = np.round(np.log1p(weight), 3)
    df["is_long_runtime"] = np.where(runtime >= 60, 1, 0)
    df["run_years"] = np.round((df["ended"] - df["premiered"]).dt.days / 365.25, 2)
    df["premiere_year"] = df["premiered"].dt.year.astype("Int64")
    df["premiere_decade"] = df["premiere_year"] // 10 * 10
    print("\nNumPy columns added: rating_band, weight_log, is_long_runtime, run_years")

    # 7. Filtering with several conditions
    modern_rated = df[
        (df["premiere_year"] >= 2000)
        & (df["rating_average"].notna())
        & (df["runtime"] >= 20)
        & (df["status"].isin(["Running", "Ended"]))
    ]
    print(
        f"\nFilter (premiered >= 2000, rated, runtime >= 20, running/ended): "
        f"{len(modern_rated)} of {len(df)} shows"
    )

    # 8. GroupBy with aggregation
    by_type = (
        df.groupby("type")
        .agg(
            shows=("id", "count"),
            avg_rating=("rating_average", "mean"),
            median_runtime=("runtime", "median"),
        )
        .round(2)
    )
    print("\nGroupBy type:")
    print(by_type.sort_values("shows", ascending=False))

    # 9. Reshaping with pivot_table
    pivot = df.pivot_table(
        index="premiere_decade",
        columns="type",
        values="id",
        aggfunc="count",
        fill_value=0,
    )
    print("\nPivot table (shows per decade and type):")
    print(pivot)

    # Final table for the database
    df = df.rename(columns={"id": "show_id"})
    df["genres"] = df["genres"].map(", ".join)
    df["premiered"] = df["premiered"].dt.strftime("%Y-%m-%d")
    df["ended"] = df["ended"].dt.strftime("%Y-%m-%d")
    df["updated_at"] = df["updated_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    clean_df = df[
        [
            "show_id",
            "name",
            "type",
            "language",
            "status",
            "genres",
            "runtime",
            "rating_average",
            "weight",
            "weight_log",
            "premiered",
            "ended",
            "premiere_year",
            "premiere_decade",
            "run_years",
            "network_name",
            "network_country",
            "updated_at",
            "url",
            "rating_band",
            "is_long_runtime",
            "runtime_zscore",
            "runtime_imputed",
        ]
    ]

    DATA_DIR.mkdir(exist_ok=True)
    clean_df.to_csv(CLEAN_CSV, index=False)
    print("\nRows after cleaning:", len(clean_df))
    return clean_df
