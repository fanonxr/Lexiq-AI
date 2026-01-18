"use client";

import { useState, useCallback } from "react";
import { UploadZone } from "@/components/knowledge/UploadZone";
import { FileDataTable, type FileMetadata } from "@/components/knowledge/FileDataTable";
import { FileTableSkeleton } from "@/components/knowledge/FileTableSkeleton";
import { VerificationChat, type ChatMessage } from "@/components/knowledge/VerificationChat";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { FileText } from "lucide-react";
import { useFiles, useUploadFile, useDeleteFile, useReindexFile, useQueryKnowledgeBase } from "@/hooks/useKnowledgeBase";
import { logger } from "@/lib/logger";

/**
 * Knowledge Base Page
 * 
 * RAG Manager for uploading, managing, and testing knowledge base documents.
 * 
 * Layout:
 * - Single Column, Max-Width: Centered layout (like document editor)
 * - Sections (Top to Bottom):
 *   - Upload Zone
 *   - File Data Table
 *   - Verification Chat
 */
export default function KnowledgeBasePage() {
  // File management state
  const [highlightedFileId, setHighlightedFileId] = useState<string | null>(null);

  // Fetch files using hooks
  const { data: files, isLoading: isLoadingFiles, error: filesError, refetch: refetchFiles } = useFiles();
  const { mutate: uploadFile, isLoading: isUploading, progress: uploadProgress } = useUploadFile();
  const { mutate: deleteFile, isLoading: isDeleting } = useDeleteFile();
  const { mutate: reindexFile, isLoading: isReindexing } = useReindexFile();
  const { mutate: queryKB, isLoading: isQuerying } = useQueryKnowledgeBase();

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  /**
   * Handle file upload
   */
  const handleFileSelect = useCallback(async (selectedFiles: File[]) => {
    for (const file of selectedFiles) {
      try {
        await uploadFile(file, (progress) => {
          // Progress callback - can be used for UI updates if needed
          logger.debug("Upload progress", { fileName: file.name, progress });
        });
        // Refresh file list after successful upload
        await refetchFiles();
      } catch (error) {
        logger.error("Failed to upload file", error instanceof Error ? error : new Error(String(error)), { fileName: file.name });
        // Error is handled by the hook, but we could show a toast here
      }
    }
  }, [uploadFile, refetchFiles]);

  /**
   * Handle file deletion
   */
  const handleDelete = useCallback(async (fileId: string) => {
    try {
      await deleteFile(fileId);
      // Refresh file list after successful deletion
      await refetchFiles();
    } catch (error) {
      logger.error("Failed to delete file", error instanceof Error ? error : new Error(String(error)), { fileId });
      // Error is handled by the hook
    }
  }, [deleteFile, refetchFiles]);

  /**
   * Handle file re-indexing
   */
  const handleReindex = useCallback(async (fileId: string) => {
    try {
      await reindexFile(fileId);
      // Refresh file list after successful re-indexing
      await refetchFiles();
    } catch (error) {
      logger.error("Failed to re-index file", error instanceof Error ? error : new Error(String(error)), { fileId });
      // Error is handled by the hook
    }
  }, [reindexFile, refetchFiles]);

  /**
   * Handle sending a chat message
   */
  const handleSendMessage = useCallback(
    async (message: string) => {
      // Add user message
      const userMessage: ChatMessage = {
        role: "user",
        content: message,
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        // Query knowledge base via RAG
        const response = await queryKB(message);
        
        // Add assistant response
        const assistantMessage: ChatMessage = {
          role: "assistant",
          content: response.answer,
          sources: response.sources || [],
        };
        
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        logger.error("Failed to query knowledge base", error instanceof Error ? error : new Error(String(error)), { query: message });
        // Add error message
        const errorMessage: ChatMessage = {
          role: "assistant",
          content: "Sorry, I encountered an error while querying the knowledge base. Please try again.",
          sources: [],
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    },
    [queryKB]
  );

  /**
   * Handle source hover (highlight file in table)
   */
  const handleSourceHover = useCallback((sourceId: string) => {
    setHighlightedFileId(sourceId);
  }, []);

  /**
   * Handle source leave (clear highlight)
   */
  const handleSourceLeave = useCallback(() => {
    setHighlightedFileId(null);
  }, []);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Knowledge Base
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload and manage documents for your AI agent's knowledge base
        </p>
      </div>

      {/* Upload Zone */}
      <UploadZone
        onFileSelect={handleFileSelect}
        accept=".pdf"
        maxSize={10 * 1024 * 1024} // 10MB
      />

      {/* File Data Table */}
      {filesError ? (
        <ErrorState
          error={filesError}
          onRetry={refetchFiles}
          title="Failed to load files"
          inline
        />
      ) : isLoadingFiles ? (
        <FileTableSkeleton count={5} />
      ) : !files || files.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="No files uploaded"
          description="Upload PDF documents to build your knowledge base. Drag and drop files above or click to browse."
          size="default"
        />
      ) : (
        <FileDataTable
          files={files}
          onDelete={handleDelete}
          onReindex={handleReindex}
          highlightedFileId={highlightedFileId}
        />
      )}

      {/* Verification Chat */}
      <VerificationChat
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isQuerying}
        onSourceHover={handleSourceHover}
        onSourceLeave={handleSourceLeave}
      />
    </div>
  );
}

