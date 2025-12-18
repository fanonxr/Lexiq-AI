"""RabbitMQ queue setup service.

This module handles the initialization of RabbitMQ queues, exchanges, and
dead-letter queues for the document ingestion service.
"""

import aio_pika
from aio_pika import ExchangeType

from document_ingestion.config import get_settings
from document_ingestion.utils.logging import get_logger

logger = get_logger("queue_setup")
settings = get_settings()


async def setup_queues(connection: aio_pika.abc.AbstractConnection) -> None:
    """
    Set up RabbitMQ queues, exchanges, and dead-letter queues.

    Creates:
    1. Main exchange (direct): `document-ingestion-exchange`
    2. Main queue: `document-ingestion` (durable, with DLX)
    3. Dead-letter exchange: `document-ingestion-dlx` (direct)
    4. Dead-letter queue: `document-ingestion-dlq` (durable)

    Args:
        connection: RabbitMQ connection instance

    Raises:
        Exception: If queue setup fails
    """
    try:
        # Create channel
        channel = await connection.channel()
        logger.info("Created RabbitMQ channel for queue setup")

        # Configure channel QoS (prefetch count)
        await channel.set_qos(prefetch_count=settings.rabbitmq.prefetch_count)
        logger.info(f"Set channel QoS prefetch_count={settings.rabbitmq.prefetch_count}")

        # 1. Create dead-letter exchange (direct exchange)
        dlx_name = f"{settings.rabbitmq.exchange_name}-dlx"
        dlx = await channel.declare_exchange(
            name=dlx_name,
            type=ExchangeType.DIRECT,
            durable=True,  # Survive broker restarts
        )
        logger.info(f"Created dead-letter exchange: {dlx_name}")

        # 2. Create dead-letter queue (durable)
        dlq = await channel.declare_queue(
            name=settings.rabbitmq.dead_letter_queue_name,
            durable=settings.rabbitmq.queue_durable,
        )
        logger.info(
            f"Created dead-letter queue: {settings.rabbitmq.dead_letter_queue_name} "
            f"(durable={settings.rabbitmq.queue_durable})"
        )

        # 3. Bind dead-letter queue to dead-letter exchange
        await dlq.bind(dlx, routing_key=settings.rabbitmq.routing_key)
        logger.info(
            f"Bound dead-letter queue to exchange with routing_key={settings.rabbitmq.routing_key}"
        )

        # 4. Create main exchange (direct exchange)
        exchange = await channel.declare_exchange(
            name=settings.rabbitmq.exchange_name,
            type=ExchangeType.DIRECT,
            durable=True,  # Survive broker restarts
        )
        logger.info(f"Created main exchange: {settings.rabbitmq.exchange_name}")

        # 5. Prepare queue arguments (for dead-letter exchange and TTL)
        queue_arguments = {
            "x-dead-letter-exchange": dlx_name,  # Route failed messages to DLX
            "x-dead-letter-routing-key": settings.rabbitmq.routing_key,  # Use same routing key
        }

        # Add message TTL if configured
        if settings.rabbitmq.message_ttl:
            queue_arguments["x-message-ttl"] = settings.rabbitmq.message_ttl
            logger.info(f"Configured message TTL: {settings.rabbitmq.message_ttl}ms")

        # 6. Create main queue (durable, with DLX configuration)
        queue = await channel.declare_queue(
            name=settings.rabbitmq.queue_name,
            durable=settings.rabbitmq.queue_durable,
            arguments=queue_arguments,
        )
        logger.info(
            f"Created main queue: {settings.rabbitmq.queue_name} "
            f"(durable={settings.rabbitmq.queue_durable}, "
            f"dlx={dlx_name})"
        )

        # 7. Bind main queue to main exchange with routing key
        await queue.bind(exchange, routing_key=settings.rabbitmq.routing_key)
        logger.info(
            f"Bound main queue to exchange with routing_key={settings.rabbitmq.routing_key}"
        )

        logger.info("RabbitMQ queue setup completed successfully")
        logger.info(f"  - Main Exchange: {settings.rabbitmq.exchange_name}")
        logger.info(f"  - Main Queue: {settings.rabbitmq.queue_name}")
        logger.info(f"  - Dead-Letter Exchange: {dlx_name}")
        logger.info(f"  - Dead-Letter Queue: {settings.rabbitmq.dead_letter_queue_name}")

    except Exception as e:
        logger.error(f"Failed to set up RabbitMQ queues: {e}", exc_info=True)
        raise


async def verify_queues(connection: aio_pika.abc.AbstractConnection) -> dict:
    """
    Verify that queues and exchanges exist.

    Args:
        connection: RabbitMQ connection instance

    Returns:
        dict: Status of queues and exchanges
    """
    try:
        channel = await connection.channel()

        # Check main queue
        try:
            main_queue = await channel.declare_queue(
                name=settings.rabbitmq.queue_name,
                passive=True,  # Only check if exists, don't create
            )
            main_queue_exists = True
            main_queue_message_count = main_queue.declaration_result.message_count
        except Exception:
            main_queue_exists = False
            main_queue_message_count = None

        # Check dead-letter queue
        try:
            dlq = await channel.declare_queue(
                name=settings.rabbitmq.dead_letter_queue_name,
                passive=True,  # Only check if exists, don't create
            )
            dlq_exists = True
            dlq_message_count = dlq.declaration_result.message_count
        except Exception:
            dlq_exists = False
            dlq_message_count = None

        # Check exchanges (declare with passive=True to check existence)
        try:
            main_exchange = await channel.declare_exchange(
                name=settings.rabbitmq.exchange_name,
                type=ExchangeType.DIRECT,
                passive=True,  # Only check if exists, don't create
            )
            main_exchange_exists = True
        except Exception:
            main_exchange_exists = False

        dlx_name = f"{settings.rabbitmq.exchange_name}-dlx"
        try:
            dlx = await channel.declare_exchange(
                name=dlx_name,
                type=ExchangeType.DIRECT,
                passive=True,  # Only check if exists, don't create
            )
            dlx_exists = True
        except Exception:
            dlx_exists = False

        return {
            "main_queue": {
                "exists": main_queue_exists,
                "name": settings.rabbitmq.queue_name,
                "message_count": main_queue_message_count,
            },
            "dead_letter_queue": {
                "exists": dlq_exists,
                "name": settings.rabbitmq.dead_letter_queue_name,
                "message_count": dlq_message_count,
            },
            "main_exchange": {
                "exists": main_exchange_exists,
                "name": settings.rabbitmq.exchange_name,
            },
            "dead_letter_exchange": {
                "exists": dlx_exists,
                "name": dlx_name,
            },
        }
    except Exception as e:
        logger.error(f"Failed to verify queues: {e}", exc_info=True)
        return {
            "error": str(e),
        }

