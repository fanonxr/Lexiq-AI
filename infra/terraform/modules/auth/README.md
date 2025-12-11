# Auth Module (Placeholder)

Terraform module for Microsoft Entra External ID / Azure AD B2C configuration.

## Status

🚧 **Placeholder** - Entra ID B2C configuration is primarily done manually in Azure Portal.

## Why Manual Setup?

Microsoft Entra External ID (Azure AD B2C) configuration is complex and often requires:
- Manual tenant creation
- User flow configuration via Azure Portal UI
- Identity provider setup (Microsoft, Google, etc.)
- Custom branding and policies

While some aspects can be automated with Terraform (App Registrations), the full setup is typically done manually for better control and visibility.

## What Can Be Automated?

Future enhancements may include:
- App Registration creation
- API permissions configuration
- Redirect URI management
- Certificate/key management

## Current Approach

1. **Manual Setup**: Follow [Entra ID Setup Guide](/docs/foundation/entra-id-setup.md)
2. **Store Credentials**: Use Azure Key Vault or environment variables
3. **Reference in Code**: Use stored Client ID and Tenant ID

## Configuration Values Needed

After manual setup, you'll need:
- **Tenant ID**: Directory (tenant) ID
- **Client ID**: Application (client) ID
- **Authority URL**: For External ID, the B2C authority URL

Store these in:
- Local: `.env.local` file
- Azure: Key Vault or Container App environment variables

## Documentation

See [Entra ID Setup Guide](/docs/foundation/entra-id-setup.md) for complete setup instructions.

