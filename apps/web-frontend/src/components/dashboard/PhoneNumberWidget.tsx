"use client";

/**
 * Phone Number Widget Component
 * 
 * Compact widget for displaying phone number status on the dashboard.
 * Shows the phone number if provisioned, or a "Get Phone Number" button if not.
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { Phone, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { 
  provisionFirmPhoneNumber, 
  getFirmPhoneNumber,
  type FirmPhoneNumberResponse 
} from "@/lib/api/firms";
import { useAuthContext } from "@/contexts/AuthContext";
import { fetchUserProfile } from "@/lib/api/users";
import { useRouter } from "next/navigation";
import { logger } from "@/lib/logger";

export function PhoneNumberWidget() {
  const { user } = useAuthContext();
  const router = useRouter();
  const [userProfile, setUserProfile] = useState<any>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [phoneNumber, setPhoneNumber] = useState<FirmPhoneNumberResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProvisioning, setIsProvisioning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch user profile from API to get latest firm_id
  useEffect(() => {
    const loadUserProfile = async () => {
      try {
        setIsLoadingProfile(true);
        const profile = await fetchUserProfile();
        setUserProfile(profile);
      } catch (err) {
        logger.error("Error fetching user profile", err instanceof Error ? err : new Error(String(err)));
        setUserProfile(user);
      } finally {
        setIsLoadingProfile(false);
      }
    };
    
    loadUserProfile();
  }, [user]);
  
  // Use firm_id from API user profile if available
  const effectiveFirmId = userProfile?.firm_id || user?.id || "";

  // Fetch current phone number
  useEffect(() => {
    if (!effectiveFirmId || isLoadingProfile) {
      setIsLoading(!isLoadingProfile);
      return;
    }

    const loadPhoneNumber = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await getFirmPhoneNumber(effectiveFirmId);
        if (response.phone_number) {
          setPhoneNumber(response);
        }
      } catch (err: any) {
        // 404 is expected if no phone number exists yet
        // 403 is authorization error - log it but don't show error
        if (err.status === 403 || err.status === 404) {
          // No phone number - that's fine
        } else {
          setError("Failed to load phone number");
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadPhoneNumber();
  }, [effectiveFirmId, isLoadingProfile]);

  const handleProvision = async () => {
    if (!effectiveFirmId) {
      setError("Firm ID is required");
      return;
    }

    try {
      setIsProvisioning(true);
      setError(null);

      const response = await provisionFirmPhoneNumber(effectiveFirmId);
      setPhoneNumber(response);
      
      // Refresh user profile
      try {
        const updatedProfile = await fetchUserProfile();
        setUserProfile(updatedProfile);
      } catch (err) {
        logger.error("Error refreshing user profile", err instanceof Error ? err : new Error(String(err)));
      }
    } catch (err: any) {
      const errorMessage = err.message || "Failed to provision phone number";
      setError(errorMessage);
      logger.error("Error provisioning phone number", err instanceof Error ? err : new Error(String(err)), {
        effectiveFirmId,
      });
    } finally {
      setIsProvisioning(false);
    }
  };

  const handleViewSettings = () => {
    router.push("/settings");
  };

  if (isLoading || isLoadingProfile) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">Phone Number</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Phone className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium">Phone Number</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}

        {phoneNumber?.phone_number ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                {phoneNumber.formatted_phone_number}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Active and ready to receive calls
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleViewSettings}
              className="w-full"
            >
              Manage in Settings
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              No phone number provisioned yet
            </p>
            <Button
              onClick={handleProvision}
              disabled={isProvisioning || !effectiveFirmId}
              size="sm"
              className="w-full"
            >
              {isProvisioning ? (
                <>
                  <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                  Provisioning...
                </>
              ) : (
                <>
                  <Phone className="mr-2 h-3 w-3" />
                  Get Phone Number
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

