import json
import logging
import os

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://eduflex:eduflexRabbit1@rabbitmq:5672/")
EXCHANGE = "eduflex.events"

logger = logging.getLogger("events")


def publish(routing_key: str, payload: dict) -> None:
    """Publica un evento en el exchange compartido. Si el broker no responde,
    se registra el error y se sigue: la fila ya quedo guardada en la base,
    el refresh periodico de reports sirve de red de seguridad."""
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payload, default=str),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
        connection.close()
    except Exception:
        logger.exception("No se pudo publicar el evento '%s'", routing_key)
