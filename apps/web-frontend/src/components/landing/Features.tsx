"use client";

import { useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { cn } from "@/lib/utils";

interface FeatureItem {
  id: number;
  title: string;
  icon: string;
  description: string;
}

interface FeaturesProps {
  features?: FeatureItem[];
}

const defaultFeatures: FeatureItem[] = [
  {
    id: 1,
    title: "AI-Powered Call Handling",
    icon: "/icons/phone-incoming.svg",
    description:
      "Advanced AI that understands legal terminology and context. Automatically routes calls, takes messages, and schedules appointments with natural conversation flow.",
  },
  {
    id: 2,
    title: "Appointment Scheduling",
    icon: "/icons/address-book-tabs.svg",
    description:
      "Sync contacts, cases, and calendar events automatically, and have the lexiq assistant schedule appointments for you.",
  },
  {
    id: 3,
    title: "Secure & Compliant",
    icon: "/icons/lock-laminated.svg",
    description:
      "HIPAA and SOC 2 compliant with end-to-end encryption. All call recordings and transcripts are securely stored and accessible only to authorized personnel.",
  },
  {
    id: 4,
    title: "24/7 Availability",
    icon: "/icons/hourglass-low.svg",
    description:
      "Never miss a call. Your AI assistant works around the clock, handling client inquiries, scheduling appointments, and providing basic information even after hours.",
  },
  {
    id: 5,
    title: "Analytics & Insights",
    icon: "/icons/chart-line-up.svg",
    description:
      "Comprehensive analytics dashboard showing call volume, response times, client satisfaction metrics, and insights to optimize your firm's communication strategy.",
  },
];

export function Features({ features = defaultFeatures }: FeaturesProps) {
  const [activeTabId, setActiveTabId] = useState<number | null>(1);
  const [activeIcon, setActiveIcon] = useState(features[0].icon);

  return (
    <section className="py-16 sm:py-24 bg-white dark:bg-zinc-900">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 sm:text-4xl">
            Powerful Features for Legal Professionals
          </h2>
          <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400">
            Everything you need to streamline your firm's communication
          </p>
        </div>

        <div className="mb-12 flex w-full flex-col items-start justify-between gap-12 md:flex-row">
          <div className="w-full md:w-1/2">
            <Accordion
              type="single"
              className="w-full"
              defaultValue="item-1"
              onValueChange={(value) => {
                const id = value ? parseInt(value.replace("item-", "")) : null;
                setActiveTabId(id);
                if (id) {
                  const feature = features.find((f) => f.id === id);
                  if (feature) {
                    setActiveIcon(feature.icon);
                  }
                }
              }}
            >
              {features.map((feature) => (
                <AccordionItem key={feature.id} value={`item-${feature.id}`}>
                  <AccordionTrigger
                    onClick={() => {
                      setActiveIcon(feature.icon);
                      setActiveTabId(feature.id);
                    }}
                    className="cursor-pointer py-5 !no-underline transition"
                  >
                    <h6
                      className={cn(
                        "text-xl font-semibold",
                        feature.id === activeTabId
                          ? "text-zinc-900 dark:text-zinc-100"
                          : "text-zinc-600 dark:text-zinc-400"
                      )}
                    >
                      {feature.title}
                    </h6>
                  </AccordionTrigger>
                  <AccordionContent>
                    <p className="mt-3 text-zinc-600 dark:text-zinc-400">
                      {feature.description}
                    </p>
                    <div className="mt-4 md:hidden flex items-center justify-center">
                      <img
                        src={feature.icon}
                        alt={feature.title}
                        className="h-48 w-48 object-contain dark:invert"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
          <div className="relative m-auto hidden w-1/2 overflow-hidden rounded-xl bg-zinc-100 dark:bg-zinc-800 md:flex items-center justify-center p-8 min-h-[400px]">
            <img
              src={activeIcon}
              alt="Feature icon"
              className="h-64 w-64 object-contain opacity-80"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
