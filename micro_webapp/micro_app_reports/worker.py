import json
import logging
import os
import time

import pika

import sync
import upsert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reports-worker")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://eduflex:eduflexRabbit1@rabbitmq:5672/")
EXCHANGE = "eduflex.events"
QUEUE_NAME = "reports_queue"
BINDINGS = ["user.#", "course.#", "enrollment.#"]

HANDLERS = {
    "user.created": upsert.upsert_user,
    "course.created": upsert.upsert_course,
    "course.updated": upsert.upsert_course,
    "course.deactivated": upsert.upsert_course,
    "enrollment.created": upsert.upsert_enrollment,
    "enrollment.cancelled": upsert.upsert_enrollment,
    "enrollment.status_changed": upsert.append_status_history,
}


def _connect():
    while True:
        try:
            return pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        except Exception:
            logger.warning("RabbitMQ no disponible todavia, reintentando en 5s...")
            time.sleep(5)


def _on_message(channel, method, properties, body):
    routing_key = method.routing_key
    handler = HANDLERS.get(routing_key)
    if handler:
        try:
            handler(json.loads(body))
        except Exception:
            logger.exception("Error procesando evento '%s'", routing_key)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    logger.info("Sincronizacion inicial (backfill) antes de escuchar eventos...")
    try:
        sync.refresh()
    except Exception:
        logger.exception("Backfill inicial fallo, se sigue igual escuchando eventos")

    connection = _connect()
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    for pattern in BINDINGS:
        channel.queue_bind(exchange=EXCHANGE, queue=QUEUE_NAME, routing_key=pattern)

    channel.basic_qos(prefetch_count=10)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=_on_message)

    logger.info("Escuchando eventos en '%s'...", QUEUE_NAME)
    channel.start_consuming()


if __name__ == "__main__":
    main()
