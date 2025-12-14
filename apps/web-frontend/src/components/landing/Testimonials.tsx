"use client";

import React from "react";
import { motion } from "framer-motion";

interface Testimonial {
  text: string;
  image: string;
  name: string;
  role: string;
}

interface TestimonialsColumnProps {
  className?: string;
  testimonials: Testimonial[];
  duration?: number;
}

export const TestimonialsColumn: React.FC<TestimonialsColumnProps> = ({
  className,
  testimonials,
  duration = 10,
}) => {
  return (
    <div className={className}>
      <motion.div
        animate={{
          translateY: "-50%",
        }}
        transition={{
          duration: duration,
          repeat: Infinity,
          ease: "linear",
          repeatType: "loop",
        }}
        className="flex flex-col gap-6 pb-6 bg-transparent"
      >
        {[
          ...new Array(2).fill(0).map((_, index) => (
            <React.Fragment key={index}>
              {testimonials.map(({ text, image, name, role }, i) => (
                <div
                  className="p-10 rounded-3xl border border-zinc-200 bg-white shadow-lg max-w-xs w-full dark:border-zinc-800 dark:bg-zinc-900"
                  key={`testimonial-${index}-${i}`}
                >
                  <div className="text-zinc-700 dark:text-zinc-300">{text}</div>
                  <div className="flex items-center gap-2 mt-5">
                    <div
                      className="h-10 w-10 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-xs font-semibold text-zinc-600 dark:text-zinc-400"
                      style={{
                        backgroundImage: image.startsWith("data:") ? "none" : `url(${image})`,
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                      }}
                    >
                      {image.startsWith("data:") && name[0]?.toUpperCase()}
                    </div>
                    <div className="flex flex-col">
                      <div className="font-medium tracking-tight leading-5 text-zinc-900 dark:text-zinc-100">
                        {name}
                      </div>
                      <div className="leading-5 opacity-60 tracking-tight text-zinc-600 dark:text-zinc-400">
                        {role}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </React.Fragment>
          )),
        ]}
      </motion.div>
    </div>
  );
};

const defaultTestimonials: Testimonial[] = [
  {
    text: "LexiqAI has transformed how we handle client calls. The AI assistant is incredibly intelligent and handles complex scheduling requests flawlessly.",
    image: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop&crop=face",
    name: "Sarah Johnson",
    role: "Managing Partner",
  },
  {
    text: "Integration with our CRM was seamless. Our team can now focus on legal work while LexiqAI handles routine client communications.",
    image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face",
    name: "Michael Chen",
    role: "Senior Attorney",
  },
  {
    text: "The HIPAA compliance and security features give us peace of mind. Our clients trust that their information is protected.",
    image: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face",
    name: "Emily Rodriguez",
    role: "Legal Operations Director",
  },
  {
    text: "24/7 availability means we never miss a potential client. The AI assistant captures every lead, even after hours.",
    image: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face",
    name: "David Thompson",
    role: "Practice Manager",
  },
  {
    text: "The analytics dashboard provides incredible insights into our call patterns. We've optimized our staffing based on the data.",
    image: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=face",
    name: "Jennifer Martinez",
    role: "Firm Administrator",
  },
  {
    text: "Setup was incredibly easy. We were up and running in under an hour, and the support team was there every step of the way.",
    image: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&h=150&fit=crop&crop=face",
    name: "Robert Williams",
    role: "IT Director",
  },
  {
    text: "The natural language processing is impressive. Clients don't realize they're talking to an AI - it feels completely human.",
    image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&h=150&fit=crop&crop=face",
    name: "Amanda Lee",
    role: "Client Relations Manager",
  },
  {
    text: "ROI was immediate. We've reduced our call handling costs by 60% while improving client satisfaction scores.",
    image: "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150&h=150&fit=crop&crop=face",
    name: "James Wilson",
    role: "CFO",
  },
  {
    text: "The transcription and recording features are game-changers for compliance. Everything is automatically documented and searchable.",
    image: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&h=150&fit=crop&crop=face",
    name: "Lisa Anderson",
    role: "Compliance Officer",
  },
];

export function Testimonials({
  testimonials = defaultTestimonials,
}: {
  testimonials?: Testimonial[];
}) {
  const firstColumn = testimonials.slice(0, 3);
  const secondColumn = testimonials.slice(3, 6);
  const thirdColumn = testimonials.slice(6, 9);

  return (
    <section className="bg-white dark:bg-zinc-900 py-16 sm:py-20 relative -mt-px">
      <div className="container z-10 mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          viewport={{ once: true }}
          className="flex flex-col items-center justify-center max-w-[540px] mx-auto"
        >
          <h2 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl xl:text-5xl font-bold tracking-tighter text-zinc-900 dark:text-zinc-100">
            What our users say
          </h2>
          <p className="text-center mt-5 opacity-75 text-zinc-600 dark:text-zinc-400">
            See what our customers have to say about us.
          </p>
        </motion.div>

        <div className="flex justify-center gap-6 mt-10 [mask-image:linear-gradient(to_bottom,transparent,black_25%,black_75%,transparent)] max-h-[740px] overflow-hidden">
          <TestimonialsColumn testimonials={firstColumn} duration={15} />
          <TestimonialsColumn
            testimonials={secondColumn}
            className="hidden md:block"
            duration={19}
          />
          <TestimonialsColumn
            testimonials={thirdColumn}
            className="hidden lg:block"
            duration={17}
          />
        </div>
      </div>
    </section>
  );
}
