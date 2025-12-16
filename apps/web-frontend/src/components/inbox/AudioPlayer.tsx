"use client";

import * as React from "react";
import { useEffect, useRef, useState, useCallback } from "react";
import WaveSurfer from "wavesurfer.js";
import { Play, Pause, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Audio Player Component
 * 
 * Custom audio player with waveform visualization using wavesurfer.js.
 * Features vertical bars that turn from gray to black as playback advances.
 * 
 * @example
 * ```tsx
 * <AudioPlayer
 *   audioUrl="/audio/recording.mp3"
 *   transcript={[
 *     { start: 0, end: 5, text: "Hello", speaker: "AI" },
 *     { start: 5, end: 10, text: "Hi there", speaker: "Caller" },
 *   ]}
 *   onTimeUpdate={(time) => console.log("Current time:", time)}
 * />
 * 
 * // Without audioUrl (shows placeholder)
 * <AudioPlayer
 *   transcript={transcriptSegments}
 * />
 * ```
 */

/**
 * Transcript segment interface
 */
export interface TranscriptSegment {
  start: number; // Start time in seconds
  end: number; // End time in seconds
  text: string; // Transcript text
  speaker: string; // Speaker label (e.g., "AI", "Caller")
}

export interface AudioPlayerProps {
  /**
   * URL of the audio file to play
   * If not provided, shows a placeholder message
   */
  audioUrl?: string;
  /**
   * Optional transcript segments for timestamp navigation
   */
  transcript?: TranscriptSegment[];
  /**
   * Callback when playback time updates
   */
  onTimeUpdate?: (time: number) => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Audio Player Ref methods
 */
export interface AudioPlayerRef {
  jumpToTime: (time: number) => void;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  getCurrentTime: () => number;
  getDuration: () => number;
}

/**
 * Format seconds to MM:SS
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Audio Player Component
 * 
 * Uses wavesurfer.js for waveform visualization with vertical bars.
 * Bars turn from gray to black as playback advances.
 * 
 * Supports ref forwarding for programmatic control (e.g., jumping to timestamps from transcript).
 */
export const AudioPlayer = React.forwardRef<AudioPlayerRef, AudioPlayerProps>(
  function AudioPlayer(
    {
      audioUrl,
      transcript,
      onTimeUpdate,
      className,
    },
    ref
  ) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Initialize WaveSurfer
  useEffect(() => {
    if (!waveformRef.current) return;

    // If no audioUrl provided, show placeholder
    if (!audioUrl) {
      setIsLoading(false);
      setError("Audio not available");
      return;
    }

    // Create WaveSurfer instance
    const wavesurfer = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: "#a1a1aa", // zinc-400 - gray bars
      progressColor: "#09090b", // zinc-950 - black progress
      cursorColor: "#09090b", // black cursor
      barWidth: 2,
      barRadius: 1,
      barGap: 1,
      height: 80,
      normalize: true,
      backend: "WebAudio",
      mediaControls: false,
    });

    wavesurferRef.current = wavesurfer;

    // Event handlers
    wavesurfer.on("ready", () => {
      setIsLoading(false);
      setDuration(wavesurfer.getDuration());
      setError(null);
    });

    wavesurfer.on("play", () => {
      setIsPlaying(true);
    });

    wavesurfer.on("pause", () => {
      setIsPlaying(false);
    });

    wavesurfer.on("timeupdate", (time: number) => {
      setCurrentTime(time);
      onTimeUpdate?.(time);
    });

    wavesurfer.on("error", (err: Error | string) => {
      const errorMessage = typeof err === "string" ? err : err.message || "Failed to load audio";
      setError(errorMessage);
      setIsLoading(false);
    });

    // Load audio with error handling
    try {
      wavesurfer.load(audioUrl).catch((err) => {
        setError("Failed to load audio file");
        setIsLoading(false);
      });
    } catch (err) {
      setError("Failed to initialize audio player");
      setIsLoading(false);
    }

    // Cleanup
    return () => {
      try {
        wavesurfer.destroy();
      } catch (err) {
        // Ignore cleanup errors
      }
      wavesurferRef.current = null;
    };
  }, [audioUrl, onTimeUpdate]);

  // Play/pause handler
  const handlePlayPause = useCallback(() => {
    if (!wavesurferRef.current) return;

    if (isPlaying) {
      wavesurferRef.current.pause();
    } else {
      wavesurferRef.current.play();
    }
  }, [isPlaying]);

  // Jump to timestamp (for transcript integration)
  const jumpToTime = useCallback((time: number) => {
    if (!wavesurferRef.current || duration === 0) return;
    const normalizedTime = Math.max(0, Math.min(time, duration));
    wavesurferRef.current.seekTo(normalizedTime / duration);
  }, [duration]);

  // Expose methods via ref (for parent components like Transcript)
  React.useImperativeHandle(
    ref,
    () => ({
      jumpToTime,
      play: () => {
        wavesurferRef.current?.play();
      },
      pause: () => {
        wavesurferRef.current?.pause();
      },
      seek: (time: number) => {
        if (wavesurferRef.current && duration > 0) {
          const normalizedTime = Math.max(0, Math.min(time, duration));
          wavesurferRef.current.seekTo(normalizedTime / duration);
        }
      },
      getCurrentTime: () => currentTime,
      getDuration: () => duration,
    }),
    [jumpToTime, currentTime, duration]
  );

  return (
    <div className={cn("space-y-3", className)}>
      {/* Waveform Container */}
      <div className="relative">
        <div ref={waveformRef} className="w-full" />
        
        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-zinc-900/50">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Error Message or Placeholder */}
        {(error || !audioUrl) && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-zinc-900/50 rounded-md">
            <div className="text-center p-4">
              <p className="text-sm text-muted-foreground">
                {!audioUrl ? "Audio recording not available" : error || "Failed to load audio"}
              </p>
              {!audioUrl && (
                <p className="text-xs text-muted-foreground mt-1">
                  Audio will be available once the recording is processed
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Controls and Time Display */}
      <div className="flex items-center justify-between gap-4" role="group" aria-label="Audio player controls">
        {/* Play/Pause Button */}
        <Button
          variant="outline"
          size="icon"
          onClick={handlePlayPause}
          disabled={isLoading || !!error || !audioUrl || duration === 0}
          className="flex-shrink-0"
          aria-label={isPlaying ? "Pause audio" : "Play audio"}
          aria-pressed={isPlaying}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>

        {/* Time Display */}
        <div className="flex items-center gap-2 flex-1 min-w-0" aria-live="polite" aria-atomic="true">
          <span className="text-xs font-mono text-muted-foreground tabular-nums" aria-label="Current time">
            {formatTime(currentTime)}
          </span>
          <span className="text-xs text-muted-foreground" aria-hidden="true">/</span>
          <span className="text-xs font-mono text-muted-foreground tabular-nums" aria-label="Total duration">
            {formatTime(duration)}
          </span>
        </div>
      </div>
    </div>
  );
  }
);

