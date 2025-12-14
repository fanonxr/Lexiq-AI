# MSAL Authentication Configuration

This directory contains the Microsoft Authentication Library (MSAL) configuration for LexiqAI.

## Files

- **`msalConfig.ts`** - MSAL configuration and request parameters
- **`msalInstance.ts`** - MSAL instance factory and singleton management

## Usage

### Basic Setup

```typescript
import { getMsalInstance } from '@/lib/auth/msalInstance';
import { loginRequest } from '@/lib/auth/msalConfig';

// Get MSAL instance
const msalInstance = getMsalInstance();

// Login
await msalInstance.loginPopup(loginRequest);
```

### Configuration

All configuration is derived from environment variables via `@/lib/env`:

- `NEXT_PUBLIC_ENTRA_ID_CLIENT_ID` - Azure AD application (client) ID
- `NEXT_PUBLIC_ENTRA_ID_TENANT_ID` - Azure AD tenant ID
- `NEXT_PUBLIC_ENTRA_ID_AUTHORITY` - Azure AD authority URL

### Request Configurations

- **`loginRequest`** - Standard login request with scopes: `openid`, `profile`, `email`, `User.Read`
- **`silentRequest`** - Silent token acquisition for refresh
- **`logoutRequest`** - Logout configuration
- **`tokenRequest(scopes)`** - Custom token request with specific scopes

### Validation

The configuration is automatically validated when the MSAL instance is created. If required environment variables are missing, an error will be thrown.

## Security Notes

- Tokens are stored in `sessionStorage` (more secure than `localStorage`)
- Auth state is NOT stored in cookies
- PII logging is disabled
- Only error-level logging in production

## Next Steps

This configuration will be used by:
- `AuthProvider` component (Phase 2.2) ✅
- `useAuth` hook (Phase 2.2) ✅
- Proxy for route protection (Phase 2.3) ✅
