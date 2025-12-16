"use client";

import { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/Label";
import { Alert } from "@/components/ui/Alert";
import { Trash2, Save, Key, User, AlertTriangle } from "lucide-react";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

/**
 * Settings Page
 * 
 * User account settings, profile management, and account termination.
 * Allows users to manage their account information and preferences.
 */
export default function SettingsPage() {
  // Profile state
  const [name, setName] = useState("John Doe");
  const [email, setEmail] = useState("john.doe@example.com");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Account termination state
  const [showTerminateConfirm, setShowTerminateConfirm] = useState(false);
  const [terminateConfirmText, setTerminateConfirmText] = useState("");
  const [isTerminating, setIsTerminating] = useState(false);

  /**
   * Handle profile save
   */
  const handleSaveProfile = useCallback(async () => {
    setIsSavingProfile(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    
    // Mock save - in real implementation, this would call the API
    console.log("Saving profile:", { name, email });
    
    setIsSavingProfile(false);
    setProfileSaved(true);
    
    setTimeout(() => setProfileSaved(false), 3000);
  }, [name, email]);

  /**
   * Handle password change
   */
  const handleChangePassword = useCallback(async () => {
    setPasswordError(null);

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("All fields are required");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    setIsChangingPassword(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    
    // Mock password change - in real implementation, this would call the API
    console.log("Changing password");
    
    setIsChangingPassword(false);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setPasswordError(null);
    
    // Show success message
    alert("Password changed successfully");
  }, [currentPassword, newPassword, confirmPassword]);

  /**
   * Handle account termination
   */
  const handleTerminateAccount = useCallback(async () => {
    if (terminateConfirmText !== "DELETE") {
      setPasswordError("Please type DELETE to confirm");
      return;
    }

    setIsTerminating(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    // Mock account termination - in real implementation, this would call the API
    console.log("Terminating account");
    
    // In real implementation, this would redirect to logout or home page
    alert("Account terminated. You will be logged out.");
    
    setIsTerminating(false);
    setShowTerminateConfirm(false);
    setTerminateConfirmText("");
  }, [terminateConfirmText]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your account settings, preferences, and profile information
        </p>
      </div>

      {/* Profile Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Profile Information</CardTitle>
          </div>
          <CardDescription>
            Update your personal information and account details
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name" required>
              Full Name
            </Label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your full name"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" required>
              Email Address
            </Label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              {profileSaved && (
                <span className="text-sm text-green-600">Profile saved successfully</span>
              )}
            </div>
            <Button
              onClick={handleSaveProfile}
              disabled={isSavingProfile}
              className="gap-2"
            >
              {isSavingProfile ? (
                "Saving..."
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Security Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Security</CardTitle>
          </div>
          <CardDescription>
            Change your password to keep your account secure
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password" required>
              Current Password
            </Label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter your current password"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-password" required>
              New Password
            </Label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Enter your new password"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <p className="text-xs text-muted-foreground">
              Password must be at least 8 characters
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-password" required>
              Confirm New Password
            </Label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your new password"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          {passwordError && (
            <Alert variant="error" title="Error">
              {passwordError}
            </Alert>
          )}

          <div className="pt-2">
            <Button
              onClick={handleChangePassword}
              disabled={isChangingPassword || !currentPassword || !newPassword || !confirmPassword}
              className="gap-2"
            >
              {isChangingPassword ? "Changing Password..." : "Change Password"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-200 dark:border-red-900/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <CardTitle className="text-lg text-red-600">Danger Zone</CardTitle>
          </div>
          <CardDescription>
            Irreversible and destructive actions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-red-200 bg-red-50/50 p-4 dark:border-red-900/50 dark:bg-red-900/10">
            <h4 className="text-sm font-semibold text-red-900 dark:text-red-400 mb-2">
              Terminate Account
            </h4>
            <p className="text-sm text-red-700 dark:text-red-300 mb-4">
              Once you delete your account, there is no going back. Please be certain.
              All your data, appointments, and settings will be permanently deleted.
            </p>

            {!showTerminateConfirm ? (
              <Button
                variant="destructive"
                onClick={() => setShowTerminateConfirm(true)}
                className="gap-2"
              >
                <Trash2 className="h-4 w-4" />
                Terminate Account
              </Button>
            ) : (
              <div className="space-y-4">
                <Alert variant="error" title="Warning">
                  This action cannot be undone. All your data will be permanently deleted.
                </Alert>

                <div className="space-y-2">
                  <Label htmlFor="terminate-confirm">
                    Type <strong>DELETE</strong> to confirm
                  </Label>
                  <input
                    id="terminate-confirm"
                    type="text"
                    value={terminateConfirmText}
                    onChange={(e) => setTerminateConfirmText(e.target.value)}
                    placeholder="Type DELETE to confirm"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <Button
                    variant="destructive"
                    onClick={handleTerminateAccount}
                    disabled={isTerminating || terminateConfirmText !== "DELETE"}
                    className="gap-2"
                  >
                    {isTerminating ? (
                      "Terminating..."
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4" />
                        Permanently Delete Account
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowTerminateConfirm(false);
                      setTerminateConfirmText("");
                      setPasswordError(null);
                    }}
                    disabled={isTerminating}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
