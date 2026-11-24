from typing import Any
import json
from datetime import datetime

from confluent_kafka import KafkaError, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from src.config import KAFKA_TOPIC, KAFKA_BOOTSTRAP_SERVERS, RAW_API_JSON
from src.api_client import flatten_show


def ensure_topic() -> None:
    """Check that the broker is reachable and create the topic if it does not exist"""

    admin = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})
    admin.list_topics(timeout=10)
    futures = admin.create_topics(
        [NewTopic(KAFKA_TOPIC, num_partitions=1, replication_factor=1)]
    )
    for topic, future in futures.items():
        try:
            future.result()
            print(f"Topic '{topic}' created.")
        except KafkaException as exc:
            if exc.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                print(f"Topic '{topic}' already exists.")
            else:
                raise


def serialize(record: dict[str, Any]) -> str:
    """JSON serialisation"""

    return json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8")


def build_records() -> tuple[list[dict, Any], int]:
    with open(RAW_API_JSON, encoding="utf-8") as f:
        raw_shows = json.load(f)
    records = []
    for show in raw_shows:
        record = flatten_show(show)
        records.append(record)
    real_count = len(records)
    return records, real_count


def run_producer():
    if not RAW_API_JSON.exists():
        raise FileNotFoundError("data/raw_api_response.json not found")

    records, real_count = build_records()
    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        ensure_topic()
    except KafkaException as exc:
        raise KafkaException(
            f"Cannot connect to / configure Kafka at {KAFKA_BOOTSTRAP_SERVERS}: {exc}\n"
            "Start the broker first: docker compose up -d"
        )

    producer = Producer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "acks": "all",
            "enable.idempotence": True,
            "message.timeout.ms": 30000,
        }
    )
    counters = {"ok": 0, "failed": 0}

    def on_delivery(error, _message):
        """On delivery callback after server received message"""

        if error is not None:
            counters["failed"] += 1
            print(f"Delivery failed: {error}")
        else:
            counters["ok"] += 1

    for record in records:
        try:
            payload = serialize(record)
        except ValueError as exc:
            counters["failed"] += 1
            print(f"Could not serialise record {record.get('id')}: {exc}")
            continue
        while True:
            try:
                producer.produce(
                    KAFKA_TOPIC,
                    key=str(record["id"]).encode("utf-8"),
                    value=payload,
                    headers=[("run_id", run_id.encode("utf-8"))],
                    on_delivery=on_delivery,
                )
                break
            except BufferError:
                producer.poll(1.0)
            except KafkaException as exc:
                counters["failed"] += 1
                print(f"Could not send record {record.get('id')}: {exc}")
                break
        producer.poll(0)

    remaining = producer.flush(30)
    if remaining:
        counters["failed"] += remaining
        print(f"{remaining} messages were not delivered before the timeout")

    print(f"Produced: {counters['ok']}")
    print(f"Failed: {counters['failed']}")
