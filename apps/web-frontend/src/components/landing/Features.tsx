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
  image: string;
  description: string;
}

interface FeaturesProps {
  features?: FeatureItem[];
}

const defaultFeatures: FeatureItem[] = [
  {
    id: 1,
    title: "AI-Powered Call Handling",
    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23e4e4e7' width='800' height='600'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='24' fill='%23918196' text-anchor='middle' dominant-baseline='middle'%3EAI Call Handling%3C/text%3E%3C/svg%3E",
    description:
      "Advanced AI that understands legal terminology and context. Automatically routes calls, takes messages, and schedules appointments with natural conversation flow.",
  },
  {
    id: 2,
    title: "CRM Integration",
    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23e4e4e7' width='800' height='600'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='24' fill='%23918196' text-anchor='middle' dominant-baseline='middle'%3ECRM Integration%3C/text%3E%3C/svg%3E",
    description:
      "Seamlessly integrates with popular legal CRMs including Clio, PracticePanther, and MyCase. Sync contacts, cases, and calendar events automatically.",
  },
  {
    id: 3,
    title: "Secure & Compliant",
    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23e4e4e7' width='800' height='600'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='24' fill='%23918196' text-anchor='middle' dominant-baseline='middle'%3ESecurity%3C/text%3E%3C/svg%3E",
    description:
      "HIPAA and SOC 2 compliant with end-to-end encryption. All call recordings and transcripts are securely stored and accessible only to authorized personnel.",
  },
  {
    id: 4,
    title: "24/7 Availability",
    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23e4e4e7' width='800' height='600'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='24' fill='%23918196' text-anchor='middle' dominant-baseline='middle'%3E24/7 Support%3C/text%3E%3C/svg%3E",
    description:
      "Never miss a call. Your AI assistant works around the clock, handling client inquiries, scheduling appointments, and providing basic information even after hours.",
  },
  {
    id: 5,
    title: "Analytics & Insights",
    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600'%3E%3Crect fill='%23e4e4e7' width='800' height='600'/%3E%3Ctext x='50%25' y='50%25' font-family='Arial' font-size='24' fill='%23918196' text-anchor='middle' dominant-baseline='middle'%3EAnalytics%3C/text%3E%3C/svg%3E",
    description:
      "Comprehensive analytics dashboard showing call volume, response times, client satisfaction metrics, and insights to optimize your firm's communication strategy.",
  },
];

export function Features({ features = defaultFeatures }: FeaturesProps) {
  const [activeTabId, setActiveTabId] = useState<number | null>(1);
  const [activeImage, setActiveImage] = useState(features[0].image);

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
                    setActiveImage(feature.image);
                  }
                }
              }}
            >
              {features.map((feature) => (
                <AccordionItem key={feature.id} value={`item-${feature.id}`}>
                  <AccordionTrigger
                    onClick={() => {
                      setActiveImage(feature.image);
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
                    <div className="mt-4 md:hidden">
                      <img
                        src={feature.image}
                        alt={feature.title}
                        className="h-full max-h-80 w-full rounded-md object-cover"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
          <div className="relative m-auto hidden w-1/2 overflow-hidden rounded-xl bg-zinc-100 dark:bg-zinc-800 md:block">
            <img
              src={activeImage}
              alt="Feature preview"
              className="aspect-[4/3] rounded-md object-cover pl-4"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
