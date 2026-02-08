#!/bin/bash
set -e

# ============================================================================
# LexiqAI Dev Deployment Script
# Build, push, and deploy Docker images to Azure Container Apps
# ============================================================================

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROJECT_NAME="lexiqai"
ENVIRONMENT="dev"

# Azure Configuration (can be overridden via environment variables)
ACR_NAME="${ACR_NAME:-lexiqaiacrshared}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-lexiqai-rg-dev}"

# Services to deploy
SERVICES=(
    "api-core"
    "cognitive-orch"
    "voice-gateway"
    "document-ingestion"
    "integration-worker"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Generate image tag based on git commit or timestamp
generate_tag() {
    if git rev-parse --git-dir > /dev/null 2>&1; then
        GIT_SHA=$(git rev-parse --short HEAD)
        IMAGE_TAG="${ENVIRONMENT}-${GIT_SHA}"
    else
        TIMESTAMP=$(date +%Y%m%d-%H%M%S)
        IMAGE_TAG="${ENVIRONMENT}-${TIMESTAMP}"
    fi
    echo "$IMAGE_TAG"
}

# ============================================================================
# BUILD COMMAND
# ============================================================================
cmd_build() {
    local service_filter="$1"
    
    log_info "Building Docker images..."
    log_info "Project root: $PROJECT_ROOT"
    
    cd "$PROJECT_ROOT"
    
    for service in "${SERVICES[@]}"; do
        if [[ -n "$service_filter" && "$service" != "$service_filter" ]]; then
            continue
        fi
        
        DOCKERFILE="docker/${service}/Dockerfile"
        
        if [[ ! -f "$DOCKERFILE" ]]; then
            log_warning "Dockerfile not found for $service at $DOCKERFILE, skipping..."
            continue
        fi
        
        log_info "Building $service..."
        
        # Build with local tag for now (will be retagged during push)
        docker build \
            -t "${PROJECT_NAME}/${service}:local" \
            -f "$DOCKERFILE" \
            .
        
        log_success "Built $service"
    done
    
    log_success "All images built successfully!"
    echo ""
    log_info "Local images:"
    docker images | grep "${PROJECT_NAME}/" | head -20
}

# ============================================================================
# PUSH COMMAND
# ============================================================================
cmd_push() {
    local service_filter="$1"
    local image_tag="${2:-$(generate_tag)}"
    
    log_info "Pushing Docker images to Azure Container Registry..."
    log_info "ACR: ${ACR_NAME}.azurecr.io"
    log_info "Tag: $image_tag"
    
    # Login to Azure ACR
    log_info "Logging into Azure Container Registry..."
    az acr login --name "$ACR_NAME" || {
        log_error "Failed to login to ACR. Make sure you're logged into Azure CLI (az login)"
        exit 1
    }
    
    for service in "${SERVICES[@]}"; do
        if [[ -n "$service_filter" && "$service" != "$service_filter" ]]; then
            continue
        fi
        
        LOCAL_IMAGE="${PROJECT_NAME}/${service}:local"
        REMOTE_IMAGE="${ACR_NAME}.azurecr.io/${PROJECT_NAME}/${service}"
        
        # Check if local image exists
        if ! docker image inspect "$LOCAL_IMAGE" > /dev/null 2>&1; then
            log_warning "Local image $LOCAL_IMAGE not found. Run 'make deploy-build' first. Skipping..."
            continue
        fi
        
        log_info "Tagging and pushing $service..."
        
        # Tag with commit SHA
        docker tag "$LOCAL_IMAGE" "${REMOTE_IMAGE}:${image_tag}"
        docker push "${REMOTE_IMAGE}:${image_tag}"
        
        # Also tag as dev-latest
        docker tag "$LOCAL_IMAGE" "${REMOTE_IMAGE}:${ENVIRONMENT}-latest"
        docker push "${REMOTE_IMAGE}:${ENVIRONMENT}-latest"
        
        log_success "Pushed $service"
    done
    
    log_success "All images pushed successfully!"
    echo ""
    log_info "Pushed images:"
    echo "  Tag: $image_tag"
    echo "  Latest: ${ENVIRONMENT}-latest"
    
    # Save the tag for deploy step
    echo "$image_tag" > "$PROJECT_ROOT/.last-image-tag"
}

# ============================================================================
# DEPLOY COMMAND
# ============================================================================
cmd_deploy() {
    local service_filter="$1"
    local image_tag="${2:-}"
    
    # Try to read the last pushed tag if not provided
    if [[ -z "$image_tag" && -f "$PROJECT_ROOT/.last-image-tag" ]]; then
        image_tag=$(cat "$PROJECT_ROOT/.last-image-tag")
    fi
    
    if [[ -z "$image_tag" ]]; then
        image_tag=$(generate_tag)
        log_warning "No image tag specified or found. Using: $image_tag"
    fi
    
    log_info "Deploying to Azure Container Apps..."
    log_info "Resource Group: $RESOURCE_GROUP"
    log_info "Image Tag: $image_tag"
    
    for service in "${SERVICES[@]}"; do
        if [[ -n "$service_filter" && "$service" != "$service_filter" ]]; then
            continue
        fi
        
        APP_NAME="${PROJECT_NAME}-${service}-${ENVIRONMENT}"
        IMAGE_REF="${ACR_NAME}.azurecr.io/${PROJECT_NAME}/${service}:${image_tag}"
        
        log_info "Updating $APP_NAME with image $IMAGE_REF..."
        
        # Check if the Container App exists
        if ! az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" > /dev/null 2>&1; then
            log_warning "Container App $APP_NAME not found in resource group $RESOURCE_GROUP. Skipping..."
            continue
        fi
        
        # Update the Container App with new image
        az containerapp update \
            --name "$APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --image "$IMAGE_REF" \
            --set-env-vars "DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --output none
        
        log_success "Updated $APP_NAME"
    done
    
    log_success "Deployment complete!"
    echo ""
    log_info "Verifying deployments..."
    
    for service in "${SERVICES[@]}"; do
        if [[ -n "$service_filter" && "$service" != "$service_filter" ]]; then
            continue
        fi
        
        APP_NAME="${PROJECT_NAME}-${service}-${ENVIRONMENT}"
        
        if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" > /dev/null 2>&1; then
            REVISION=$(az containerapp revision list \
                --name "$APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --query "[0].name" -o tsv 2>/dev/null || echo "unknown")
            STATE=$(az containerapp revision list \
                --name "$APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --query "[0].properties.runningState" -o tsv 2>/dev/null || echo "unknown")
            echo "  $APP_NAME: $REVISION ($STATE)"
        fi
    done
}

# ============================================================================
# ALL COMMAND (build + push + deploy)
# ============================================================================
cmd_all() {
    local service_filter="$1"
    local image_tag=$(generate_tag)
    
    log_info "============================================"
    log_info "Full deployment pipeline"
    log_info "Environment: $ENVIRONMENT"
    log_info "Image Tag: $image_tag"
    log_info "============================================"
    echo ""
    
    # Step 1: Build
    log_info "Step 1/3: Building Docker images..."
    echo ""
    cmd_build "$service_filter"
    echo ""
    
    # Step 2: Push
    log_info "Step 2/3: Pushing to Azure Container Registry..."
    echo ""
    cmd_push "$service_filter" "$image_tag"
    echo ""
    
    # Step 3: Deploy
    log_info "Step 3/3: Deploying to Azure Container Apps..."
    echo ""
    cmd_deploy "$service_filter" "$image_tag"
    echo ""
    
    log_success "============================================"
    log_success "Full deployment pipeline completed!"
    log_success "============================================"
}

# ============================================================================
# STATUS COMMAND
# ============================================================================
cmd_status() {
    log_info "Checking deployment status..."
    log_info "Resource Group: $RESOURCE_GROUP"
    echo ""
    
    for service in "${SERVICES[@]}"; do
        APP_NAME="${PROJECT_NAME}-${service}-${ENVIRONMENT}"
        
        if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" > /dev/null 2>&1; then
            IMAGE=$(az containerapp show \
                --name "$APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --query "properties.template.containers[0].image" -o tsv 2>/dev/null || echo "unknown")
            STATE=$(az containerapp revision list \
                --name "$APP_NAME" \
                --resource-group "$RESOURCE_GROUP" \
                --query "[0].properties.runningState" -o tsv 2>/dev/null || echo "unknown")
            echo -e "${GREEN}✓${NC} $APP_NAME"
            echo "    Image: $IMAGE"
            echo "    State: $STATE"
        else
            echo -e "${RED}✗${NC} $APP_NAME (not found)"
        fi
    done
}

# ============================================================================
# MAIN
# ============================================================================
usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  build [service]   Build Docker images for all services (or a specific service)"
    echo "  push [service]    Push images to Azure Container Registry"
    echo "  deploy [service]  Update Azure Container Apps with new images"
    echo "  all [service]     Run build, push, and deploy in sequence"
    echo "  status            Show current deployment status"
    echo ""
    echo "Options:"
    echo "  service           Optional: api-core, cognitive-orch, voice-gateway,"
    echo "                              document-ingestion, integration-worker"
    echo ""
    echo "Environment Variables:"
    echo "  ACR_NAME              Azure Container Registry name (default: lexiqaiacrshared)"
    echo "  AZURE_RESOURCE_GROUP  Azure Resource Group (default: lexiqai-rg-dev)"
    echo ""
    echo "Examples:"
    echo "  $0 build                    # Build all services"
    echo "  $0 build api-core           # Build only api-core"
    echo "  $0 push                     # Push all services to ACR"
    echo "  $0 deploy                   # Deploy all services to Container Apps"
    echo "  $0 all                      # Full pipeline: build, push, deploy"
    echo "  $0 all api-core             # Full pipeline for api-core only"
    echo "  $0 status                   # Check deployment status"
}

COMMAND="${1:-}"
SERVICE="${2:-}"

case "$COMMAND" in
    build)
        cmd_build "$SERVICE"
        ;;
    push)
        cmd_push "$SERVICE"
        ;;
    deploy)
        cmd_deploy "$SERVICE"
        ;;
    all)
        cmd_all "$SERVICE"
        ;;
    status)
        cmd_status
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        if [[ -z "$COMMAND" ]]; then
            usage
        else
            log_error "Unknown command: $COMMAND"
            echo ""
            usage
            exit 1
        fi
        ;;
esac
