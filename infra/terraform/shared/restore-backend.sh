#!/bin/bash
# Restore backend configuration and migrate to remote state

set -e

BACKEND_FILE="backend-shared.tf"
BACKEND_DISABLED="${BACKEND_FILE}.disabled"

echo "🔄 Restoring backend configuration..."

# Check if backend is disabled
if [ ! -f "$BACKEND_DISABLED" ]; then
    echo "⚠️  Backend is not disabled. Nothing to restore."
    exit 0
fi

# Restore backend
mv "$BACKEND_DISABLED" "$BACKEND_FILE"
echo "✅ Backend configuration restored"

# Backup local state
if [ -f "terraform.tfstate" ]; then
    BACKUP_FILE="terraform.tfstate.local-backup-$(date +%Y%m%d-%H%M%S)"
    cp terraform.tfstate "$BACKUP_FILE"
    echo "✅ Local state backed up to: $BACKUP_FILE"
fi

echo ""
echo "📦 Migrating to remote state..."
terraform init -migrate-state

echo ""
echo "✅ Migration complete! State is now stored in Azure Storage."
echo "   Verify with: terraform state list"
