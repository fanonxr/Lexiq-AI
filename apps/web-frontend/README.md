# LexiqAI Web Frontend

Next.js 14 application for LexiqAI's marketing site and SaaS dashboard.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4
- **Authentication:** Microsoft Entra ID (Azure AD) with MSAL
- **Fonts:** Geist Sans & Geist Mono

## Project Structure

The application uses Next.js route groups to organize different sections:

```
src/app/
├── layout.tsx              # Root layout (fonts, global styles)
├── (site)/                 # Public marketing site
│   ├── layout.tsx         # Marketing layout (navbar, footer)
│   └── page.tsx           # Landing page
├── (dashboard)/            # Protected SaaS app
│   ├── layout.tsx         # Dashboard layout (sidebar, auth check)
│   ├── dashboard/         # Dashboard home
│   ├── settings/          # User settings
│   └── recordings/        # Call recordings
└── (auth)/                 # Authentication pages
    ├── layout.tsx         # Clean centered auth layout
    ├── login/             # Sign in page
    ├── signup/            # Sign up page
    └── reset-password/    # Password reset page
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Azure AD tenant with App Registration (see [Entra ID Setup Guide](/docs/foundation/entra-id-setup.md))

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   ```bash
   cp env.example .env.local
   ```
   
   Edit `.env.local` and add your Azure AD credentials:
   ```bash
   NEXT_PUBLIC_ENTRA_ID_TENANT_ID=your-tenant-id
   NEXT_PUBLIC_ENTRA_ID_CLIENT_ID=your-client-id
   NEXT_PUBLIC_ENTRA_ID_AUTHORITY=https://login.microsoftonline.com/common
   NEXT_PUBLIC_APP_URL=http://localhost:3000
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Environment Variables

### Client-Side vs Server-Side

- **`NEXT_PUBLIC_*`** - Exposed to browser (safe for public identifiers like CLIENT_ID)
- **No prefix** - Server-only (for secrets, API keys, credentials)

**⚠️ Security Note:** CLIENT_ID and TENANT_ID are safe to be public in OAuth/OIDC flows. They are not secrets. See [`src/lib/env.security.md`](src/lib/env.security.md) for details.

**Quick Setup:**
```bash
cp env.example .env.local
# Edit .env.local with your Azure AD credentials
```

**Required client-side variables:**
- `NEXT_PUBLIC_ENTRA_ID_TENANT_ID` - Azure AD tenant ID (safe to be public)
- `NEXT_PUBLIC_ENTRA_ID_CLIENT_ID` - Azure AD application (client) ID (safe to be public)
- `NEXT_PUBLIC_ENTRA_ID_AUTHORITY` - Azure AD authority URL (default: `https://login.microsoftonline.com/common`)

**Optional client-side variables:**
- `NEXT_PUBLIC_APP_URL` - Application URL (default: `http://localhost:3000`)
- `NEXT_PUBLIC_API_URL` - API Core service URL (default: `http://localhost:8000`)
- `NEXT_PUBLIC_ENABLE_GOOGLE_SIGNIN` - Enable Google sign-in (default: `true`)
- `NEXT_PUBLIC_ENABLE_EMAIL_OTP` - Enable email OTP (default: `true`)

**Server-side variables (no NEXT_PUBLIC_ prefix):**
- `API_SECRET_KEY` - Secret API key (if needed)
- `DATABASE_URL` - Database connection string (if needed)
- `AZURE_CLIENT_SECRET` - Azure client secret (only if using server-side auth)

For detailed documentation, see:
- [`src/lib/env.security.md`](src/lib/env.security.md) - Security best practices
- [`src/lib/env.docs.md`](src/lib/env.docs.md) - Complete environment variables guide
- `env.example` - Example configuration file
- [Entra ID Setup Guide](/docs/foundation/entra-id-setup.md) - Azure AD setup instructions

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Type-Safe Environment Variables

#### Client-Side (Browser)

Use `env` for client-side variables (NEXT_PUBLIC_ prefix):

```typescript
import { env } from '@/lib/env';

// Access Entra ID config
const tenantId = env.entraId.tenantId;
const clientId = env.entraId.clientId;

// Access app URLs
const appUrl = env.app.url;
const apiUrl = env.app.apiUrl;

// Check feature flags
if (env.features.enableGoogleSignIn) {
  // Show Google sign-in button
}
```

#### Server-Side (API Routes, Server Components)

Use `serverEnv` for server-only variables (no NEXT_PUBLIC_ prefix):

```typescript
// ✅ Use in Server Components, API Routes, Server Actions
import { serverEnv } from '@/lib/env.server';

// Access server-only secrets
const apiKey = serverEnv.api.secretKey;
const dbUrl = serverEnv.database?.connectionString;
```

**⚠️ Important:** Never import `serverEnv` in client components. It will throw an error if accessed in the browser.

## Implementation Status

### ✅ Phase 1: Foundation (Complete)
- [x] Dependencies installed
- [x] Environment configuration
- [x] Route groups structure
- [x] Basic layouts

### ✅ Phase 2: Authentication (Complete)
- [x] MSAL configuration
- [x] Authentication context & provider
- [x] Proxy for route protection

### 📋 Phase 3-10: See [Implementation Plan](/docs/frontend/implementation-plan.md)

## Routes

### Public Routes (No Authentication Required)
- `/` - Landing page
- `/login` - Sign in page
- `/signup` - Sign up page
- `/reset-password` - Password reset page

### Protected Routes (Authentication Required)
- `/dashboard` - Dashboard home
- `/settings` - User settings
- `/recordings` - Call recordings

## Documentation

- [Implementation Plan](/docs/frontend/implementation-plan.md) - Complete implementation roadmap
- [System Design](/docs/design/system-design.md) - Overall architecture
- [Entra ID Setup Guide](/docs/foundation/entra-id-setup.md) - Azure AD configuration

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [MSAL.js Documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
