import json
from pathlib import Path

from decouple import config


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIGURES_DIR = PROJECT_ROOT / "figures"

API_BASE_URL = config("TVMAZE_API_URL", cast=str)
SHOWS_URL = f"{API_BASE_URL}/shows"
MAX_RECORDS = config("MAX_RECORDS", cast=int, default=500)
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3

KAFKA_BOOTSTRAP_SERVERS = config("KAFKA_BOOTSTRAP_SERVERS", cast=str, default="localhost:9092")
KAFKA_TOPIC = config("KAFKA_TOPIC", cast=str, default="tvmaze_shows")

RAW_API_JSON = DATA_DIR / "raw_api_response.json"   
RAW_CSV = DATA_DIR / "raw_data.csv"                 
# CONSUMED_JSONL = DATA_DIR / "consumed_messages.jsonl"
# VALID_JSONL = DATA_DIR / "valid_records.jsonl"
# INVALID_CSV = DATA_DIR / "invalid_records.csv"
# CLEAN_CSV = DATA_DIR / "clean_data.csv"
# DB_PATH = DATA_DIR / "output.db"
# STATS_JSON = DATA_DIR / "pipeline_stats.json"


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    FIGURES_DIR.mkdir(exist_ok=True)


# def read_stats():
#     if STATS_JSON.exists():
#         with open(STATS_JSON, encoding="utf-8") as f:
#             return json.load(f)
#     return {}


# def update_stats(stage, values):
#     """Store the counts of one pipeline stage so verify.py can compare them."""
#     ensure_dirs()
#     stats = read_stats()
#     values = dict(values)
#     values["finished_at"] = datetime.now().isoformat(timespec="seconds")
#     stats[stage] = values
#     with open(STATS_JSON, "w", encoding="utf-8") as f:
#         json.dump(stats, f, indent=2)


def _json_default(obj):
    if hasattr(obj, "item"):          
        return obj.item()
    return str(obj)


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=_json_default) + "\n")


def read_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
