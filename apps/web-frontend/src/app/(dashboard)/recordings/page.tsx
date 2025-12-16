"use client";

import { useState, useEffect, useRef, useMemo, useCallback, lazy, Suspense } from "react";
import { CallListItem, type Call, type CallStatus } from "@/components/inbox/CallListItem";
import { CallListSkeleton } from "@/components/inbox/CallListSkeleton";
import { FilterTabs, type FilterType } from "@/components/inbox/FilterTabs";
import { Transcript } from "@/components/inbox/Transcript";
import { SmartSummary } from "@/components/inbox/SmartSummary";
import { ActionToolbar } from "@/components/inbox/ActionToolbar";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Phone, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// Lazy load heavy audio player component (includes wavesurfer.js)
const AudioPlayer = lazy(() => 
  import("@/components/inbox/AudioPlayer").then(module => ({
    default: module.AudioPlayer,
  }))
);

// Re-export types for use in this file
export type { AudioPlayerRef, TranscriptSegment } from "@/components/inbox/AudioPlayer";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

/**
 * Recordings/Inbox Page
 * 
 * Master-detail view for viewing and managing call recordings.
 * 
 * Layout:
 * - Left Sidebar (30%): Filter tabs + Scrollable call list
 * - Right Pane (70%): Audio Player + Summary + Transcript + Actions
 * 
 * Features:
 * - Filter calls by status (All, Unread, Leads, Spam)
 * - Keyboard navigation (j/k keys)
 * - Karaoke mode (transcript highlights during playback)
 * - Click transcript sentences to jump to timestamps
 */
