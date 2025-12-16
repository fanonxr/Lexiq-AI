"use client";

import * as React from "react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/Label";
import { Phone, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Test Playground Component
 * 
 * Sticky panel for testing agent configuration. Styled like a phone dialer
 * or chat interface with phone number input and "Call Me Now" button.
 * 
 * @example
 * ```tsx
 * <TestPlayground
 *   onTestCall={(phoneNumber) => initiateTestCall(phoneNumber)}
 *   isCalling={isCalling}
 * />
 * ```
 */

export interface TestPlaygroundProps {
  /**
   * Callback when test call is initiated
   */
  onTestCall: (phoneNumber: string) => void;
  /**
   * Whether a test call is currently in progress
   * @default false
   */
  isCalling?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Basic phone number validation
 */
function isValidPhoneNumber(phone: string): boolean {
  // Remove common formatting characters
  const cleaned = phone.replace(/[\s\-\(\)]/g, "");
  // Check if it's a valid format (at least 10 digits)
  return /^\+?[\d]{10,}$/.test(cleaned);
}

/**
 * Test Playground Component
 * 
 * Features:
 * - Sticky panel (right side)
 * - Phone dialer/chat interface style
 * - Input: "Enter your phone number"
 * - Large button: "Call Me Now" with Phone icon
 * - Loading state during test call
 */
export function TestPlayground({
  onTestCall,
  isCalling = false,
  className,
}: TestPlaygroundProps) {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!phoneNumber.trim()) {
      setError("Please enter a phone number");
      return;
    }

    if (!isValidPhoneNumber(phoneNumber)) {
      setError("Please enter a valid phone number");
      return;
    }

    setError(null);
    onTestCall(phoneNumber);
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setPhoneNumber(value);
    // Clear error when user starts typing
    if (error) {
      setError(null);
    }
  };

  return (
    <Card
      className={cn(
        "sticky top-4",
        className
      )}
    >
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Test Playground</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Phone Number Input */}
          <div className="space-y-2">
            <Label htmlFor="test-phone-number">Phone Number</Label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                id="test-phone-number"
                type="tel"
                placeholder="Enter your phone number"
                value={phoneNumber}
                onChange={handlePhoneChange}
                disabled={isCalling}
                className={cn(
                  "w-full pl-10 pr-3 py-2 rounded-md border",
                  "bg-background text-foreground",
                  "border-border",
                  "placeholder:text-muted-foreground",
                  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  error && "border-destructive focus:ring-destructive"
                )}
                aria-label="Phone number for test call"
                aria-invalid={error ? "true" : "false"}
                aria-describedby={error ? "phone-error" : "phone-helper"}
              />
            </div>
            {error ? (
              <p id="phone-error" className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : (
              <p id="phone-helper" className="text-xs text-muted-foreground">
                We'll call this number to test your agent configuration
              </p>
            )}
          </div>

          {/* Call Me Now Button */}
          <Button
            type="submit"
            variant="default"
            size="lg"
            className="w-full gap-2"
            disabled={isCalling || !phoneNumber.trim()}
            aria-label="Initiate test call"
          >
            {isCalling ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Calling...
              </>
            ) : (
              <>
                <Phone className="h-5 w-5" />
                Call Me Now
              </>
            )}
          </Button>

          {/* Status Message */}
          {isCalling && (
            <p className="text-center text-sm text-muted-foreground">
              Initiating test call...
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}

