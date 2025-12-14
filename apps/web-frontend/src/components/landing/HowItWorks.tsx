"use client";

import { cn } from "@/lib/utils";
import { Layers, Search, Zap } from "lucide-react";
import type React from "react";

interface HowItWorksProps extends React.HTMLAttributes<HTMLElement> {}

interface StepCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  benefits: string[];
}

const StepCard: React.FC<StepCardProps> = ({
  icon,
  title,
  description,
  benefits,
}) => (
  <div
    className={cn(
      "relative rounded-2xl border border-zinc-200 bg-white p-6 text-zinc-900 transition-all duration-300 ease-in-out dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100",
      "hover:scale-105 hover:shadow-lg hover:border-zinc-400 hover:bg-zinc-50 dark:hover:border-zinc-600 dark:hover:bg-zinc-800"
    )}
  >
    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100">
      {icon}
    </div>
    <h3 className="mb-2 text-xl font-semibold">{title}</h3>
    <p className="mb-6 text-zinc-600 dark:text-zinc-400">{description}</p>
    <ul className="space-y-3">
      {benefits.map((benefit, index) => (
        <li key={index} className="flex items-center gap-3">
          <div className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-zinc-200 dark:bg-zinc-700">
            <div className="h-2 w-2 rounded-full bg-zinc-900 dark:bg-zinc-100"></div>
          </div>
          <span className="text-zinc-600 dark:text-zinc-400">{benefit}</span>
        </li>
      ))}
    </ul>
  </div>
);

export const HowItWorks: React.FC<HowItWorksProps> = ({
  className,
  ...props
}) => {
  const stepsData = [
    {
      icon: <Search className="h-6 w-6" />,
      title: "Set Up Your AI Assistant",
      description:
        "Configure your AI assistant with your firm's information, office hours, and preferences. Integration with your CRM takes just minutes.",
      benefits: [
        "Quick setup wizard guides you through configuration",
        "Automatic CRM synchronization",
        "Customizable greeting and call handling rules",
      ],
    },
    {
      icon: <Layers className="h-6 w-6" />,
      title: "Handle Calls Automatically",
      description:
        "Your AI assistant answers calls, understands client needs, schedules appointments, and routes urgent matters to the right team member.",
      benefits: [
        "Natural conversation flow with clients",
        "Intelligent call routing based on urgency",
        "Automatic calendar integration",
      ],
    },
    {
      icon: <Zap className="h-6 w-6" />,
      title: "Review & Optimize",
      description:
        "Access call transcripts, analytics, and insights. Continuously improve your assistant's performance with detailed reporting.",
      benefits: [
        "Complete call transcripts and recordings",
        "Performance analytics and insights",
        "Easy optimization based on data",
      ],
    },
  ];

  return (
    <section
      id="how-it-works"
      className={cn(
        "w-full bg-zinc-50 py-16 dark:bg-zinc-950 sm:py-24",
        className
      )}
      {...props}
    >
      <div className="container mx-auto px-4">
        <div className="mx-auto mb-16 max-w-4xl text-center">
          <h2 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 sm:text-5xl">
            How it works
          </h2>
          <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400">
            Get started with LexiqAI in three simple steps and transform your
            firm's communication workflow
          </p>
        </div>

        <div className="relative mx-auto mb-8 w-full max-w-4xl">
          <div
            aria-hidden="true"
            className="absolute left-[16.6667%] top-1/2 h-0.5 w-[66.6667%] -translate-y-1/2 bg-zinc-300 dark:bg-zinc-700"
          ></div>
          <div className="relative grid grid-cols-3">
            {stepsData.map((_, index) => (
              <div
                key={index}
                className="flex h-8 w-8 items-center justify-center justify-self-center rounded-full bg-zinc-200 font-semibold text-zinc-900 ring-4 ring-zinc-50 dark:bg-zinc-800 dark:text-zinc-100 dark:ring-zinc-950"
              >
                {index + 1}
              </div>
            ))}
          </div>
        </div>

        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-8 md:grid-cols-3">
          {stepsData.map((step, index) => (
            <StepCard
              key={index}
              icon={step.icon}
              title={step.title}
              description={step.description}
              benefits={step.benefits}
            />
          ))}
        </div>
      </div>
    </section>
  );
};
