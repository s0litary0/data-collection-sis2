# Data Dictionary

**Project:** TVmaze data streaming and validation pipeline
**Source:** TVmaze public API


## Stored table `shows` (SQLite)

- Database file: `data/db.sqlite`. 
- Primary key: `show_id`.

### Original columns

| Column | SQL type | Nullable | Description / change from flat record |
|---|---|---|---|
| `show_id` | INTEGER | No (primary key) | From `id` |
| `name` | TEXT | No | Trimmed, repeated spaces collapsed |
| `type` | TEXT | No | Trimmed, title case |
| `language` | TEXT | No | Title case; missing values replaced by `Unknown` |
| `status` | TEXT | No | Trimmed, title case |
| `genres` | TEXT | No | Genres sorted, title case, joined with `", "`; empty list replaced by `Unknown` |
| `runtime` | INTEGER | Yes | Minutes; missing values filled (see imputation below) |
| `rating_average` | REAL | Yes | Left empty (NULL) when the show has no rating |
| `weight` | INTEGER | Yes | Popularity score, rounded |
| `premiered` | TEXT | Yes | ISO date `YYYY-MM-DD` |
| `ended` | TEXT | Yes | ISO date; NULL means the show has not ended |
| `network_name` | TEXT | No | Network name; if missing, web channel name; otherwise `Unknown` |
| `network_country` | TEXT | No | Upper case country code; `Unknown` if missing |
| `updated_at` | TEXT | Yes | `updated` converted to `YYYY-MM-DD HH:MM:SS` |
| `url` | TEXT | Yes | TVmaze page |

### Derived columns (created during cleaning)

| Column | SQL type | Nullable | How it is calculated |
|---|---|---|---|
| `weight_log` | REAL | Yes | `log(1 + weight)` (NumPy `log1p`), reduces skew |
| `premiere_year` | INTEGER | Yes | Year of `premiered` |
| `premiere_decade` | INTEGER | Yes | `premiere_year // 10 * 10` (for example 1994 becomes 1990) |
| `run_years` | REAL | Yes | Years between `premiered` and `ended`; NULL if not ended |
| `rating_band` | TEXT | No | `Unrated` if no rating, `Low` below 6, `Medium` below 7.5, otherwise `High` |
| `is_long_runtime` | INTEGER | No | 1 if `runtime >= 60`, otherwise 0 |
| `runtime_zscore` | REAL | Yes | `(runtime - mean) / standard deviation` |
| `runtime_imputed` | BOOLEAN | No | True if `runtime` was missing and filled |

### Table constraints

| Constraint | Rule |
|---|---|
| Primary key | `show_id` is unique, so repeated loading cannot create duplicates |
| `rating_between_0_and_10` | `rating_average` between 0 and 10 |
| `runtime_positive` | `runtime` greater than 0 |
| NOT NULL | `name`, `type`, `language`, `status`, `genres`, `network_name`, `network_country`, `rating_band`, `is_long_runtime`, `runtime_imputed` |


Deliberately invalid records are appended after the real data to prove that validation works. They have `is_test_record = True`, are rejected by the Pandera schema, written to `data/invalid_records.csv` with the reasons, and never reach the cleaned data or the database.