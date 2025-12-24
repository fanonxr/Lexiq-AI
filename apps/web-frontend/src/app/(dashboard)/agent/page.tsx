"use client";

import { useState, useEffect, useCallback } from "react";
import { VoiceLabGrid, type VoiceOption } from "@/components/agent/VoiceLabGrid";
import { ScriptingInput } from "@/components/agent/ScriptingInput";
import { BehaviorToggle } from "@/components/agent/BehaviorToggle";
import { TestPlayground } from "@/components/agent/TestPlayground";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAgentConfig, useUpdateAgentConfig, useVoiceOptions, useTestCall, useImproveScript } from "@/hooks/useAgent";

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
  // Fetch agent config and voice options
  const { data: config, isLoading: configLoading, error: configError, refetch: refetchConfig } = useAgentConfig();
  const { data: voiceOptions = [], isLoading: voicesLoading } = useVoiceOptions();
  const { mutate: updateConfig, isLoading: isUpdating } = useUpdateAgentConfig();
  const { mutate: testCall, isLoading: isCalling } = useTestCall();
  const { mutate: improveScript, isLoading: isImproving } = useImproveScript();

  // Local state (initialized from config when loaded)
  const [selectedVoice, setSelectedVoice] = useState<string>("1");
  const [greetingScript, setGreetingScript] = useState("Hello, thank you for calling. How can I assist you today?");
  const [closingScript, setClosingScript] = useState("Thank you for calling. Have a great day!");
  const [transferScript, setTransferScript] = useState("Let me transfer you to someone who can better assist you.");
  const [autoRespond, setAutoRespond] = useState(false);
  const [recordCalls, setRecordCalls] = useState(true);
  const [autoTranscribe, setAutoTranscribe] = useState(true);
  const [enableVoicemail, setEnableVoicemail] = useState(true);

  // Auto-save state
  const [showSavedIndicator, setShowSavedIndicator] = useState(false);

  // Initialize state from config when loaded
  useEffect(() => {
    if (config) {
      setSelectedVoice(config.voiceId || "1");
      setGreetingScript(config.greetingScript || "Hello, thank you for calling. How can I assist you today?");
      setClosingScript(config.closingScript || "Thank you for calling. Have a great day!");
      setTransferScript(config.transferScript || "Let me transfer you to someone who can better assist you.");
      setAutoRespond(config.autoRespond ?? false);
      setRecordCalls(config.recordCalls ?? true);
      setAutoTranscribe(config.autoTranscribe ?? true);
      setEnableVoicemail(config.enableVoicemail ?? true);
    }
  }, [config]);

  // Auto-save functionality (debounced)
  useEffect(() => {
    // Skip auto-save if config is still loading or if this is the initial load
    if (configLoading || !config) {
      return;
    }

    // Debounce auto-save
    const timer = setTimeout(() => {
      handleAutoSave();
    }, 2000); // 2 second debounce

    return () => clearTimeout(timer);
  }, [greetingScript, closingScript, transferScript, selectedVoice, autoRespond, recordCalls, autoTranscribe, enableVoicemail, configLoading, config]);

  const handleAutoSave = useCallback(async () => {
    try {
      await updateConfig({
        voiceId: selectedVoice,
        greetingScript,
        closingScript,
        transferScript,
        autoRespond,
        recordCalls,
        autoTranscribe,
        enableVoicemail,
      });
      
      setShowSavedIndicator(true);
      setTimeout(() => {
        setShowSavedIndicator(false);
      }, 2000);
    } catch (error) {
      console.error("Failed to save agent configuration:", error);
    }
  }, [selectedVoice, greetingScript, closingScript, transferScript, autoRespond, recordCalls, autoTranscribe, enableVoicemail, updateConfig]);

  const handleImproveGreeting = async () => {
    try {
      const improved = await improveScript({ script: greetingScript, scriptType: "greeting" });
      setGreetingScript(improved);
    } catch (error) {
      console.error("Failed to improve greeting script:", error);
    }
  };

  const handleImproveClosing = async () => {
    try {
      const improved = await improveScript({ script: closingScript, scriptType: "closing" });
      setClosingScript(improved);
    } catch (error) {
      console.error("Failed to improve closing script:", error);
    }
  };

  const handleImproveTransfer = async () => {
    try {
      const improved = await improveScript({ script: transferScript, scriptType: "transfer" });
      setTransferScript(improved);
    } catch (error) {
      console.error("Failed to improve transfer script:", error);
    }
  };

  const handleTestCall = async (phoneNumber: string) => {
    try {
      await testCall(phoneNumber);
      // Success message could be shown here
    } catch (error) {
      console.error("Failed to initiate test call:", error);
    }
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
        {(isUpdating || configLoading) && !showSavedIndicator && (
          <div className="text-sm text-muted-foreground">Saving...</div>
        )}
        {configError && (
          <div className="text-sm text-red-600">Failed to load configuration</div>
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
              {voicesLoading ? (
                <div className="text-sm text-muted-foreground p-4">Loading voices...</div>
              ) : (
                <VoiceLabGrid
                  voices={voiceOptions || []}
                  selectedVoice={selectedVoice}
                  onVoiceSelect={setSelectedVoice}
                />
              )}
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

