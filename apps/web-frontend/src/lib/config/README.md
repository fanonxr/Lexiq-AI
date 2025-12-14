# Configuration Files

This directory contains environment variable configuration files organized by context.

## Structure

```
lib/config/
├── browser/
│   └── env.ts          # Client-side environment variables (NEXT_PUBLIC_*)
└── server/
    └── env.ts          # Server-side environment variables (secrets, API keys)
```

## Usage

### Browser/Client-Side

```typescript
// ✅ Use in Client Components, browser code
import { getEnv } from '@/lib/config/browser/env';

const env = getEnv();
const tenantId = env.entraId.tenantId;
const clientId = env.entraId.clientId;
```

### Server-Side

```typescript
// ✅ Use in Server Components, API Routes, Server Actions
import { getServerEnv } from '@/lib/config/server/env';

const serverEnv = getServerEnv();
const apiKey = serverEnv.api.secretKey;
```

## Important Notes

1. **Browser config** (`browser/env.ts`) - Only `NEXT_PUBLIC_*` variables
2. **Server config** (`server/env.ts`) - Variables WITHOUT `NEXT_PUBLIC_` prefix
3. **Lazy loading** - Both configs are lazy-loaded to avoid SSR issues
4. **Restart required** - Always restart dev server after editing `.env.local`

## Environment Variables Location

The `.env.local` file must be in:
```
apps/web-frontend/.env.local
```

(Same directory as `package.json`)
