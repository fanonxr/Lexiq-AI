"use client";

import * as React from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { cn } from "@/lib/utils";
import type { TranscriptSegment } from "./AudioPlayer";

/**
 * Transcript Component
 * 
 * Displays call transcript in an accordion with karaoke mode highlighting.
 * Speaker labels are shown in bold mono font, and sentences are clickable
 * to jump to timestamps in the audio player.
 * 
 * @example
 * ```tsx
 * <Transcript
 *   transcript={[
 *     { start: 0, end: 5, text: "Hello, how can I help you?", speaker: "AI" },
 *     { start: 5, end: 10, text: "I need help with my case", speaker: "Caller" },
 *   ]}
 *   currentTime={3}
 *   onSentenceClick={(time) => audioPlayerRef.current?.jumpToTime(time)}
 * />
 * ```
 */

export interface TranscriptProps {
  /**
   * Array of transcript segments with timestamps
   */
  transcript: TranscriptSegment[];
  /**
   * Current playback time in seconds (for karaoke mode highlighting)
   */
  currentTime?: number;
  /**
   * Callback when a sentence is clicked (to jump audio to timestamp)
   */
  onSentenceClick?: (timestamp: number) => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Determine if a segment should be highlighted based on current time
 */
function isSegmentActive(
  segment: TranscriptSegment,
  currentTime: number | undefined
): boolean {
  if (currentTime === undefined) return false;
  return currentTime >= segment.start && currentTime < segment.end;
}

/**
 * Transcript Component
 * 
 * Features:
 * - Accordion with "View Full Transcript" trigger
 * - Speaker labels in bold mono font
 * - Karaoke mode: Highlights current sentence during playback
 * - Clickable sentences that jump audio to timestamp
 * - Readable text size (text-sm)
 */
export const Transcript = React.memo(function Transcript({
  transcript,
  currentTime,
  onSentenceClick,
  className,
}: TranscriptProps) {
  if (transcript.length === 0) {
    return (
      <div className={cn("text-sm text-muted-foreground p-4", className)}>
        No transcript available
      </div>
    );
  }

  return (
    <Accordion type="single" collapsible className={cn("w-full", className)}>
      <AccordionItem value="transcript">
        <AccordionTrigger>View Full Transcript</AccordionTrigger>
        <AccordionContent>
          <div className="space-y-3 pt-2">
            {transcript.map((segment, index) => {
              const isActive = isSegmentActive(segment, currentTime);
              const isClickable = !!onSentenceClick;

              return (
                <div
                  key={index}
                  className={cn(
                    "text-sm",
                    // Karaoke mode: Highlight active segment with subtle gray background
                    isActive && "bg-muted/50 rounded-md px-2 py-1",
                    // Smooth transition for highlighting
                    "transition-colors duration-200"
                  )}
                >
                  {/* Speaker label in bold mono font */}
                  <div className="font-mono font-bold text-foreground mb-1">
                    {segment.speaker}:
                  </div>
                  
                  {/* Transcript text - clickable to jump to timestamp */}
                  <button
                    onClick={() => {
                      if (isClickable) {
                        onSentenceClick?.(segment.start);
                      }
                    }}
                    disabled={!isClickable}
                    className={cn(
                      "text-sm text-foreground text-left w-full",
                      // Clickable styling
                      isClickable && "hover:text-primary cursor-pointer",
                      !isClickable && "cursor-default",
                      // Focus state
                      "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded-sm"
                    )}
                    aria-label={`Jump to ${segment.start} seconds`}
                  >
                    {segment.text}
                  </button>
                </div>
              );
            })}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
});

