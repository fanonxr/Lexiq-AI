# Redis Dockerfile
# Extends the official Redis image with custom configuration
FROM redis:7-alpine

# Copy custom Redis configuration if needed
# COPY redis.conf /usr/local/etc/redis/redis.conf

# Redis runs as root by default in the official image
# For production, consider creating a non-root user
# USER redis

# Default command (can be overridden)
CMD ["redis-server", "--appendonly", "yes"]
