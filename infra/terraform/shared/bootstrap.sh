#!/bin/bash
# Bootstrap script for Terraform state storage
# This temporarily disables the backend config to create the storage account

set -e

BACKEND_FILE="backend-shared.tf"
BACKEND_DISABLED="${BACKEND_FILE}.disabled"

echo "🔧 Bootstrap: Temporarily disabling backend configuration..."

# Check if backend is already disabled
if [ -f "$BACKEND_DISABLED" ]; then
    echo "⚠️  Backend is already disabled. Restoring it first..."
    mv "$BACKEND_DISABLED" "$BACKEND_FILE"
fi

# Disable backend for bootstrap
if [ -f "$BACKEND_FILE" ]; then
    mv "$BACKEND_FILE" "$BACKEND_DISABLED"
    echo "✅ Backend configuration disabled"
else
    echo "⚠️  Backend file not found, continuing..."
fi

echo ""
echo "📦 Initializing Terraform with local state..."
terraform init

echo ""
echo "📋 Running terraform plan..."
terraform plan -var-file=shared.tfvars

echo ""
echo "✅ Ready to apply! Run: terraform apply -var-file=shared.tfvars"
echo ""
echo "After the storage account is created, run: ./restore-backend.sh"
