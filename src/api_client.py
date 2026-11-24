from typing import Any
import json
import time

import pandas as pd
from requests import Session
from requests.exceptions import RequestException

from src.config import (
    SHOWS_URL,
    MAX_RETRIES,
    MAX_RECORDS,
    REQUEST_TIMEOUT_SECONDS,
    RAW_API_JSON,
    RAW_CSV,
)
from src.config import ensure_dirs


class ApiError(Exception):
    pass


def fetch_page(session: Session, page: int) -> list[dict[str, Any]]:
    """Fetch one page of shows"""

    params = {"page": page}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                SHOWS_URL,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except RequestException as exc:
            print(f"[Attempt {attempt}] network error: {exc}")
            time.sleep(0.5 * attempt)
            continue

        status = response.status_code
        if status == 200:
            try:
                return response.json()
            except ValueError:
                print(f"[Attempt {attempt}] response is not valid JSON")
                time.sleep(0.5 * attempt)
                continue
        if status == 404:
            return []
    raise ApiError(f"Page {page} failed after {MAX_RETRIES} attempts")


def collect_shows(max_records: int) -> list[dict[str, Any]]:
    """Request pages until at least max_records shows are collected"""

    shows, page = [], 0
    with Session() as session:
        while len(shows) < max_records:
            print(f"Requesting page {page}")
            batch = fetch_page(session, page)
            if not batch:
                break
            shows.extend(batch)
            page += 1
            time.sleep(0.5)
    return shows[:max_records], page


def flatten_show(show: dict[str, Any]) -> dict[str, Any]:
    """Turn one nested API object into a flat record"""

    network = show.get("network") or {}
    country = network.get("country") or {}
    web_channel = show.get("webChannel") or {}
    rating = show.get("rating") or {}
    return {
        "id": show.get("id"),
        "name": show.get("name"),
        "type": show.get("type"),
        "language": show.get("language"),
        "genres": show.get("genres") or [],
        "status": show.get("status"),
        "runtime": show.get("runtime"),
        "averageRuntime": show.get("averageRuntime"),
        "premiered": show.get("premiered"),
        "ended": show.get("ended"),
        "rating_average": rating.get("average"),
        "weight": show.get("weight"),
        "network_name": network.get("name"),
        "network_country": country.get("code"),
        "web_channel_name": web_channel.get("name"),
        "updated": show.get("updated"),
        "url": show.get("url"),
    }


def save_raw(shows: list[dict, Any]):
    ensure_dirs()
    with open(RAW_API_JSON, "w", encoding="utf-8") as f:
        json.dump(shows, f, ensure_ascii=False)
    flat = pd.DataFrame([flatten_show(s) for s in shows])
    flat["genres"] = flat["genres"].map(lambda g: "|".join(g))
    flat.to_csv(RAW_CSV, index=False)


def run_collect():
    try:
        shows, pages = collect_shows(MAX_RECORDS)
    except ApiError as exc:
        raise ApiError(f"API collection failed: {exc}")
    if not shows:
        raise Exception("No records collected")
    save_raw(shows)