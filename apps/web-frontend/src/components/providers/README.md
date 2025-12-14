# Authentication Provider

The `AuthProvider` component wraps your application and provides authentication state and methods to all child components.

## Setup

The `AuthProvider` is already added to the root layout (`src/app/layout.tsx`). It wraps the entire application, making authentication available everywhere.

## Usage

### Basic Example

```tsx
"use client";

import { useAuth } from "@/hooks/useAuth";

export default function MyComponent() {
  const { isAuthenticated, user, login, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <div>
        <p>Please sign in</p>
        <button onClick={login}>Sign In</button>
      </div>
    );
  }

  return (
    <div>
      <p>Welcome, {user?.name}!</p>
      <p>Email: {user?.email}</p>
      <button onClick={logout}>Sign Out</button>
    </div>
  );
}
```

### With Loading State

```tsx
"use client";

import { useAuth } from "@/hooks/useAuth";

export default function MyComponent() {
  const { isLoading, isAuthenticated, user } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <div>Not authenticated</div>;
  }

  return <div>Welcome, {user?.name}!</div>;
}
```

### With Error Handling

```tsx
"use client";

import { useAuth } from "@/hooks/useAuth";

export default function MyComponent() {
  const { error, clearError, login } = useAuth();

  return (
    <div>
      {error && (
        <div>
          <p>Error: {error.message}</p>
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}
      <button onClick={login}>Sign In</button>
    </div>
  );
}
```

### Getting Access Tokens

```tsx
"use client";

import { useAuth } from "@/hooks/useAuth";
import { useEffect, useState } from "react";

export default function MyComponent() {
  const { getAccessToken, isAuthenticated } = useAuth();
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      getAccessToken(["User.Read"]).then(setToken);
    }
  }, [isAuthenticated, getAccessToken]);

  if (!token) {
    return <div>Loading token...</div>;
  }

  return <div>Token acquired: {token.substring(0, 20)}...</div>;
}
```

## API Reference

See `useAuth` hook documentation for complete API reference.

## Features

- ✅ Automatic authentication state management
- ✅ User profile extraction from MSAL account
- ✅ Loading states during authentication
- ✅ Error handling and recovery
- ✅ Token acquisition (silent and interactive)
- ✅ Login/logout methods (popup and redirect)
- ✅ Authentication state refresh
