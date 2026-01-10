"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/Alert";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  CreditCard,
  Calendar,
  TrendingUp,
  TrendingDown,
  Download,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { UsageMeter } from "@/components/billing/UsageMeter";
import {
  getSubscription,
  getUsage,
  getInvoices,
  fetchPlans,
  upgradeSubscription,
  cancelSubscription,
  type Subscription,
  type UsageSummary,
  type Invoice,
  type Plan,
} from "@/lib/api/billing";
import { logger } from "@/lib/logger";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

/**
 * Billing Dashboard Page
 * 
 * Displays subscription status, usage statistics, invoice history,
 * and plan management options.
 */
export default function BillingPage() {
  const router = useRouter();

  // State
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [isCanceling, setIsCanceling] = useState(false);

  // Load data on mount
  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load subscription, usage, invoices, and plans in parallel
      const [subData, usageData, invoicesData, plansData] = await Promise.all([
        getSubscription().catch(() => null), // Subscription is optional
        getUsage().catch(() => null), // Usage is optional
        getInvoices(0, 10).catch(() => ({ invoices: [], total: 0, skip: 0, limit: 10 })),
        fetchPlans().catch(() => []),
      ]);

      setSubscription(subData);
      setUsage(usageData);
      setInvoices(invoicesData.invoices || []);
      setPlans(plansData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load billing data";
      setError(errorMessage);
      logger.error("Error loading billing data", err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  };

  // Handle plan upgrade
  const handleUpgrade = async (newPlanId: string) => {
    if (!subscription) return;

    try {
      setIsUpgrading(true);
      const updated = await upgradeSubscription(subscription.id, newPlanId);
      setSubscription(updated);
      // Reload to get updated usage
      await loadBillingData();
    } catch (err) {
      logger.error("Error upgrading subscription", err instanceof Error ? err : new Error(String(err)));
      alert("Failed to upgrade subscription. Please try again.");
    } finally {
      setIsUpgrading(false);
    }
  };

  // Handle subscription cancellation
  const handleCancel = async () => {
    if (!subscription) return;

    if (!confirm("Are you sure you want to cancel your subscription? It will remain active until the end of the current billing period.")) {
      return;
    }

    try {
      setIsCanceling(true);
      const updated = await cancelSubscription(subscription.id, true);
      setSubscription(updated);
      // Reload billing data to ensure everything is up to date
      await loadBillingData();
    } catch (err) {
      logger.error("Error canceling subscription", err instanceof Error ? err : new Error(String(err)));
      alert("Failed to cancel subscription. Please try again.");
    } finally {
      setIsCanceling(false);
    }
  };

  // Calculate usage stats from usage data
  const usageStats = usage ? {
    callMinutes: usage.features?.call_minutes || usage.features?.calls || 0,
    storage: usage.features?.storage || 0,
    apiRequests: usage.features?.api_requests || 0,
  } : null;

  // Get plan details
  // Prefer new columns (includedMinutes, overageRatePerMinute) over features_json
  const currentPlan = subscription?.plan;
  let includedMinutes = 0;
  let overageRate = 0;
  
  // Use new columns if available
  if (currentPlan?.includedMinutes !== undefined && currentPlan.includedMinutes !== null) {
    includedMinutes = currentPlan.includedMinutes;
  }
  if (currentPlan?.overageRatePerMinute !== undefined && currentPlan.overageRatePerMinute !== null) {
    overageRate = currentPlan.overageRatePerMinute;
  }
  
  // Fallback to features_json if columns are not available
  if ((includedMinutes === 0 && overageRate === 0) && currentPlan?.features) {
    // Handle both object and string JSON
    const features = typeof currentPlan.features === 'string' 
      ? JSON.parse(currentPlan.features) 
      : currentPlan.features;
    if (includedMinutes === 0) {
      includedMinutes = features?.included_minutes || 0;
    }
    if (overageRate === 0) {
      overageRate = features?.overage_rate_per_minute || 0;
    }
  }
  
  const callMinutes = usageStats?.callMinutes || 0;

  // Calculate days until renewal
  const daysUntilRenewal = subscription?.currentPeriodEnd
    ? Math.ceil((new Date(subscription.currentPeriodEnd).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;

  // Define plan tier order (lower number = lower tier)
  const getPlanTier = (planName: string): number => {
    const tierMap: Record<string, number> = {
      starter: 1,
      professional: 2,
      enterprise: 3,
    };
    return tierMap[planName.toLowerCase()] || 999;
  };

  // Get available upgrade plans (higher tier than current)
  const currentPlanTier = currentPlan?.name ? getPlanTier(currentPlan.name) : 0;
  const availableUpgradePlans = plans.filter(
    (plan) =>
      plan.id !== subscription?.planId &&
      plan.isPublic &&
      plan.isActive &&
      getPlanTier(plan.name) > currentPlanTier
  );
  
  // Sort by tier (ascending)
  availableUpgradePlans.sort((a, b) => getPlanTier(a.name) - getPlanTier(b.name));

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        error={new Error(error)}
        onRetry={loadBillingData}
        title="Failed to load billing information"
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Billing & Subscription
        </h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
          Manage your subscription, view usage, and access invoices
        </p>
      </div>

      {/* Subscription Status */}
      {subscription ? (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Current Subscription</CardTitle>
                <CardDescription>
                  {currentPlan?.displayName || "No plan"} • {subscription.billingCycle}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {subscription.status === "trialing" && (
                  <span className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400">
                    <Calendar className="h-4 w-4" />
                    Free Trial
                  </span>
                )}
                {subscription.status === "active" && !subscription.cancelAtPeriodEnd && (
                  <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Active
                  </span>
                )}
                {subscription.status === "active" && subscription.cancelAtPeriodEnd && (
                  <span className="flex items-center gap-1 text-sm text-amber-600 dark:text-amber-400">
                    <AlertCircle className="h-4 w-4" />
                    Cancels {daysUntilRenewal !== null ? `in ${daysUntilRenewal} days` : "at period end"}
                  </span>
                )}
                {subscription.status === "past_due" && (
                  <span className="flex items-center gap-1 text-sm text-red-600 dark:text-red-400">
                    <AlertCircle className="h-4 w-4" />
                    Past Due
                  </span>
                )}
                {subscription.status === "canceled" && (
                  <span className="flex items-center gap-1 text-sm text-red-600 dark:text-red-400">
                    <AlertCircle className="h-4 w-4" />
                    Canceled
                  </span>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Trial Period Info */}
            {subscription.status === "trialing" && subscription.trialEnd && (
              <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  <h3 className="font-semibold text-blue-900 dark:text-blue-100">Free Trial Active</h3>
                </div>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Your trial ends on {format(new Date(subscription.trialEnd), "MMM d, yyyy")}. 
                  {(() => {
                    const trialEndDate = new Date(subscription.trialEnd);
                    const daysRemaining = Math.ceil((trialEndDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                    return daysRemaining > 0 ? ` ${daysRemaining} ${daysRemaining === 1 ? "day" : "days"} remaining.` : " Trial ending soon.";
                  })()}
                </p>
              </div>
            )}

            {/* Billing Period */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-zinc-500 dark:text-zinc-500">
                  {subscription.status === "trialing" ? "Trial Period" : "Current Period"}
                </div>
                <div className="font-medium text-zinc-900 dark:text-zinc-100">
                  {subscription.currentPeriodStart
                    ? format(new Date(subscription.currentPeriodStart), "MMM d, yyyy")
                    : "N/A"}{" "}
                  -{" "}
                  {subscription.currentPeriodEnd
                    ? format(new Date(subscription.currentPeriodEnd), "MMM d, yyyy")
                    : "N/A"}
                </div>
              </div>
              {subscription.status === "trialing" && subscription.trialEnd ? (
                <div>
                  <div className="text-zinc-500 dark:text-zinc-500">Trial Ends</div>
                  <div className="font-medium text-zinc-900 dark:text-zinc-100">
                    {format(new Date(subscription.trialEnd), "MMM d, yyyy")}
                  </div>
                </div>
              ) : daysUntilRenewal !== null ? (
                <div>
                  <div className="text-zinc-500 dark:text-zinc-500">Renews In</div>
                  <div className="font-medium text-zinc-900 dark:text-zinc-100">
                    {daysUntilRenewal} {daysUntilRenewal === 1 ? "day" : "days"}
                  </div>
                </div>
              ) : null}
            </div>

            {/* Usage Meter */}
            {includedMinutes > 0 && (
              <div>
                <UsageMeter
                  current={callMinutes}
                  limit={includedMinutes}
                  overageRate={overageRate}
                  unit="minutes"
                />
              </div>
            )}

            {/* Plan Actions */}
            <div className="flex gap-2 pt-4 border-t border-zinc-200 dark:border-zinc-800">
              {!subscription.cancelAtPeriodEnd && (
                <Button
                  onClick={handleCancel}
                  variant="outline"
                  disabled={isCanceling}
                >
                  {isCanceling ? "Canceling..." : "Cancel Subscription"}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              title="No Active Subscription"
              description="Subscribe to a plan to get started with LexiqAI"
              action={
                <Button onClick={() => router.push("/pricing")}>
                  View Plans
                </Button>
              }
            />
          </CardContent>
        </Card>
      )}

      {/* Upgrade Plans Section */}
      {subscription && availableUpgradePlans.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upgrade Your Plan</CardTitle>
            <CardDescription>
              Unlock more features and higher limits with an upgrade
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {availableUpgradePlans.map((plan) => {
                const isEnterprise = plan.name.toLowerCase() === "enterprise";
                const planPrice = plan.priceMonthly
                  ? `$${parseFloat(plan.priceMonthly.toString()).toFixed(0)}/month`
                  : "Custom Pricing";
                
                return (
                  <div
                    key={plan.id}
                    className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-4 space-y-3"
                  >
                    <div>
                      <h3 className="font-semibold text-lg text-zinc-900 dark:text-zinc-100">
                        {plan.displayName}
                      </h3>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">
                        {plan.description}
                      </p>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                        {planPrice}
                      </span>
                    </div>
                    {plan.includedMinutes && (
                      <div className="text-sm text-zinc-600 dark:text-zinc-400">
                        {plan.includedMinutes.toLocaleString()} minutes included
                      </div>
                    )}
                    <Button
                      onClick={() => {
                        if (isEnterprise) {
                          // Enterprise requires custom pricing - redirect to contact
                          router.push("/contact");
                        } else {
                          // Use upgrade API for standard plans
                          handleUpgrade(plan.id);
                        }
                      }}
                      className="w-full"
                      disabled={isUpgrading}
                    >
                      <TrendingUp className="h-4 w-4 mr-2" />
                      {isUpgrading ? "Upgrading..." : `Upgrade to ${plan.displayName}`}
                    </Button>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Usage Statistics */}
      {usageStats && (
        <Card>
          <CardHeader>
            <CardTitle>Usage Statistics</CardTitle>
            <CardDescription>
              Current billing period usage
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500">Call Minutes</div>
                <div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                  {callMinutes.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500">Storage</div>
                <div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                  {(usageStats.storage / 1024).toFixed(2)} GB
                </div>
              </div>
              <div>
                <div className="text-sm text-zinc-500 dark:text-zinc-500">API Requests</div>
                <div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                  {usageStats.apiRequests.toLocaleString()}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Invoice History */}
      <Card>
        <CardHeader>
          <CardTitle>Invoice History</CardTitle>
          <CardDescription>
            View and download your past invoices
          </CardDescription>
        </CardHeader>
        <CardContent>
          {invoices.length > 0 ? (
            <div className="space-y-3">
              {invoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between p-4 border border-zinc-200 dark:border-zinc-800 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="font-medium text-zinc-900 dark:text-zinc-100">
                      {invoice.invoiceNumber}
                    </div>
                    <div className="text-sm text-zinc-500 dark:text-zinc-500">
                      {format(new Date(invoice.dueDate), "MMM d, yyyy")} •{" "}
                      {invoice.status === "paid" ? (
                        <span className="text-green-600 dark:text-green-400">Paid</span>
                      ) : invoice.status === "open" ? (
                        <span className="text-amber-600 dark:text-amber-400">Pending</span>
                      ) : (
                        <span className="text-zinc-500 dark:text-zinc-500">{invoice.status}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-semibold text-zinc-900 dark:text-zinc-100">
                        ${parseFloat(invoice.amount.toString()).toFixed(2)}
                      </div>
                      <div className="text-xs text-zinc-500 dark:text-zinc-500">
                        {invoice.currency.toUpperCase()}
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No Invoices"
              description="Your invoices will appear here once you have an active subscription"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
