"use client";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Sidebar } from "@/components/layout/Sidebar";
import { UserMenu } from "@/components/layout/UserMenu";
import { useState, useEffect } from "react";
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
    if (pathname.startsWith("/billing")) return "Billing";
    return "Dashboard";
  };

  // Keyboard navigation: Esc to close mobile menu
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle Esc if not typing in an input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if (e.key === "Escape" && mobileMenuOpen) {
        e.preventDefault();
        setMobileMenuOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

  return (
    <ProtectedRoute>
      {/* Skip to main content link for keyboard navigation */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-zinc-900 focus:text-white focus:rounded-md focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        Skip to main content
      </a>

      <div className="fixed inset-0 flex h-screen w-full bg-white text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          mobileOpen={mobileMenuOpen}
          onMobileOpenChange={setMobileMenuOpen}
        />

        {/* Main Content */}
        <main id="main-content" className="flex flex-1 flex-col overflow-hidden md:ml-0" role="main">
          {/* Top Bar */}
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-200 bg-white text-zinc-900 px-4 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100 sm:px-6 lg:px-8" role="banner">
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
          <div className="flex-1 overflow-y-auto bg-white dark:bg-zinc-950">
            <div className="p-4 sm:p-6 lg:p-8">{children}</div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
