"use client";

/**
 * Navbar Component
 * 
 * Marketing site navigation bar with responsive menu.
 * 
 * @example
 * ```tsx
 * <Navbar />
 * ```
 */

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

export interface NavbarProps {
  /**
   * Whether to show authentication buttons
   * @default true
   */
  showAuth?: boolean;
}

/**
 * Marketing site navbar
 */
export function Navbar({ showAuth = true }: NavbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { isAuthenticated } = useAuth();

  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/pricing", label: "Pricing" },
  ];

  return (
    <nav
      className="sticky top-0 z-50 w-full border-b border-zinc-800 bg-black backdrop-blur supports-[backdrop-filter]:bg-black/95 dark:border-zinc-700 dark:bg-black dark:supports-[backdrop-filter]:bg-black/95"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center">
            <Link
              href="/"
              className="flex items-center space-x-2 text-xl font-bold text-white"
              aria-label="LexiqAI Home"
            >
              <span>LexiqAI</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:space-x-6">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-base font-semibold text-zinc-200 transition-colors hover:text-white"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Auth Buttons / User Menu */}
          <div className="hidden md:flex md:items-center md:space-x-4">
            {showAuth && (
              <>
                {isAuthenticated ? (
                    <Link href="/dashboard">
                      <Button size="sm" className="bg-white text-zinc-900 hover:bg-zinc-100">
                        Dashboard
                      </Button>
                    </Link>
                  ) : (
                    <>
                      <Link href="/login">
                        <Button variant="ghost" size="sm" className="text-zinc-200 hover:text-white hover:bg-zinc-800">
                          Sign In
                        </Button>
                      </Link>
                      <Link href="/signup">
                        <Button size="sm" className="bg-white text-zinc-900 hover:bg-zinc-100">
                          Get Started
                        </Button>
                      </Link>
                    </>
                  )}
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            type="button"
            className="md:hidden rounded-md p-2 text-zinc-200 hover:bg-zinc-800 hover:text-white"
            aria-label="Toggle menu"
            aria-expanded={isMenuOpen}
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2"
            >
              {isMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-zinc-800 py-4">
            <div className="flex flex-col space-y-4">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-base font-semibold text-zinc-200 hover:text-white"
                  onClick={() => setIsMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              {showAuth && (
                <div className="flex flex-col space-y-2 pt-4">
                  {isAuthenticated ? (
                    <Link href="/dashboard" onClick={() => setIsMenuOpen(false)}>
                      <Button size="sm" className="w-full bg-white text-zinc-900 hover:bg-zinc-100">
                        Dashboard
                      </Button>
                    </Link>
                  ) : (
                    <>
                      <Link href="/login" onClick={() => setIsMenuOpen(false)}>
                        <Button variant="ghost" size="sm" className="w-full text-zinc-200 hover:text-white hover:bg-zinc-800">
                          Sign In
                        </Button>
                      </Link>
                      <Link href="/signup" onClick={() => setIsMenuOpen(false)}>
                        <Button size="sm" className="w-full bg-white text-zinc-900 hover:bg-zinc-100">
                          Get Started
                        </Button>
                      </Link>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
