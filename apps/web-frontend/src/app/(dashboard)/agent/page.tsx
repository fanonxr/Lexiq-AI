"use client";

import { useState, useEffect, useCallback } from "react";
import { VoiceLabGrid, type VoiceOption } from "@/components/agent/VoiceLabGrid";
import { ScriptingInput } from "@/components/agent/ScriptingInput";
import { BehaviorToggle } from "@/components/agent/BehaviorToggle";
import { TestPlayground } from "@/components/agent/TestPlayground";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

/**
 * Agent Configuration Page
 * 
 * Agent Architect (Customization Page) for configuring AI agent settings.
 * 
 * Layout:
 * - Two-Column Split:
 *   - Left (60%): Scrollable form with voice selection, scripting, and behavior toggles
 *   - Right (40%): Sticky Test Playground
 * 
 * Features:
 * - Voice selection grid
 * - Scripting inputs with AI improve buttons
 * - Behavior toggles
 * - Auto-save functionality
 * - Test playground for testing configuration
 */
export default function AgentPage() {
  // Voice selection
  const [selectedVoice, setSelectedVoice] = useState<string>("1");

  // Scripting inputs
  const [greetingScript, setGreetingScript] = useState(
    "Hello, thank you for calling. How can I assist you today?"
  );
  const [closingScript, setClosingScript] = useState(
    "Thank you for calling. Have a great day!"
  );
  const [transferScript, setTransferScript] = useState(
    "Let me transfer you to someone who can better assist you."
  );

  // Behavior toggles
  const [autoRespond, setAutoRespond] = useState(false);
  const [recordCalls, setRecordCalls] = useState(true);
  const [autoTranscribe, setAutoTranscribe] = useState(true);
  const [enableVoicemail, setEnableVoicemail] = useState(true);

  // Auto-save state
  const [isSaving, setIsSaving] = useState(false);
  const [showSavedIndicator, setShowSavedIndicator] = useState(false);

  // Test call state
  const [isCalling, setIsCalling] = useState(false);

  // Mock voice options
  const voiceOptions: VoiceOption[] = [
    {
      id: "1",
      name: "Professional",
      icon: "user",
      description: "Clear and professional tone",
      previewUrl: "/audio/voice-professional.mp3",
    },
    {
      id: "2",
      name: "Friendly",
      icon: "mic",
      description: "Warm and approachable",
      previewUrl: "/audio/voice-friendly.mp3",
    },
    {
      id: "3",
      name: "Assistant",
      icon: "user",
      description: "Neutral and helpful",
      previewUrl: "/audio/voice-assistant.mp3",
    },
    {
      id: "4",
      name: "Executive",
      icon: "user",
      description: "Confident and authoritative",
      previewUrl: "/audio/voice-executive.mp3",
    },
  ];

  // Auto-save functionality (debounced)
  useEffect(() => {
    // Debounce auto-save
    const timer = setTimeout(() => {
      if (greetingScript || closingScript || transferScript) {
        handleAutoSave();
      }
    }, 2000); // 2 second debounce

    return () => clearTimeout(timer);
  }, [greetingScript, closingScript, transferScript, selectedVoice, autoRespond, recordCalls, autoTranscribe, enableVoicemail]);

  const handleAutoSave = useCallback(async () => {
    setIsSaving(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    // Mock save - in real implementation, this would call the API
    console.log("Auto-saving agent configuration:", {
      selectedVoice,
      greetingScript,
      closingScript,
      transferScript,
      autoRespond,
      recordCalls,
      autoTranscribe,
      enableVoicemail,
    });

    setIsSaving(false);
    setShowSavedIndicator(true);

    // Hide saved indicator after 2 seconds
    setTimeout(() => {
      setShowSavedIndicator(false);
    }, 2000);
  }, [selectedVoice, greetingScript, closingScript, transferScript, autoRespond, recordCalls, autoTranscribe, enableVoicemail]);

  const handleImproveGreeting = async () => {
    // Mock AI improvement
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setGreetingScript(
      "Hello, thank you for calling [Company Name]. My name is [AI Name], and I'm here to help you today. How can I assist you?"
    );
  };

  const handleImproveClosing = async () => {
    // Mock AI improvement
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setClosingScript(
      "Thank you for calling [Company Name]. We appreciate your time today. If you have any further questions, please don't hesitate to reach out. Have a wonderful day!"
    );
  };

  const handleImproveTransfer = async () => {
    // Mock AI improvement
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setTransferScript(
      "I understand you'd like to speak with someone who can provide more specialized assistance. Let me transfer you to the right person who can help you with that."
    );
  };

  const handleTestCall = async (phoneNumber: string) => {
    setIsCalling(true);
    // Mock test call - in real implementation, this would call the API
    console.log("Initiating test call to:", phoneNumber);
    
    // Simulate call initiation
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    setIsCalling(false);
    // In real implementation, you might show a success message or handle the call result
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            Agent Configuration
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Customize your AI agent's voice, scripts, and behavior
          </p>
        </div>

        {/* Auto-save Indicator */}
        {showSavedIndicator && (
          <div className="flex items-center gap-2 text-sm text-green-600">
            <Check className="h-4 w-4" />
            <span>Saved</span>
          </div>
        )}
        {isSaving && !showSavedIndicator && (
          <div className="text-sm text-muted-foreground">Saving...</div>
        )}
      </div>

      {/* Two-Column Layout */}
      {/* Mobile: Stack vertically, Tablet: Stack vertically, Desktop: Side by side (3/2 split) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Left Column - Settings (60% = 3 columns on desktop) */}
        <div className="lg:col-span-3 space-y-6">
          {/* Voice Selection */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Voice Selection</CardTitle>
            </CardHeader>
            <CardContent>
              <VoiceLabGrid
                voices={voiceOptions}
                selectedVoice={selectedVoice}
                onVoiceSelect={setSelectedVoice}
              />
            </CardContent>
          </Card>

          {/* Scripting Inputs */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Scripts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <ScriptingInput
                label="Greeting Script"
                placeholder="Enter the greeting message your agent will use..."
                value={greetingScript}
                onChange={setGreetingScript}
                onImproveWithAI={handleImproveGreeting}
                height="100px"
              />

              <ScriptingInput
                label="Closing Script"
                placeholder="Enter the closing message your agent will use..."
                value={closingScript}
                onChange={setClosingScript}
                onImproveWithAI={handleImproveClosing}
                height="100px"
              />

              <ScriptingInput
                label="Transfer Script"
                placeholder="Enter the message when transferring calls..."
                value={transferScript}
                onChange={setTransferScript}
                onImproveWithAI={handleImproveTransfer}
                height="100px"
              />
            </CardContent>
          </Card>

          {/* Behavior Toggles */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Behavior Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1 divide-y divide-zinc-200 dark:divide-zinc-800">
                <BehaviorToggle
                  label="Auto-respond to voicemails"
                  description="Automatically send follow-up emails for missed calls and voicemails"
                  checked={autoRespond}
                  onChange={setAutoRespond}
                />

                <BehaviorToggle
                  label="Record all calls"
                  description="Automatically record and store all incoming and outgoing calls"
                  checked={recordCalls}
                  onChange={setRecordCalls}
                />

                <BehaviorToggle
                  label="Auto-transcribe calls"
                  description="Automatically generate transcripts for all recorded calls"
                  checked={autoTranscribe}
                  onChange={setAutoTranscribe}
                />

                <BehaviorToggle
                  label="Enable voicemail"
                  description="Allow callers to leave voicemail messages when calls are not answered"
                  checked={enableVoicemail}
                  onChange={setEnableVoicemail}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Test Playground (40% = 2 columns) */}
        <div className="lg:col-span-2">
          <TestPlayground
            onTestCall={handleTestCall}
            isCalling={isCalling}
          />
        </div>
      </div>
    </div>
  );
}

