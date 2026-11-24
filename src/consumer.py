import json
import time
import uuid
from typing import Any

from confluent_kafka import OFFSET_BEGINNING, Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient

from src.config import KAFKA_TOPIC, KAFKA_BOOTSTRAP_SERVERS

IDLE_TIMEOUT = 20


def deserialize(raw_bytes: bytes) -> dict[str, Any]:
    """JSON deserialisation"""

    return json.loads(raw_bytes.decode("utf-8"))


def run_consumer() -> list[dict[str, Any]]:
    try:
        AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS}).list_topics(timeout=10)
    except KafkaException as exc:
        raise KafkaException(
            f"Cannot connect to Kafka at {KAFKA_BOOTSTRAP_SERVERS}: {exc}\n"
            "Start the broker first: docker compose up -d"
        )

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": f"tvmaze-consumer-{uuid.uuid4()}",
            "enable.auto.commit": False,
        }
    )

    partition = TopicPartition(KAFKA_TOPIC, 0, OFFSET_BEGINNING)
    consumer.assign([partition])
    low, high = consumer.get_watermark_offsets(partition, timeout=10)
    expected = high - low
    print(f"Broker reports {expected} messages in '{KAFKA_TOPIC}'")

    records: list[dict[str, Any]] = []
    bad_messages, kafka_errors = 0, 0
    stop_reason = "idle timeout"
    last_activity = time.monotonic()

    try:
        while len(records) + bad_messages < expected:
            message = consumer.poll(1.0)
            if message is None:
                if time.monotonic() - last_activity > IDLE_TIMEOUT:
                    break
                continue
            if message.error():
                kafka_errors += 1
                print(f"Kafka error: {message.error()}")
                if message.error().fatal():
                    stop_reason = "fatal Kafka error"
                    break
                continue

            last_activity = time.monotonic()
            try:
                records.append(deserialize(message.value()))
            except (ValueError, UnicodeDecodeError) as exc:
                bad_messages += 1
                print(f"Could not deserialise offset {message.offset()}: {exc}")
        else:
            stop_reason = "all messages in the topic consumed"
    except KafkaException as exc:
        print(f"Kafka error while consuming: {exc}")
        stop_reason = "kafka exception"
    finally:
        consumer.close()

    print(f"Consumed {len(records)} of {expected} messages; stop reason: {stop_reason}")
    print(f"Undecodable: {bad_messages}")
    print(f"Kafka errors: {kafka_errors}")
    return records