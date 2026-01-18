"use client";

/**
 * Knowledge Base Hooks
 * 
 * Custom hooks for knowledge base management including file operations,
 * uploads with progress tracking, and RAG querying.
 * 
 * @example
 * ```tsx
 * function KnowledgeBasePage() {
 *   const { data: files, isLoading, error } = useFiles();
 *   const { mutate: uploadFile, isLoading: isUploading, progress } = useUploadFile();
 *   const { mutate: deleteFile } = useDeleteFile();
 *   const { mutate: queryKB, isLoading: isQuerying } = useQueryKnowledgeBase();
 * 
 *   if (isLoading) return <LoadingSpinner />;
 *   if (error) return <ErrorMessage error={error} />;
 * 
 *   return <div>render knowledge base</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { logger } from "@/lib/logger";
import {
  fetchFiles,
  uploadFile,
  deleteFile,
  reindexFile,
  queryKnowledgeBase,
  getFileStatus,
  type FileMetadata,
  type QueryKnowledgeBaseResponse,
  type FileStatusResponse,
} from "@/lib/api/knowledge";
import type { ChatMessage } from "@/components/knowledge/VerificationChat";

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
 * Upload mutation result with progress tracking
 */
interface UseUploadFileResult {
  mutate: (file: File, onProgress?: (progress: number) => void) => Promise<FileMetadata>;
  isLoading: boolean;
  progress: number;
  error: Error | null;
  reset: () => void;
}

/**
 * Hook to fetch indexed files
 * 
 * @returns Files with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: files, isLoading, error, refetch } = useFiles();
 * ```
 */
export function useFiles(): UseQueryResult<FileMetadata[]> {
  const [data, setData] = useState<FileMetadata[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const files = await fetchFiles();
      setData(files);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch files");
      setError(error);
      logger.error("Error fetching files", error);
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
 * Hook to upload a file with progress tracking
 * 
 * @returns Upload mutation with progress tracking
 * 
 * @example
 * ```tsx
 * const { mutate: uploadFile, isLoading, progress } = useUploadFile();
 * 
 * const handleUpload = (file: File) => {
 *   uploadFile(file, (progress) => {
 *     logger.debug(`Upload progress: ${progress}%`);
 *   });
 * };
 * ```
 */
export function useUploadFile(): UseUploadFileResult {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (file: File, onProgress?: (progress: number) => void): Promise<FileMetadata> => {
      try {
        setIsLoading(true);
        setProgress(0);
        setError(null);

        // Simulate progress for now (in production, this would come from the upload)
        const progressInterval = setInterval(() => {
          setProgress((prev) => {
            const newProgress = Math.min(prev + 10, 90);
            onProgress?.(newProgress);
            return newProgress;
          });
        }, 200);

        const uploadedFile = await uploadFile(file, (prog) => {
          setProgress(prog);
          onProgress?.(prog);
        });

        clearInterval(progressInterval);
        setProgress(100);
        onProgress?.(100);

        return uploadedFile;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to upload file");
        setError(error);
        logger.error("Error uploading file", error, { fileName: file.name });
        throw error;
      } finally {
        setIsLoading(false);
        // Reset progress after a delay
        setTimeout(() => setProgress(0), 1000);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setError(null);
    setProgress(0);
  }, []);

  return { mutate, isLoading, progress, error, reset };
}

/**
 * Hook to delete a file
 * 
 * @returns Delete mutation
 * 
 * @example
 * ```tsx
 * const { mutate: deleteFile, isLoading } = useDeleteFile();
 * 
 * const handleDelete = (fileId: string) => {
 *   deleteFile(fileId);
 * };
 * ```
 */
export function useDeleteFile(): UseMutationResult<boolean, string> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (fileId: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await deleteFile(fileId);
      return response.success;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to delete file");
      setError(error);
      logger.error("Error deleting file", error, { fileId });
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
 * Hook to re-index a file
 * 
 * @returns Re-index mutation
 * 
 * @example
 * ```tsx
 * const { mutate: reindexFile, isLoading } = useReindexFile();
 * 
 * const handleReindex = (fileId: string) => {
 *   reindexFile(fileId);
 * };
 * ```
 */
export function useReindexFile(): UseMutationResult<FileMetadata, string> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (fileId: string): Promise<FileMetadata> => {
    try {
      setIsLoading(true);
      setError(null);
      const file = await reindexFile(fileId);
      return file;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to re-index file");
      setError(error);
      logger.error("Error re-indexing file", error, { fileId });
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
 * Hook to query the knowledge base (RAG system)
 * 
 * @returns Query mutation
 * 
 * @example
 * ```tsx
 * const { mutate: queryKB, isLoading } = useQueryKnowledgeBase();
 * 
 * const handleQuery = async (query: string) => {
 *   const response = await queryKB(query);
 *   logger.debug("Query response", { answer: response.answer, sources: response.sources });
 * };
 * ```
 */
export function useQueryKnowledgeBase(): UseMutationResult<
  QueryKnowledgeBaseResponse,
  string
> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (query: string): Promise<QueryKnowledgeBaseResponse> => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await queryKnowledgeBase(query);
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to query knowledge base");
        setError(error);
        logger.error("Error querying knowledge base", error, { query });
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

/**
 * Hook to poll for file processing status
 * 
 * @param fileId - File ID to poll
 * @param enabled - Whether to enable polling
 * @param interval - Polling interval in milliseconds
 * @returns File status with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: status, isLoading } = useFileStatus(fileId, true, 2000);
 * ```
 */
export function useFileStatus(
  fileId: string | null,
  enabled: boolean = true,
  interval: number = 2000
): UseQueryResult<FileStatusResponse> {
  const [data, setData] = useState<FileStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const refetch = useCallback(async () => {
    if (!fileId || !enabled) return;

    try {
      setIsLoading(true);
      setError(null);
      const status = await getFileStatus(fileId);
      setData(status);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch file status");
      setError(error);
      logger.error("Error fetching file status", error, { fileId });
    } finally {
      setIsLoading(false);
    }
  }, [fileId, enabled]);

  useEffect(() => {
    if (!fileId || !enabled) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Initial fetch
    refetch();

    // Set up polling
    intervalRef.current = setInterval(() => {
      refetch();
    }, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fileId, enabled, interval, refetch]);

  return { data, isLoading, error, refetch };
}

