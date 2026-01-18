"use client";

/**
 * Agent Hooks
 * 
 * Custom hooks for agent configuration including fetching config,
 * updating settings, voice options, test calls, and AI script improvement.
 * 
 * @example
 * ```tsx
 * function AgentPage() {
 *   const { data: config, isLoading, error } = useAgentConfig();
 *   const { mutate: updateConfig } = useUpdateAgentConfig();
 *   const { data: voices } = useVoiceOptions();
 *   const { mutate: testCall, isCalling } = useTestCall();
 * 
 *   if (isLoading) return <LoadingSpinner />;
 *   if (error) return <ErrorMessage error={error} />;
 * 
 *   return <div>Render agent config here</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback } from "react";
import { logger } from "@/lib/logger";
import {
  fetchAgentConfig,
  updateAgentConfig,
  fetchVoiceOptions,
  initiateTestCall,
  improveScript,
  type AgentConfig,
  type VoiceOption,
} from "@/lib/api/agent";

/**
 * Hook result with loading and error states
 */
interface UseQueryResult<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Mutation result with loading and error states
 */
interface UseMutationResult<TData, TVariables> {
  mutate: (variables: TVariables) => Promise<TData>;
  isLoading: boolean;
  error: Error | null;
  reset: () => void;
}

/**
 * Hook to fetch current agent configuration
 * 
 * @returns Agent configuration with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: config, isLoading, error, refetch } = useAgentConfig();
 * ```
 */
export function useAgentConfig(): UseQueryResult<AgentConfig> {
  const [data, setData] = useState<AgentConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const config = await fetchAgentConfig();
      setData(config);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch agent config");
      setError(error);
      logger.error("Error fetching agent config", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

/**
 * Hook to update agent configuration
 * 
 * @returns Mutation function with loading and error states
 * 
 * @example
 * ```tsx
 * const { mutate: updateConfig, isLoading, error } = useUpdateAgentConfig();
 * 
 * const handleSave = () => {
 *   updateConfig({ voiceId: "2", greetingScript: "Hello!" });
 * };
 * ```
 */
export function useUpdateAgentConfig(): UseMutationResult<AgentConfig, Partial<AgentConfig>> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (config: Partial<AgentConfig>): Promise<AgentConfig> => {
    try {
      setIsLoading(true);
      setError(null);
      const updated = await updateAgentConfig(config);
      return updated;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to update agent config");
      setError(error);
      logger.error("Error updating agent config", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isLoading, error, reset };
}

/**
 * Hook to fetch available voice options
 * 
 * @returns Voice options with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: voices, isLoading, error } = useVoiceOptions();
 * ```
 */
export function useVoiceOptions(): UseQueryResult<VoiceOption[]> {
  const [data, setData] = useState<VoiceOption[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const voices = await fetchVoiceOptions();
      setData(voices);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch voice options");
      setError(error);
      logger.error("Error fetching voice options", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

/**
 * Hook to initiate a test call
 * 
 * @returns Mutation function with loading and error states
 * 
 * @example
 * ```tsx
 * const { mutate: testCall, isLoading: isCalling, error } = useTestCall();
 * 
 * const handleTestCall = () => {
 *   testCall("+1234567890");
 * };
 * ```
 */
export function useTestCall(): UseMutationResult<
  { callId: string; status: string },
  string
> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (phoneNumber: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await initiateTestCall(phoneNumber);
      return {
        callId: response.callId,
        status: response.status,
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to initiate test call");
      setError(error);
      logger.error("Error initiating test call", error, { phoneNumber });
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isLoading, error, reset };
}

/**
 * Hook to improve a script using AI
 * 
 * @returns Mutation function with loading and error states
 * 
 * @example
 * ```tsx
 * const { mutate: improveScript, isLoading, error } = useImproveScript();
 * 
 * const handleImprove = async () => {
 *   const improved = await improveScript("Hello!", "greeting");
 *   setScript(improved);
 * };
 * ```
 */
export function useImproveScript(): UseMutationResult<
  string,
  { script: string; scriptType: "greeting" | "closing" | "transfer" }
> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async ({
      script,
      scriptType,
    }: {
      script: string;
      scriptType: "greeting" | "closing" | "transfer";
    }): Promise<string> => {
      try {
        setIsLoading(true);
        setError(null);
        const improved = await improveScript(script, scriptType);
        return improved;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to improve script");
        setError(error);
        logger.error("Error improving script", error, { scriptType });
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isLoading, error, reset };
}

