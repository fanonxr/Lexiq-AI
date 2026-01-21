#!/bin/bash
# Script to update Terraform provider lock file with checksums for all platforms
# This ensures the lock file works across macOS, Linux, and Windows
#
# Usage: ./update-provider-lock.sh
# Or: cd infra/terraform && ../scripts/update-provider-lock.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${GREEN}=== Updating Terraform Provider Lock File ===${NC}"
echo ""
echo "This will update .terraform.lock.hcl with checksums for all platforms:"
echo "  - darwin_amd64 (Intel Mac)"
echo "  - darwin_arm64 (Apple Silicon Mac)"
echo "  - linux_amd64 (Linux)"
echo "  - windows_amd64 (Windows)"
echo ""

cd "$TERRAFORM_DIR"

# Check if terraform is available
if ! command -v terraform &> /dev/null; then
    echo -e "${YELLOW}Error: terraform command not found${NC}"
    echo "Please install Terraform first"
    exit 1
fi

# Update lock file with all platforms
echo -e "${YELLOW}Updating provider lock file...${NC}"
terraform providers lock \
  -platform=darwin_amd64 \
  -platform=darwin_arm64 \
  -platform=linux_amd64 \
  -platform=windows_amd64

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Provider lock file updated successfully!${NC}"
    echo ""
    echo "The lock file now includes checksums for all platforms."
    echo "This ensures Terraform works on macOS, Linux, and Windows."
else
    echo ""
    echo -e "${YELLOW}✗ Failed to update lock file${NC}"
    echo "Please check your network connection and try again"
    exit 1
fi
