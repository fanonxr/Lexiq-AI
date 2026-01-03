"use client";

/**
 * Firm Phone Number Settings Component
 * 
 * Component for managing firm phone number provisioning.
 * Allows users to provision a new Twilio phone number for their firm.
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/Label";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Phone, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { 
  provisionFirmPhoneNumber, 
  getFirmPhoneNumber,
  type FirmPhoneNumberResponse 
} from "@/lib/api/firms";
import { useAuthContext } from "@/contexts/AuthContext";
import { fetchUserProfile } from "@/lib/api/users";
import { logger } from "@/lib/logger";

interface FirmPhoneNumberSettingsProps {
  firmId?: string; // Optional - defaults to user ID
}

export function FirmPhoneNumberSettings({ firmId }: FirmPhoneNumberSettingsProps) {
  const { user } = useAuthContext();
  const [userProfile, setUserProfile] = useState<any>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  
  // Fetch user profile from API to get latest firm_id
  useEffect(() => {
    const loadUserProfile = async () => {
      try {
        setIsLoadingProfile(true);
        const profile = await fetchUserProfile();
        setUserProfile(profile);
        logger.debug("Fetched user profile from API", { userId: profile?.id, firmId: profile?.firm_id });
      } catch (err) {
        logger.error("Error fetching user profile", err instanceof Error ? err : new Error(String(err)));
        // Fall back to user from context if API fails
        setUserProfile(user);
      } finally {
        setIsLoadingProfile(false);
      }
    };
    
    loadUserProfile();
  }, [user]);
  
  // Use firm_id from API user profile if available, otherwise fall back to user.id
  const effectiveFirmId = firmId || userProfile?.firm_id || user?.id || "";
  
  // Debug logging
  useEffect(() => {
    logger.debug("User profile", {
      userId: user?.id,
      apiFirmId: userProfile?.firm_id,
      contextFirmId: (user as any)?.firm_id,
      effectiveFirmId,
    });
  }, [user, userProfile, effectiveFirmId]);
  
  const [phoneNumber, setPhoneNumber] = useState<FirmPhoneNumberResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProvisioning, setIsProvisioning] = useState(false);
  const [areaCode, setAreaCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Fetch current phone number
  useEffect(() => {
    if (!effectiveFirmId || isLoadingProfile) {
      setIsLoading(!isLoadingProfile); // Only set loading to false if profile is loaded
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
        // 403 is authorization error - log it but don't show error (user might not have firm_id yet)
        if (err.status === 403) {
          logger.warn("Authorization error loading phone number", {
            error: err.message,
            firmId: effectiveFirmId,
            userId: user?.id,
            apiFirmId: userProfile?.firm_id,
            contextFirmId: (user as any)?.firm_id,
          });
          // Don't set error - just don't show phone number
          // The user can still try to provision one
        } else if (err.status !== 404) {
          setError(err.message || "Failed to load phone number");
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

    // Debug logging
    logger.debug("Provisioning phone number", {
      effectiveFirmId,
      firmIdType: typeof effectiveFirmId,
      firmIdLength: effectiveFirmId.length,
      userFirmId: (user as any)?.firm_id,
      userId: user?.id,
      areaCode,
    });

    try {
      setIsProvisioning(true);
      setError(null);
      setSuccess(null);

      const request = areaCode ? { area_code: areaCode } : undefined;
      const response = await provisionFirmPhoneNumber(effectiveFirmId, request);
      
      setPhoneNumber(response);
      setSuccess(`Phone number ${response.formatted_phone_number} has been provisioned successfully!`);
      setAreaCode(""); // Clear area code input
      
      // Refresh user profile to get updated firm_id
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
        areaCode,
      });
    } finally {
      setIsProvisioning(false);
    }
  };

  if (isLoading || isLoadingProfile) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Phone Number</CardTitle>
          <CardDescription>Loading phone number information...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Phone className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-lg">Phone Number</CardTitle>
        </div>
        <CardDescription>
          Manage your firm's phone number for receiving calls. We'll set up a phone number for you instantly.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <Alert variant="error">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </Alert>
        )}

        {success && (
          <Alert className="bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200">
            <CheckCircle2 className="h-4 w-4" />
            <span>{success}</span>
          </Alert>
        )}

        {phoneNumber?.phone_number ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Current Phone Number</Label>
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span className="text-lg font-semibold">
                  {phoneNumber.formatted_phone_number}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                This number is active and ready to receive calls.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="area-code">Preferred Area Code (Optional)</Label>
              <Input
                id="area-code"
                type="text"
                placeholder="415"
                value={areaCode}
                onChange={(e) => {
                  // Only allow 3 digits
                  const value = e.target.value.replace(/\D/g, "").slice(0, 3);
                  setAreaCode(value);
                }}
                maxLength={3}
                disabled={isProvisioning}
              />
              <p className="text-sm text-muted-foreground">
                Enter a 3-digit area code (e.g., 415, 212) to get a number in that area. 
                Leave blank to get any available number.
              </p>
            </div>

            <Button
              onClick={handleProvision}
              disabled={isProvisioning || !effectiveFirmId}
              className="w-full"
            >
              {isProvisioning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Provisioning...
                </>
              ) : (
                <>
                  <Phone className="mr-2 h-4 w-4" />
                  Get Phone Number
                </>
              )}
            </Button>

            <p className="text-sm text-muted-foreground">
              Click "Get Phone Number" to instantly provision a new phone number for your firm. 
              This number will be used for incoming calls.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

