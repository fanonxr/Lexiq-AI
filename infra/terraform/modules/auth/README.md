# Azure AD App Registration Module

Terraform module for managing Microsoft Entra ID (Azure AD) App Registration with all required configurations.

## Features

This module automates the creation and configuration of Azure AD App Registrations, including:

- ✅ **App Registration Creation** - Creates the main application registration
- ✅ **Redirect URIs** - Configures web, SPA, and public client redirect URIs
- ✅ **API Permissions** - Sets up Microsoft Graph and other API permissions
- ✅ **Exposed API** - Configures API scopes for frontend-to-backend authentication
- ✅ **Client Secrets** - Creates and stores client secrets in Key Vault
- ✅ **Service Principal** - Automatically creates the service principal
- ✅ **App Roles** - Supports role-based access control (RBAC)

## Usage

See the main Terraform configuration in `../../main.tf` for usage examples.

## Required Permissions

To use this module, you need:

1. **Azure AD Permissions**:
   - `Application Administrator` or `Global Administrator` role
   - Or `Application.ReadWrite.All` API permission

2. **Key Vault Permissions** (if storing secrets):
   - `Key Vault Secrets Officer` or `Key Vault Contributor` role

## Admin Consent

**Important**: Admin consent for API permissions must be granted manually:

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Select your app → API permissions
3. Click "Grant admin consent for [Your Organization]"

Or via Azure CLI:
```bash
az ad app permission admin-consent --id <application-id>
```

## Outputs

The module provides the following outputs:

- `application_id` - Application (Client) ID
- `application_object_id` - Application Object ID
- `service_principal_id` - Service Principal ID
- `authority_url` - Authority URL for authentication
- `tenant_id` - Azure AD Tenant ID
- `application_id_uri` - Application ID URI (for exposed API)
- `client_secret_value` - Client secret value (sensitive, stored in Key Vault)

## Related Documentation

- [Azure AD App Registration Guide](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Microsoft Graph Permissions](https://learn.microsoft.com/en-us/graph/permissions-reference)
