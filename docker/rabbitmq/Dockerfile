# RabbitMQ Dockerfile
# Extends the official RabbitMQ image with custom configuration
FROM rabbitmq:3-management-alpine

# Enable management plugin by default
RUN rabbitmq-plugins enable rabbitmq_management

# Default command (can be overridden)
CMD ["rabbitmq-server"]
