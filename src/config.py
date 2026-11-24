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


def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    FIGURES_DIR.mkdir(exist_ok=True)


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
