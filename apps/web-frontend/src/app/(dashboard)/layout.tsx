"use client";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Sidebar } from "@/components/layout/Sidebar";
import { UserMenu } from "@/components/layout/UserMenu";
import { useState } from "react";
import { usePathname } from "next/navigation";

/**
 * Dashboard layout - Protected routes
 * Includes sidebar navigation and user menu
 * All routes under this layout require authentication
 */
export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  // Get page title based on current route
  const getPageTitle = () => {
    if (pathname === "/dashboard") return "Dashboard";
    if (pathname.startsWith("/recordings")) return "Recordings";
    if (pathname.startsWith("/settings")) return "Settings";
    return "Dashboard";
  };

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen bg-zinc-50 dark:bg-zinc-950">
        {/* Sidebar */}
        <Sidebar
          mobileOpen={mobileMenuOpen}
          onMobileOpenChange={setMobileMenuOpen}
        />

        {/* Main Content */}
        <main className="flex flex-1 flex-col overflow-hidden md:ml-0">
          {/* Top Bar */}
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900 sm:px-6 lg:px-8">
            <div className="flex flex-1 items-center">
              {/* Mobile: Add spacing for menu button */}
              <div className="md:hidden w-12" />
              <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 md:text-xl">
                {getPageTitle()}
              </h1>
            </div>

            {/* User Menu */}
            <div className="flex items-center">
              <UserMenu />
            </div>
          </header>

          {/* Page Content */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4 sm:p-6 lg:p-8">{children}</div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
