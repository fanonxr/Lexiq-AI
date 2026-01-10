"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import Link from "next/link";
import { fetchPlans, createCheckoutSession, type Plan } from "@/lib/api/billing";
import { logger } from "@/lib/logger";
import { useAuth } from "@/hooks/useAuth";

interface PricingFeature {
  text: string;
  included: boolean;
}

interface PricingTier {
  name: string;
  description: string;
  price: string;
  priceNote?: string;
  includedMinutes: string;
  overageRate: string;
  features: PricingFeature[];
  cta: string;
  popular?: boolean;
}

const pricingTiers: PricingTier[] = [
  {
    name: "Starter",
    description: "Perfect for small law firms getting started",
    price: "$149",
    priceNote: "per month",
    includedMinutes: "500",
    overageRate: "$0.18/min",
    features: [
      { text: "500 minutes of AI call handling included", included: true },
      { text: "Unlimited call recordings", included: true },
      { text: "Auto-transcription for all calls", included: true },
      { text: "Calendar sync (Outlook, Google Calendar)", included: true },
      { text: "Basic analytics dashboard", included: true },
      { text: "Email support", included: true },
      { text: "Custom voice selection", included: false },
      { text: "Advanced AI scripting", included: false },
      { text: "Priority support", included: false },
      { text: "Dedicated account manager", included: false },
    ],
    cta: "Start Free Trial",
    popular: false,
  },
  {
    name: "Professional",
    description: "For growing law firms with higher call volumes",
    price: "$399",
    priceNote: "per month",
    includedMinutes: "2,000",
    overageRate: "$0.15/min",
    features: [
      { text: "2,000 minutes of AI call handling included", included: true },
      { text: "Unlimited call recordings", included: true },
      { text: "Auto-transcription for all calls", included: true },
      { text: "Calendar sync (Outlook, Google Calendar)", included: true },
      { text: "Advanced analytics dashboard", included: true },
      { text: "Custom voice selection", included: true },
      { text: "Advanced AI scripting", included: true },
      { text: "Priority email support", included: true },
      { text: "Knowledge base integration", included: true },
      { text: "Dedicated account manager", included: false },
      { text: "Custom integrations", included: false },
    ],
    cta: "Start Free Trial",
    popular: true,
  },
  {
    name: "Enterprise",
    description: "For large firms with custom needs",
    price: "Custom",
    priceNote: "contact us",
    includedMinutes: "Unlimited",
    overageRate: "Volume discounts",
    features: [
      { text: "Unlimited minutes of AI call handling", included: true },
      { text: "Unlimited call recordings", included: true },
      { text: "Auto-transcription for all calls", included: true },
      { text: "Calendar sync (Outlook, Google Calendar)", included: true },
      { text: "Enterprise analytics & reporting", included: true },
      { text: "Custom voice selection", included: true },
      { text: "Advanced AI scripting", included: true },
      { text: "24/7 priority support", included: true },
      { text: "Knowledge base integration", included: true },
      { text: "Dedicated account manager", included: true },
      { text: "Custom integrations & API access", included: true },
      { text: "SLA guarantees", included: true },
      { text: "On-premise deployment options", included: true },
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

/**
 * Pricing page
 * Displays pricing tiers with features and usage limits
 */
export default function PricingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingPlan, setProcessingPlan] = useState<string | null>(null);

  // Fetch plans from API
  useEffect(() => {
    async function loadPlans() {
      try {
        const fetchedPlans = await fetchPlans();
        setPlans(fetchedPlans);
      } catch (error) {
        logger.error("Failed to fetch plans", error instanceof Error ? error : new Error(String(error)));
        // Continue with static tiers if API fails
      } finally {
        setIsLoading(false);
      }
    }
    loadPlans();
  }, []);

  // Map tier name to plan ID
  // Plans in database use lowercase names (starter, professional, enterprise)
  // Frontend tiers use capitalized names (Starter, Professional, Enterprise)
  const getPlanId = (tierName: string): string | null => {
    if (plans.length === 0) {
      logger.warn("No plans loaded from API");
      return null;
    }
    
    const plan = plans.find(
      (p) => p.name.toLowerCase() === tierName.toLowerCase()
    );
    
    if (!plan) {
      logger.error(`Plan not found for tier: ${tierName}`, {
        availablePlans: plans.map((p) => ({ name: p.name, id: p.id })),
        requestedTier: tierName,
      });
    }
    
    return plan?.id || null;
  };

  // Handle checkout button click
  const handleCheckout = async (tierName: string) => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      // Redirect to signup with checkout parameter
      const signupUrl = `/signup?redirect=${encodeURIComponent(`/pricing?checkout=${tierName.toLowerCase()}`)}`;
      router.push(signupUrl);
      return;
    }

    const planId = getPlanId(tierName);
    if (!planId) {
      logger.error(`Plan not found for tier: ${tierName}`);
      return;
    }

    try {
      setProcessingPlan(tierName);
      const session = await createCheckoutSession(planId);
      // Redirect to Stripe Checkout
      if (session.url) {
        window.location.href = session.url;
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (error) {
      logger.error("Failed to create checkout session", error instanceof Error ? error : new Error(String(error)));
      // Show error to user (don't redirect to signup since they're already authenticated)
    } finally {
      setProcessingPlan(null);
    }
  };

  // Handle automatic checkout after signup redirect
  useEffect(() => {
    // Wait for auth and plans to load
    if (authLoading || isLoading || plans.length === 0) return;
    
    // Check if user is authenticated and has a checkout parameter
    const checkoutPlan = searchParams.get("checkout");
    if (checkoutPlan && isAuthenticated) {
      // Remove checkout param from URL
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.delete("checkout");
      window.history.replaceState({}, "", newUrl.toString());
      
      // Automatically initiate checkout
      handleCheckout(checkoutPlan);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isLoading, isAuthenticated, plans.length, searchParams]);

  return (
    <div className="bg-white dark:bg-zinc-900 min-h-screen">
      <div className="container mx-auto px-4 py-16 sm:py-24">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4 text-zinc-900 dark:text-zinc-100">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
            Choose the plan that fits your firm. All plans include a 14-day free trial. No credit card required.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid gap-8 md:grid-cols-3 max-w-6xl mx-auto mb-16">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.name}
              className={tier.popular ? "border-2 border-zinc-900 dark:border-zinc-100 relative" : ""}
              hoverable
            >
              {tier.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </span>
                </div>
              )}
              
              <CardHeader className="text-center pb-6">
                <CardTitle className="text-2xl font-bold mb-2">{tier.name}</CardTitle>
                <p className="text-sm text-muted-foreground mb-6">{tier.description}</p>
                
                <div className="mb-4">
                  <div className="flex items-baseline justify-center gap-2">
                    <span className="text-4xl font-bold text-zinc-900 dark:text-zinc-100">
                      {tier.price}
                    </span>
                    {tier.priceNote && (
                      <span className="text-sm text-muted-foreground">
                        {tier.priceNote}
                      </span>
                    )}
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-center gap-2 text-zinc-700 dark:text-zinc-300">
                    <span className="font-medium">{tier.includedMinutes}</span>
                    <span className="text-muted-foreground">minutes included</span>
                  </div>
                  {tier.overageRate !== "Volume discounts" && (
                    <div className="text-muted-foreground">
                      Then {tier.overageRate}
                    </div>
                  )}
                  {tier.overageRate === "Volume discounts" && (
                    <div className="text-muted-foreground">
                      {tier.overageRate}
                    </div>
                  )}
                </div>
              </CardHeader>

              <CardContent className="space-y-6">
                <div className="space-y-3">
                  {tier.features.map((feature, index) => (
                    <div key={index} className="flex items-start gap-3">
                      {feature.included ? (
                        <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <div className="h-5 w-5 flex-shrink-0 mt-0.5" />
                      )}
                      <span
                        className={`text-sm ${
                          feature.included
                            ? "text-zinc-700 dark:text-zinc-300"
                            : "text-zinc-400 dark:text-zinc-600 line-through"
                        }`}
                      >
                        {feature.text}
                      </span>
                    </div>
                  ))}
                </div>

                {tier.name === "Enterprise" ? (
                  <Link href="/contact" className="block">
                    <Button
                      className="w-full"
                      variant="outline"
                    >
                      {tier.cta}
                    </Button>
                  </Link>
                ) : (
                  <Button
                    className={`w-full ${
                      tier.popular
                        ? "bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
                        : ""
                    }`}
                    variant={tier.popular ? "default" : "outline"}
                    onClick={() => handleCheckout(tier.name)}
                    disabled={isLoading || processingPlan === tier.name}
                  >
                    {processingPlan === tier.name ? "Processing..." : tier.cta}
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto mt-20">
          <h2 className="text-3xl font-bold text-center mb-12 text-zinc-900 dark:text-zinc-100">
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-8">
            <div>
              <h3 className="text-lg font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
                How are minutes calculated?
              </h3>
              <p className="text-zinc-600 dark:text-zinc-400">
                Minutes are calculated based on the total duration of AI-handled calls. This includes time spent on inbound calls answered by the AI assistant, outbound calls made by the system, and any call transfers or follow-ups.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
                What happens if I exceed my included minutes?
              </h3>
              <p className="text-zinc-600 dark:text-zinc-400">
                You'll be charged the overage rate for any minutes beyond your plan's included amount. Overage charges are billed at the end of your billing cycle. You can monitor your usage in real-time from your dashboard.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
                Can I change plans later?
              </h3>
              <p className="text-zinc-600 dark:text-zinc-400">
                Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any charges or credits accordingly.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
                Is there a setup fee?
              </h3>
              <p className="text-zinc-600 dark:text-zinc-400">
                No setup fees. All plans include free setup assistance to get you started. Enterprise plans include dedicated onboarding support.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-2 text-zinc-900 dark:text-zinc-100">
                What payment methods do you accept?
              </h3>
              <p className="text-zinc-600 dark:text-zinc-400">
                We accept all major credit cards, ACH transfers, and wire transfers for Enterprise customers. All payments are processed securely.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
