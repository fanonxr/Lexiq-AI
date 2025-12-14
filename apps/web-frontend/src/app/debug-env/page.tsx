"use client";

import { useEffect, useState } from "react";

/**
 * Debug page to check if environment variables are loaded
 * 
 * Access at: http://localhost:3000/debug-env
 */
export default function DebugEnvPage() {
  const [mounted, setMounted] = useState(false);
  const [allEnvKeys, setAllEnvKeys] = useState<string[]>([]);
  const [envVars, setEnvVars] = useState<Record<string, string>>({});

  useEffect(() => {
    setMounted(true);
    // Check what's available in process.env
    const keys = Object.keys(process.env).filter(k => k.startsWith("NEXT_PUBLIC_"));
    setAllEnvKeys(keys);
    
    const vars: Record<string, string> = {};
    keys.forEach((key) => {
      vars[key] = process.env[key] || "";
    });
    setEnvVars(vars);
  }, []);

  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <div style={{ padding: "2rem", fontFamily: "monospace" }}>
        <h1>Environment Variables Debug</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "monospace" }}>
      <h1>Environment Variables Debug</h1>
      
      <h2>Status</h2>
      <p>
        <strong>NEXT_PUBLIC_* variables found:</strong> {allEnvKeys.length}
      </p>
      
      {allEnvKeys.length === 0 ? (
        <div style={{ background: "#fee", padding: "1rem", borderRadius: "4px" }}>
          <strong>⚠️ No NEXT_PUBLIC_* variables found!</strong>
          <p>This means Next.js hasn't embedded them. Check:</p>
          <ul>
            <li>Is .env.local in apps/web-frontend/ directory?</li>
            <li>Did you restart the dev server after creating/editing .env.local?</li>
            <li>Are variables prefixed with NEXT_PUBLIC_?</li>
          </ul>
        </div>
      ) : (
        <div style={{ background: "#efe", padding: "1rem", borderRadius: "4px" }}>
          <strong>✅ Environment variables are loaded!</strong>
        </div>
      )}

      <h2>All NEXT_PUBLIC_* Variables</h2>
      {allEnvKeys.length > 0 ? (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr style={{ background: "#f0f0f0" }}>
              <th style={{ padding: "0.5rem", border: "1px solid #ccc", textAlign: "left" }}>Key</th>
              <th style={{ padding: "0.5rem", border: "1px solid #ccc", textAlign: "left" }}>Value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(envVars).map(([key, value]) => (
              <tr key={key}>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>{key}</td>
                <td style={{ padding: "0.5rem", border: "1px solid #ccc" }}>
                  {value || <em style={{ color: "#999" }}>(empty)</em>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#999" }}>No variables found</p>
      )}

      <h2>Required Variables</h2>
      <ul>
        <li>
          NEXT_PUBLIC_ENTRA_ID_TENANT_ID:{" "}
          {envVars.NEXT_PUBLIC_ENTRA_ID_TENANT_ID || (
            <span style={{ color: "red" }}>❌ Missing</span>
          )}
        </li>
        <li>
          NEXT_PUBLIC_ENTRA_ID_CLIENT_ID:{" "}
          {envVars.NEXT_PUBLIC_ENTRA_ID_CLIENT_ID || (
            <span style={{ color: "red" }}>❌ Missing</span>
          )}
        </li>
        <li>
          NEXT_PUBLIC_ENTRA_ID_AUTHORITY:{" "}
          {envVars.NEXT_PUBLIC_ENTRA_ID_AUTHORITY || (
            <span style={{ color: "red" }}>❌ Missing</span>
          )}
        </li>
      </ul>

      <h2>Raw process.env (first 20 keys)</h2>
      <pre style={{ background: "#f5f5f5", padding: "1rem", overflow: "auto" }}>
        {JSON.stringify(
          Object.keys(process.env).slice(0, 20).reduce((acc, key) => {
            acc[key] = process.env[key];
            return acc;
          }, {} as Record<string, string | undefined>),
          null,
          2
        )}
      </pre>
    </div>
  );
}

