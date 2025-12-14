/**
 * Debug utility to check environment variables
 * Use this in the browser console to debug env var issues
 */

export function debugEnvVars() {
  if (typeof window === "undefined") {
    console.log("This function only works in the browser");
    return;
  }

  console.log("=== Environment Variables Debug ===");
  console.log("NEXT_PUBLIC_ENTRA_ID_TENANT_ID:", process.env.NEXT_PUBLIC_ENTRA_ID_TENANT_ID || "NOT SET");
  console.log("NEXT_PUBLIC_ENTRA_ID_CLIENT_ID:", process.env.NEXT_PUBLIC_ENTRA_ID_CLIENT_ID || "NOT SET");
  console.log("NEXT_PUBLIC_ENTRA_ID_AUTHORITY:", process.env.NEXT_PUBLIC_ENTRA_ID_AUTHORITY || "NOT SET");
  console.log("NEXT_PUBLIC_APP_URL:", process.env.NEXT_PUBLIC_APP_URL || "NOT SET");
  console.log("NEXT_PUBLIC_API_URL:", process.env.NEXT_PUBLIC_API_URL || "NOT SET");
  console.log("===================================");
  
  // Check if .env.local exists (can't actually read it, but we can check if vars are loaded)
  const allVarsSet = 
    process.env.NEXT_PUBLIC_ENTRA_ID_TENANT_ID &&
    process.env.NEXT_PUBLIC_ENTRA_ID_CLIENT_ID;
  
  if (!allVarsSet) {
    console.warn("⚠️ Some required environment variables are missing!");
    console.warn("Make sure:");
    console.warn("1. .env.local exists in apps/web-frontend/ directory");
    console.warn("2. Variables start with NEXT_PUBLIC_ prefix");
    console.warn("3. Dev server was restarted after creating/editing .env.local");
  } else {
    console.log("✅ All required environment variables are set");
  }
}

// Make it available globally in development
if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  (window as any).debugEnvVars = debugEnvVars;
}