export default function RecordingsPage() {
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const audioPlayerRef = useRef<AudioPlayerRef>(null);
  // Loading state - will be replaced with actual hook loading states
  const [isLoadingCalls, setIsLoadingCalls] = useState(false);
  // Error state - will be replaced with actual hook error states
  const [callsError, setCallsError] = useState<Error | null>(null);

  // Mock call data - will be replaced with API calls later
  const mockCalls: Call[] = useMemo(
    () => [
      {
        id: "1",
        callerName: "John Doe",
        status: "new_client",
        summary: "Inquiry about estate planning services and will preparation...",
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
        phoneNumber: "+1 (555) 123-4567",
        duration: 180,
      },
      {
        id: "2",
        callerName: "Sarah Smith",
        status: "lead",
        summary: "Interested in business law consultation for startup incorporation...",
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000), // 5 hours ago
        phoneNumber: "+1 (555) 234-5678",
        duration: 240,
      },
      {
        id: "3",
        callerName: "Michael Johnson",
        status: "unread",
        summary: "Follow-up call regarding contract review and negotiation terms...",
        timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), // 1 day ago
        phoneNumber: "+1 (555) 345-6789",
        duration: 320,
      },
      {
        id: "4",
        callerName: "Emily Davis",
        status: "existing_client",
        summary: "Routine check-in about ongoing litigation case status...",
        timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
        phoneNumber: "+1 (555) 456-7890",
        duration: 150,
      },
      {
        id: "5",
        callerName: "Unknown Caller",
        status: "spam",
        summary: "Automated call about extended warranty for vehicle...",
        timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
        phoneNumber: "+1 (555) 000-0000",
        duration: 45,
      },
    ],
    []
  );

  // Filter calls based on active filter
  const filteredCalls = useMemo(() => {
    if (activeFilter === "all") return mockCalls;
    if (activeFilter === "unread") {
      return mockCalls.filter((call) => call.status === "unread");
    }
    if (activeFilter === "leads") {
      return mockCalls.filter((call) => call.status === "lead");
    }
    if (activeFilter === "spam") {
      return mockCalls.filter((call) => call.status === "spam");
    }
    return mockCalls;
  }, [activeFilter, mockCalls]);

  // Get selected call data
  const selectedCall = useMemo(() => {
    if (!selectedCallId) return null;
    return mockCalls.find((call) => call.id === selectedCallId) || null;
  }, [selectedCallId, mockCalls]);

  // Mock transcript data for selected call
  const mockTranscript: TranscriptSegment[] = useMemo(() => {
    if (!selectedCall) return [];
    return [
      { start: 0, end: 5, text: "Hello, thank you for calling. How can I assist you today?", speaker: "AI" },
      { start: 5, end: 12, text: "Hi, I'm interested in learning more about your estate planning services.", speaker: "Caller" },
      { start: 12, end: 20, text: "I'd be happy to help with that. Are you looking to create a will, or do you need assistance with trust planning?", speaker: "AI" },
      { start: 20, end: 28, text: "I'm not sure yet. This is my first time dealing with estate planning, so I'd like to understand my options.", speaker: "Caller" },
      { start: 28, end: 35, text: "That's perfectly fine. We offer a free consultation where we can discuss your specific needs and answer any questions you may have.", speaker: "AI" },
    ];
  }, [selectedCall]);

  // Mock summary data
  const mockSummary = useMemo(() => {
    if (!selectedCall) return [];
    return [
      "Client inquired about estate planning services",
      "First-time caller seeking information about will and trust options",
      "Expressed interest in free consultation",
      "No immediate urgency, exploring options",
    ];
  }, [selectedCall]);

  // Calculate filter counts
  const filterCounts = useMemo(() => {
    return {
      all: mockCalls.length,
      unread: mockCalls.filter((call) => call.status === "unread").length,
      leads: mockCalls.filter((call) => call.status === "lead").length,
      spam: mockCalls.filter((call) => call.status === "spam").length,
    };
  }, [mockCalls]);

  // Memoize time update handler to prevent unnecessary re-renders
  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  // Keyboard navigation (j/k/Enter/Esc keys)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if not typing in an input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      if (e.key === "j" || e.key === "k") {
        e.preventDefault();
        const currentIndex = filteredCalls.findIndex(
          (call) => call.id === selectedCallId
        );

        let newIndex: number;
        if (e.key === "j") {
          // Next call
          newIndex =
            currentIndex === -1
              ? 0
              : Math.min(currentIndex + 1, filteredCalls.length - 1);
        } else {
          // Previous call
          newIndex =
            currentIndex === -1
              ? filteredCalls.length - 1
              : Math.max(currentIndex - 1, 0);
        }

        if (filteredCalls[newIndex]) {
          setSelectedCallId(filteredCalls[newIndex].id);
        }
      } else if (e.key === "Enter") {
        // Open selected call (if not already open or if on mobile, ensure it's visible)
        e.preventDefault();
        if (selectedCallId && filteredCalls.find((call) => call.id === selectedCallId)) {
          // Call is already selected, but Enter ensures it's visible
          // On mobile, this will show the detail view
          // On desktop, it's already visible
        } else if (filteredCalls.length > 0) {
          // No call selected, select first one
          setSelectedCallId(filteredCalls[0].id);
        }
      } else if (e.key === "Escape") {
        // Close mobile detail view
        e.preventDefault();
        // On mobile, close the detail view and return to list
        if (window.innerWidth < 1024) {
          setSelectedCallId(null);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [filteredCalls, selectedCallId]);

  // Auto-select first call if none selected
  useEffect(() => {
    if (!selectedCallId && filteredCalls.length > 0) {
      setSelectedCallId(filteredCalls[0].id);
    }
  }, [selectedCallId, filteredCalls]);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4 -mx-4 -my-4 sm:-mx-6 sm:-my-6 lg:-mx-8 lg:-my-8">
      {/* Left Sidebar - Call List */}
      {/* Mobile/Tablet: Full width when no call selected, hidden when call selected */}
      {/* Desktop: Always visible, 30% width */}
      <div
        className={cn(
          "flex w-full flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900",
          "lg:w-[30%]",
          // On mobile/tablet, hide sidebar when call is selected
          selectedCallId && "hidden lg:flex"
        )}
      >
        {/* Sticky Filter Tabs */}
        <div className="px-4">
          <FilterTabs
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            counts={filterCounts}
          />
        </div>

        {/* Scrollable Call List */}
        <div
          className="flex-1 overflow-y-auto"
          role="listbox"
          aria-label="Call list"
          aria-activedescendant={selectedCallId ? `call-${selectedCallId}` : undefined}
        >
          {callsError ? (
            <div className="p-4">
              <ErrorState
                error={callsError}
                onRetry={() => {
                  setCallsError(null);
                  // In real implementation, this would call refetch()
                }}
                title="Failed to load calls"
                inline
              />
            </div>
          ) : isLoadingCalls ? (
            <CallListSkeleton count={5} />
          ) : filteredCalls.length === 0 ? (
            <EmptyState
              icon={<Phone className="h-12 w-12" />}
              title="No calls found"
              description={
                activeFilter === "all"
                  ? "You don't have any calls yet. Calls will appear here once they're recorded."
                  : `No ${activeFilter === "unread" ? "unread" : activeFilter === "leads" ? "lead" : "spam"} calls found.`
              }
              size="default"
            />
          ) : (
            <div className="divide-y divide-zinc-200 dark:divide-zinc-800" role="list">
              {filteredCalls.map((call) => (
                <div key={call.id} id={`call-${call.id}`} role="none">
                  <CallListItem
                    call={call}
                    isSelected={call.id === selectedCallId}
                    onClick={() => setSelectedCallId(call.id)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Pane - Detail View */}
      {/* Mobile/Tablet: Full screen overlay when call selected */}
      {/* Desktop: Always visible, 70% width */}
      <div
        className={cn(
          "hidden w-full flex-1 flex-col gap-4 overflow-y-auto px-4",
          "lg:flex lg:w-[70%]",
          // On mobile/tablet, show as full screen overlay
          selectedCallId && "lg:flex"
        )}
      >
        {selectedCall ? (
          <>
            {/* Header: Audio Player + Action Toolbar */}
            <div className="flex items-start justify-between gap-4 border-b border-zinc-200 pb-4 dark:border-zinc-800">
              <div className="flex-1">
                <h2 className="mb-2 text-lg font-semibold">
                  {selectedCall.callerName}
                </h2>
                <AudioPlayer
                  ref={audioPlayerRef}
                  // audioUrl will be available once API is implemented
                  // For now, leaving it undefined to show placeholder
                  audioUrl={undefined}
                    transcript={mockTranscript}
                    onTimeUpdate={handleTimeUpdate}
                />
              </div>
              <div className="flex-shrink-0">
                <ActionToolbar
                  onCall={() => console.log("Call clicked")}
                  onMail={() => console.log("Mail clicked")}
                  onArchive={() => console.log("Archive clicked")}
                  onExport={() => console.log("Export clicked")}
                />
              </div>
            </div>

            {/* Smart Summary Card */}
            <SmartSummary summary={mockSummary} />

            {/* Transcript Accordion */}
            <Transcript
              transcript={mockTranscript}
              currentTime={currentTime}
              onSentenceClick={(time) => {
                audioPlayerRef.current?.jumpToTime(time);
              }}
            />
          </>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="text-lg font-medium text-foreground">
                Select a call to view details
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Choose a call from the list to see the transcript, summary, and
                audio player
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Mobile/Tablet: Show selected call in full screen overlay */}
      {selectedCall && (
        <div className="fixed inset-0 z-50 flex flex-col bg-white dark:bg-zinc-900 lg:hidden">
          <div className="flex items-center justify-between border-b border-zinc-200 p-4 dark:border-zinc-800">
            <h2 className="text-lg font-semibold">{selectedCall.callerName}</h2>
            <button
              onClick={() => setSelectedCallId(null)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Close details"
            >
              Close
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-4">
              <AudioPlayer
                ref={audioPlayerRef}
                // audioUrl will be available once API is implemented
                // For now, leaving it undefined to show placeholder
                audioUrl={undefined}
                    transcript={mockTranscript}
                    onTimeUpdate={handleTimeUpdate}
              />
              <ActionToolbar
                onCall={() => console.log("Call clicked")}
                onMail={() => console.log("Mail clicked")}
                onArchive={() => console.log("Archive clicked")}
                onExport={() => console.log("Export clicked")}
              />
              <SmartSummary summary={mockSummary} />
              <Transcript
                transcript={mockTranscript}
                currentTime={currentTime}
                onSentenceClick={(time) => {
                  audioPlayerRef.current?.jumpToTime(time);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
