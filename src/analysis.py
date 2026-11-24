import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import DATA_DIR


matplotlib.use("Agg")
FIGURES_DIR = DATA_DIR.parent / "figures"
sns.set_theme(style="whitegrid")


def save_figure(name):
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / name, dpi=150)
    plt.close()


def run_analysis(df: pd.DataFrame):
    """EDA of the processed data (dataframe loaded from the database)"""

    FIGURES_DIR.mkdir(exist_ok=True)

    print("Shape (rows, columns):", df.shape)
    print("\nData types:")
    print(df.dtypes)
    numeric_cols = ["runtime", "rating_average", "weight", "run_years", "premiere_year"]
    print("\nDescriptive statistics:")
    print(df[numeric_cols].describe().round(2))

    print("\nShows without rating:", f"{df['rating_average'].isna().mean():.1%}")
    print("Correlations:")
    print(df[numeric_cols].corr().round(2))
    for col in ["type", "status", "language", "rating_band"]:
        print(f"\n{col}:")
        print(df[col].value_counts().head(5))

    by_type = (
        df.groupby("type")
        .agg(
            shows=("show_id", "count"),
            avg_rating=("rating_average", "mean"),
            median_runtime=("runtime", "median"),
        )
        .round(2)
    )
    print("\nBy type:")
    print(by_type.sort_values("avg_rating", ascending=False))

    print("\nBy status (average rating):")
    print(df.groupby("status")["rating_average"].mean().round(2))

    genres = df.assign(genre=df["genres"].str.split(", ")).explode("genre")
    by_genre = (
        genres.groupby("genre")
        .agg(shows=("show_id", "count"), avg_rating=("rating_average", "mean"))
        .query("shows >= 5")
        .sort_values("avg_rating", ascending=False)
        .round(2)
    )
    print("\nBy genre (genres with at least 5 shows):")
    print(by_genre.head(10))

    # 4. Visualizations
    rated = df["rating_average"].dropna()

    # Q1: how are ratings distributed?
    plt.figure(figsize=(8, 5))
    sns.histplot(rated, bins=30, kde=True, color="steelblue", edgecolor="black")
    plt.axvline(
        rated.mean(), color="red", linestyle="--", label=f"mean = {rated.mean():.2f}"
    )
    plt.axvline(
        rated.median(),
        color="green",
        linestyle=":",
        label=f"median = {rated.median():.2f}",
    )
    plt.title("Distribution of average show rating")
    plt.xlabel("average rating (0-10)")
    plt.ylabel("number of shows")
    plt.legend()
    save_figure("fig1_rating_distribution.png")

    # Q2: do show types differ in rating?
    plt.figure(figsize=(9, 5))
    sns.boxplot(data=df, x="type", y="rating_average", color="lightsteelblue")
    plt.title("Rating by show type")
    plt.xlabel("show type")
    plt.ylabel("average rating")
    plt.xticks(rotation=30)
    save_figure("fig2_rating_by_type.png")

    # Q3: how did the number of shows change over the decades?
    by_decade = df.dropna(subset=["premiere_decade"]).astype({"premiere_decade": int})
    plt.figure(figsize=(9, 5))
    sns.countplot(data=by_decade, x="premiere_decade", hue="status")
    plt.title("Shows by premiere decade and status")
    plt.xlabel("premiere decade")
    plt.ylabel("number of shows")
    plt.legend(title="status")
    save_figure("fig3_shows_per_decade.png")

    # Q4: which genres have the highest ratings?
    top_genres = by_genre.head(10)
    plt.figure(figsize=(8, 5))
    sns.barplot(x=top_genres["avg_rating"], y=top_genres.index, color="seagreen")
    plt.title("Top 10 genres by average rating (genres with 5+ shows)")
    plt.xlabel("average rating")
    plt.ylabel("genre")
    save_figure("fig4_rating_by_genre.png")

    # 5. Findings
    type_ratings = by_type["avg_rating"].dropna()
    print("\nFindings:")
    print(
        f"- Mean rating {rated.mean():.2f}, median {rated.median():.2f}; "
        f"{df['rating_average'].isna().mean():.1%} of shows have no rating."
    )
    print(
        f"- Best type by rating: {type_ratings.idxmax()} ({type_ratings.max():.2f}), "
        f"worst: {type_ratings.idxmin()} ({type_ratings.min():.2f})."
    )
    print(f"- Most common type: {df['type'].value_counts().idxmax()}.")
    print(f"- Decade with most shows: {int(by_decade['premiere_decade'].mode()[0])}.")
    if len(by_genre):
        print(
            f"- Best genre: {by_genre.index[0]} ({by_genre['avg_rating'].iloc[0]:.2f})."
        )
    print(
        f"- Correlation runtime vs rating: {df['runtime'].corr(df['rating_average']):.2f}."
    )
