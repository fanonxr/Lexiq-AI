# Multi-stage build for voice-gateway service
# Stage 1: Build
FROM golang:1.22-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Set working directory
WORKDIR /build

# Copy go mod files
COPY apps/voice-gateway/go.mod apps/voice-gateway/go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY apps/voice-gateway/ ./

# Sync vendor directory if it exists, or use -mod=mod to ignore it
# This fixes inconsistent vendoring errors
RUN if [ -d vendor ]; then \
        go mod vendor; \
    fi

# Build the binary
# CGO_ENABLED=0 creates a statically linked binary
# -ldflags="-w -s" reduces binary size by stripping debug info
# Use -mod=mod to ignore vendor directory if it's inconsistent
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -mod=mod \
    -ldflags="-w -s" \
    -o voice-gateway \
    ./cmd/server

# Stage 2: Runtime
FROM alpine:latest

# Install ca-certificates for HTTPS and curl for health checks
RUN apk --no-cache add ca-certificates curl tzdata

# Create non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /build/voice-gateway .

# Copy timezone data
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the binary
CMD ["./voice-gateway"]

