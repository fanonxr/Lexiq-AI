"use client";

import * as React from "react";
import { useState } from "react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Button } from "@/components/ui/button";
import { Play, Pause, User, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Voice Lab Grid Component
 * 
 * Grid of voice cards for selecting AI voice. Each card displays
 * an avatar/icon, voice name, and play button for preview.
 * Selected voice has a thick black border ring.
 * 
 * @example
 * ```tsx
 * <VoiceLabGrid
 *   voices={[
 *     { id: "1", name: "Professional", icon: "user" },
 *     { id: "2", name: "Friendly", icon: "mic" },
 *   ]}
 *   selectedVoice="1"
 *   onVoiceSelect={(id) => setSelectedVoice(id)}
 * />
 * ```
 */

/**
 * Voice option interface
 */
export interface VoiceOption {
  /**
   * Unique identifier for the voice
   */
  id: string;
  /**
   * Display name of the voice
   */
  name: string;
  /**
   * Optional icon type ("user", "mic", or custom icon element)
   */
  icon?: "user" | "mic" | React.ReactNode;
  /**
   * Optional preview audio URL
   */
  previewUrl?: string;
  /**
   * Optional description
   */
  description?: string;
}

export interface VoiceLabGridProps {
  /**
   * Array of voice options
   */
  voices: VoiceOption[];
  /**
   * Currently selected voice ID
   */
  selectedVoice: string;
  /**
   * Callback when voice is selected
   */
  onVoiceSelect: (voiceId: string) => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get icon component based on icon type
 */
function getVoiceIcon(icon?: VoiceOption["icon"]): React.ReactNode {
  if (!icon) {
    return <User className="h-8 w-8" />;
  }

  if (typeof icon === "string") {
    switch (icon) {
      case "user":
        return <User className="h-8 w-8" />;
      case "mic":
        return <Mic className="h-8 w-8" />;
      default:
        return <User className="h-8 w-8" />;
    }
  }

  // Custom React node
  return icon;
}

/**
 * Voice Lab Grid Component
 * 
 * Features:
 * - Grid of voice cards (RadioGroup styled as cards)
 * - Each card: Avatar/icon, Voice Name, Play button
 * - Selected state: Thick black border ring
 * - Preview playback with waveform animation
 */
export function VoiceLabGrid({
  voices,
  selectedVoice,
  onVoiceSelect,
  className,
}: VoiceLabGridProps) {
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);

  const handlePlayPreview = (voiceId: string, previewUrl?: string) => {
    if (playingVoiceId === voiceId) {
      // Stop playback
      setPlayingVoiceId(null);
      // TODO: Stop audio playback
    } else {
      // Start playback
      setPlayingVoiceId(voiceId);
      if (previewUrl) {
        // TODO: Play audio preview
        // For now, just simulate with timeout
        setTimeout(() => {
          setPlayingVoiceId(null);
        }, 3000);
      }
    }
  };

  // Handle null/undefined voices
  if (!voices || voices.length === 0) {
    return (
      <div className={cn("text-sm text-muted-foreground p-4", className)}>
        No voices available
      </div>
    );
  }

  return (
    <RadioGroup
      value={selectedVoice}
      onValueChange={onVoiceSelect}
      className={cn(
        // Mobile: 1 column, Tablet: 2 columns, Desktop: 3 columns
        "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
        className
      )}
    >
      {voices.map((voice) => {
        const isSelected = selectedVoice === voice.id;
        const isPlaying = playingVoiceId === voice.id;

        return (
          <label
            key={voice.id}
            className={cn(
              "relative flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 p-4 transition-colors",
              // Base border
              "border-zinc-200 dark:border-zinc-800",
              // Hover state
              "hover:border-zinc-300 dark:hover:border-zinc-700",
              // Selected state: Thick black border ring
              isSelected && "border-primary border-4",
              // Background
              "bg-white dark:bg-zinc-900",
              // Focus state - visible focus indicator for keyboard navigation
              "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"
            )}
          >
            <RadioGroupItem
              value={voice.id}
              className="sr-only"
              aria-label={`Select ${voice.name} voice`}
            />

            {/* Avatar/Icon */}
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted text-muted-foreground">
              {getVoiceIcon(voice.icon)}
            </div>

            {/* Voice Name */}
            <div className="text-center">
              <div className="text-sm font-semibold text-foreground">
                {voice.name}
              </div>
              {voice.description && (
                <div className="mt-1 text-xs text-muted-foreground">
                  {voice.description}
                </div>
              )}
            </div>

            {/* Play Button */}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-full"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handlePlayPreview(voice.id, voice.previewUrl);
              }}
              aria-label={isPlaying ? `Pause ${voice.name} preview` : `Play ${voice.name} preview`}
            >
              {isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>

            {/* Waveform Animation (when playing) */}
            {isPlaying && (
              <div className="absolute bottom-2 left-1/2 flex -translate-x-1/2 gap-1">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "h-1 w-1 rounded-full bg-primary",
                      "animate-pulse"
                    )}
                    style={{
                      animationDelay: `${i * 0.1}s`,
                      animationDuration: "0.6s",
                    }}
                  />
                ))}
              </div>
            )}
          </label>
        );
      })}
    </RadioGroup>
  );
}

