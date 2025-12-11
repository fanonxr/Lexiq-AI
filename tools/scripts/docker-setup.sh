#!/bin/bash
# Docker Setup Script for LexiqAI Local Development
# This script initializes the Docker Compose environment and verifies services are healthy

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐳 LexiqAI Docker Setup${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop and try again.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ docker-compose is not installed. Please install Docker Compose.${NC}"
    exit 1
fi

# Determine docker-compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}📦 Starting Docker services...${NC}"
$DOCKER_COMPOSE up -d

echo ""
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 5

# Health check function
check_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if $DOCKER_COMPOSE ps "$service" | grep -q "healthy\|Up"; then
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Check PostgreSQL
echo -n "Checking PostgreSQL"
if check_service postgres; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}PostgreSQL failed to start. Check logs with: make docker-logs${NC}"
    exit 1
fi

# Check Redis
echo -n "Checking Redis"
if check_service redis; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Redis failed to start. Check logs with: make docker-logs${NC}"
    exit 1
fi

# Check Qdrant
echo -n "Checking Qdrant"
if check_service qdrant; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Qdrant failed to start. Check logs with: make docker-logs${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ All services are running!${NC}"
echo ""
echo "Service URLs:"
echo "  PostgreSQL:  localhost:5432"
echo "  Redis:       localhost:6379"
echo "  Qdrant:      http://localhost:6333 (REST), localhost:6334 (gRPC)"
echo ""
echo "Connection details:"
echo "  PostgreSQL User:     ${POSTGRES_USER:-admin}"
echo "  PostgreSQL Password: ${POSTGRES_PASSWORD:-password}"
echo "  PostgreSQL Database: ${POSTGRES_DB:-lexiqai_local}"
echo ""
echo "Useful commands:"
echo "  make docker-logs    - View service logs"
echo "  make docker-ps      - Show running containers"
echo "  make docker-down     - Stop services"
echo "  make docker-clean    - Remove containers and volumes"
echo ""

