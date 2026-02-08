#!/bin/bash
set -e

# ============================================================================
# LexiqAI Frontend Deployment (Dev)
# Build Next.js and deploy to Azure Static Web Apps
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROJECT_NAME="lexiqai"
ENVIRONMENT="dev"

# Azure Configuration
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-lexiqai-rg-dev}"
SWA_NAME="${PROJECT_NAME}-web-${ENVIRONMENT}"

# Next.js build output (next.config has output: 'export')
FRONTEND_DIR="$PROJECT_ROOT/apps/web-frontend"
OUTPUT_DIR="$FRONTEND_DIR/out"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Load .env for NEXT_PUBLIC_* if present
load_env() {
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "$PROJECT_ROOT/.env"
        set +a
        log_info "Loaded .env for build"
    fi
}

# ============================================================================
# BUILD
# ============================================================================
cmd_build() {
    log_info "Building Next.js frontend..."
    log_info "Output: $OUTPUT_DIR (static export)"

    load_env

    cd "$FRONTEND_DIR"

    if [[ ! -f package.json ]]; then
        log_error "package.json not found in $FRONTEND_DIR"
        exit 1
    fi

    log_info "Installing dependencies..."
    npm ci

    log_info "Building (static export)..."
    # Build-time env vars; fallbacks for local dev deploy
    export NODE_ENV=production
    export NEXT_PUBLIC_ENTRA_ID_TENANT_ID="${NEXT_PUBLIC_ENTRA_ID_TENANT_ID:-}"
    export NEXT_PUBLIC_ENTRA_ID_CLIENT_ID="${NEXT_PUBLIC_ENTRA_ID_CLIENT_ID:-}"
    export NEXT_PUBLIC_ENTRA_ID_AUTHORITY="${NEXT_PUBLIC_ENTRA_ID_AUTHORITY:-https://login.microsoftonline.com/common}"
    export NEXT_PUBLIC_APP_URL="${NEXT_PUBLIC_APP_URL:-}"
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-}"
    export NEXT_PUBLIC_ENABLE_GOOGLE_SIGNIN="${NEXT_PUBLIC_ENABLE_GOOGLE_SIGNIN:-true}"
    export NEXT_PUBLIC_ENABLE_EMAIL_OTP="${NEXT_PUBLIC_ENABLE_EMAIL_OTP:-true}"

    npm run build

    if [[ ! -d "$OUTPUT_DIR" ]]; then
        log_error "Build did not produce $OUTPUT_DIR (check next.config output: 'export')"
        exit 1
    fi

    log_success "Frontend built successfully"
    log_info "Contents: $OUTPUT_DIR"
}

# ============================================================================
# DEPLOY (to Azure Static Web App)
# ============================================================================
cmd_deploy() {
    if [[ ! -d "$OUTPUT_DIR" ]]; then
        log_error "Build output not found. Run build first: make deploy-frontend-build"
        exit 1
    fi

    log_info "Deploying to Azure Static Web App..."
    log_info "App: $SWA_NAME"
    log_info "Resource Group: $RESOURCE_GROUP"

    if ! command -v az &>/dev/null; then
        log_error "Azure CLI not found. Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    if ! az account show &>/dev/null; then
        log_error "Not logged in to Azure. Run: az login"
        exit 1
    fi

    if ! az staticwebapp show --name "$SWA_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        log_error "Static Web App '$SWA_NAME' not found in resource group '$RESOURCE_GROUP'"
        log_info "Create it with Terraform first, or set AZURE_RESOURCE_GROUP"
        exit 1
    fi

    log_info "Getting deployment token..."
    DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
        --name "$SWA_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.apiKey" -o tsv)

    if [[ -z "$DEPLOYMENT_TOKEN" ]]; then
        log_error "Could not get deployment token"
        exit 1
    fi

    # Deploy using Azure Static Web Apps CLI
    if command -v swa &>/dev/null; then
        log_info "Using swa CLI..."
        cd "$FRONTEND_DIR"
        swa deploy "$OUTPUT_DIR" --deployment-token "$DEPLOYMENT_TOKEN" --env production
    else
        log_info "Using npx @azure/static-web-apps-cli..."
        cd "$FRONTEND_DIR"
        npx --yes @azure/static-web-apps-cli deploy "$OUTPUT_DIR" \
            --deployment-token "$DEPLOYMENT_TOKEN" \
            --env production
    fi

    DEFAULT_HOSTNAME=$(az staticwebapp show \
        --name "$SWA_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "defaultHostname" -o tsv 2>/dev/null || true)

    log_success "Frontend deployed successfully"
    if [[ -n "$DEFAULT_HOSTNAME" ]]; then
        echo ""
        log_info "URL: https://${DEFAULT_HOSTNAME}"
    fi
}

# ============================================================================
# ALL (build + deploy)
# ============================================================================
cmd_all() {
    log_info "============================================"
    log_info "Frontend deployment (dev)"
    log_info "============================================"
    echo ""
    cmd_build
    echo ""
    cmd_deploy
    echo ""
    log_success "Frontend deployment complete!"
}

# ============================================================================
# STATUS
# ============================================================================
cmd_status() {
    log_info "Static Web App: $SWA_NAME"
    log_info "Resource Group: $RESOURCE_GROUP"
    echo ""

    if ! az staticwebapp show --name "$SWA_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        log_error "Static Web App not found"
        exit 1
    fi

    DEFAULT_HOSTNAME=$(az staticwebapp show \
        --name "$SWA_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "defaultHostname" -o tsv)
    echo "  URL: https://${DEFAULT_HOSTNAME}"
}

# ============================================================================
# MAIN
# ============================================================================
usage() {
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build   Build Next.js (static export to apps/web-frontend/out)"
    echo "  deploy  Deploy built output to Azure Static Web App"
    echo "  all     Build and deploy"
    echo "  status  Show Static Web App URL"
    echo ""
    echo "Environment:"
    echo "  AZURE_RESOURCE_GROUP  Resource group (default: lexiqai-rg-dev)"
    echo "  NEXT_PUBLIC_*        Set in .env or env for build"
}

case "${1:-}" in
    build)  cmd_build ;;
    deploy) cmd_deploy ;;
    all)    cmd_all ;;
    status) cmd_status ;;
    -h|--help|help) usage ;;
    *)
        if [[ -z "${1:-}" ]]; then usage; else log_error "Unknown command: $1"; usage; exit 1; fi
        ;;
esac
