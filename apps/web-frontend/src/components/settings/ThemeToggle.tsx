"use client";

/**
 * Theme Toggle Component
 * 
 * Allows users to switch between light, dark, and system theme preferences.
 * Used in the settings page.
 * 
 * @example
 * ```tsx
 * <ThemeToggle />
 * ```
 */

import { useTheme } from "@/contexts/ThemeContext";
import { Label } from "@/components/ui/Label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Moon, Sun, Monitor } from "lucide-react";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const themes: Array<{ value: "light" | "dark" | "system"; label: string; icon: React.ReactNode; description: string }> = [
    {
      value: "light",
      label: "Light",
      icon: <Sun className="h-5 w-5" />,
      description: "Always use light mode",
    },
    {
      value: "dark",
      label: "Dark",
      icon: <Moon className="h-5 w-5" />,
      description: "Always use dark mode",
    },
    {
      value: "system",
      label: "System",
      icon: <Monitor className="h-5 w-5" />,
      description: "Follow system preference",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Monitor className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg">Appearance</CardTitle>
        </div>
        <CardDescription>
          Choose how LexiqAI looks to you. You can choose between light mode, dark mode, or match your system settings.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Label className="text-base font-medium">Theme</Label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {themes.map((themeOption) => (
              <button
                key={themeOption.value}
                type="button"
                onClick={() => setTheme(themeOption.value)}
                className={cn(
                  "relative flex flex-col items-start gap-2 rounded-lg border-2 p-4 text-left transition-all",
                  "hover:border-zinc-400 dark:hover:border-zinc-600",
                  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  theme === themeOption.value
                    ? "border-zinc-900 bg-zinc-50 dark:border-zinc-100 dark:bg-zinc-800"
                    : "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900"
                )}
                aria-pressed={theme === themeOption.value}
                role="radio"
                aria-label={`Select ${themeOption.label} theme`}
              >
                <div className="flex items-center gap-2">
                  <div
                    className={cn(
                      "text-zinc-600 dark:text-zinc-400",
                      theme === themeOption.value && "text-zinc-900 dark:text-zinc-100"
                    )}
                  >
                    {themeOption.icon}
                  </div>
                  <span
                    className={cn(
                      "text-sm font-medium text-zinc-700 dark:text-zinc-300",
                      theme === themeOption.value && "text-zinc-900 dark:text-zinc-100"
                    )}
                  >
                    {themeOption.label}
                  </span>
                </div>
                <p
                  className={cn(
                    "text-xs text-zinc-500 dark:text-zinc-400",
                    theme === themeOption.value && "text-zinc-600 dark:text-zinc-300"
                  )}
                >
                  {themeOption.description}
                </p>
                {theme === themeOption.value && (
                  <div className="absolute right-2 top-2">
                    <div className="h-2 w-2 rounded-full bg-zinc-900 dark:bg-zinc-100" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

