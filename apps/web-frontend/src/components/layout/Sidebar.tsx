"use client";

/**
 * Sidebar Component
 * 
 * Dashboard sidebar navigation with collapsible menu.
 * 
 * @example
 * ```tsx
 * <Sidebar />
 * ```
 */

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Mic, Settings, Menu, X, Bot, BookOpen, Calendar } from "lucide-react";
import { clsx } from "clsx";

export interface SidebarItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
  badge?: string | number;
}

export interface SidebarProps {
  /**
   * Navigation items
   */
  items?: SidebarItem[];
  /**
   * Whether the sidebar is collapsed (desktop)
   */
  collapsed?: boolean;
  /**
   * Callback when collapse state changes
   */
  onCollapseChange?: (collapsed: boolean) => void;
  /**
   * Whether the sidebar is open on mobile
   */
  mobileOpen?: boolean;
  /**
   * Callback when mobile open state changes
   */
  onMobileOpenChange?: (open: boolean) => void;
}

const defaultItems: SidebarItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: <LayoutDashboard className="h-5 w-5" /> },
  { label: "Recordings", href: "/recordings", icon: <Mic className="h-5 w-5" /> },
  { label: "Agent", href: "/agent", icon: <Bot className="h-5 w-5" /> },
  { label: "Knowledge Base", href: "/knowledge", icon: <BookOpen className="h-5 w-5" /> },
  { label: "Appointments", href: "/appointments", icon: <Calendar className="h-5 w-5" /> },
];

/**
 * Dashboard sidebar navigation
 */
export function Sidebar({
  items = defaultItems,
  collapsed: controlledCollapsed,
  onCollapseChange,
  mobileOpen: controlledMobileOpen,
  onMobileOpenChange,
}: SidebarProps) {
  const pathname = usePathname();
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const [internalMobileOpen, setInternalMobileOpen] = useState(false);
  const isCollapsed = controlledCollapsed ?? internalCollapsed;
  const isMobileOpen = controlledMobileOpen ?? internalMobileOpen;

  const handleCollapse = () => {
    const newCollapsed = !isCollapsed;
    if (onCollapseChange) {
      onCollapseChange(newCollapsed);
    } else {
      setInternalCollapsed(newCollapsed);
    }
  };

  const handleMobileToggle = () => {
    const newOpen = !isMobileOpen;
    if (onMobileOpenChange) {
      onMobileOpenChange(newOpen);
    } else {
      setInternalMobileOpen(newOpen);
    }
  };

  const handleLinkClick = () => {
    // Close mobile menu when link is clicked
    if (isMobileOpen) {
      if (onMobileOpenChange) {
        onMobileOpenChange(false);
      } else {
        setInternalMobileOpen(false);
      }
    }
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        type="button"
        onClick={handleMobileToggle}
        className="fixed left-4 top-4 z-50 rounded-md p-2 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100 md:hidden"
        aria-label="Toggle menu"
        aria-expanded={isMobileOpen}
      >
        {isMobileOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <Menu className="h-6 w-6" />
        )}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={handleMobileToggle}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-zinc-200 bg-white text-zinc-900 transition-all duration-300 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100 md:relative md:h-full md:z-auto",
          // Mobile: slide in/out
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          // Desktop: width based on collapsed state
          isCollapsed ? "w-16" : "w-64"
        )}
        role="navigation"
        aria-label="Dashboard navigation"
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
          {!isCollapsed && (
            <Link
              href="/dashboard"
              className="text-lg font-bold text-zinc-900 dark:text-zinc-100"
            >
              LexiqAI
            </Link>
          )}
          <button
            type="button"
            onClick={handleCollapse}
            className="hidden rounded-md p-1.5 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100 md:block"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <Menu className="h-5 w-5" />
            ) : (
              <X className="h-5 w-5" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
          {items.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={handleLinkClick}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                    : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100",
                  isCollapsed && "justify-center"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                {item.icon && (
                  <span className="flex-shrink-0" aria-hidden="true">
                    {item.icon}
                  </span>
                )}
                {!isCollapsed && (
                  <>
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto rounded-full bg-zinc-200 px-2 py-0.5 text-xs font-medium text-zinc-900 dark:bg-zinc-700 dark:text-zinc-100">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
