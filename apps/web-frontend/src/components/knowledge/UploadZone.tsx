"use client";

import * as React from "react";
import { useState, useRef, useCallback, useEffect } from "react";
import { Cloud, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";

/**
 * Upload Zone Component
 * 
 * Drag-and-drop file upload zone with click-to-browse functionality.
 * Used for uploading PDFs and other documents to the knowledge base.
 * 
 * @example
 * ```tsx
 * <UploadZone
 *   onFileSelect={(files) => handleFiles(files)}
 *   accept=".pdf"
 *   maxSize={10 * 1024 * 1024} // 10MB
 * />
 * ```
 */

export interface UploadZoneProps {
  /**
   * Callback when files are selected
   */
  onFileSelect: (files: File[]) => void;
  /**
   * Accepted file types (MIME types or extensions)
   * @default ".pdf"
   */
  accept?: string;
  /**
   * Maximum file size in bytes
   */
  maxSize?: number;
  /**
   * Whether multiple files can be selected
   * @default true
   */
  multiple?: boolean;
  /**
   * Upload progress (0-100). When provided, shows progress bar instead of upload zone
   */
  progress?: number;
  /**
   * Whether upload is in progress
   */
  isUploading?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Upload Zone Component
 * 
 * Features:
 * - Large dashed border zone
 * - Empty state: Cloud icon + "Drag PDF here or click to browse"
 * - Active drag state: Blue border and background tint
 * - File input (hidden)
 * - Click to browse functionality
 */
export function UploadZone({
  onFileSelect,
  accept = ".pdf",
  maxSize,
  multiple = true,
  progress,
  isUploading: externalIsUploading,
  className,
}: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [internalProgress, setInternalProgress] = useState<number | undefined>(undefined);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Use external progress if provided, otherwise use internal
  const uploadProgress = progress !== undefined ? progress : internalProgress;
  const isUploading = externalIsUploading !== undefined ? externalIsUploading : uploadProgress !== undefined;

  /**
   * Validate file size
   */
  const validateFileSize = useCallback(
    (file: File): boolean => {
      if (maxSize && file.size > maxSize) {
        return false;
      }
      return true;
    },
    [maxSize]
  );

  /**
   * Process selected files
   */
  const processFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;

      const fileArray = Array.from(files);
      const validFiles: File[] = [];

      for (const file of fileArray) {
        if (maxSize && !validateFileSize(file)) {
          console.warn(`File ${file.name} exceeds maximum size of ${maxSize} bytes`);
          continue;
        }
        validFiles.push(file);
      }

      if (validFiles.length > 0) {
        // Start upload progress simulation if not provided externally
        if (progress === undefined) {
          setInternalProgress(0);
          // Simulate progress (in real implementation, this would come from upload API)
          let currentProgress = 0;
          const interval = setInterval(() => {
            currentProgress += 10;
            if (currentProgress >= 100) {
              clearInterval(interval);
              setTimeout(() => {
                setInternalProgress(undefined);
              }, 500);
            } else {
              setInternalProgress(currentProgress);
            }
          }, 200);
        }
        onFileSelect(validFiles);
      }
    },
    [onFileSelect, maxSize, validateFileSize, progress]
  );

  /**
   * Handle drag events
   */
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      processFiles(files);
    },
    [processFiles]
  );

  /**
   * Handle file input change
   */
  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      processFiles(files);
      // Reset input so same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [processFiles]
  );

  /**
   * Handle click to browse
   */
  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // Show progress bar when uploading
  if (isUploading && uploadProgress !== undefined) {
    return (
      <div
        className={cn(
          "relative rounded-lg border-2 border-solid transition-all duration-300",
          "border-primary bg-primary/5 dark:border-primary dark:bg-primary/10",
          className
        )}
      >
        <div className="flex flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Upload className="h-6 w-6 animate-pulse" />
          </div>
          <div className="w-full space-y-2">
            <p className="text-sm font-medium text-foreground">
              Uploading... {uploadProgress}%
            </p>
            <Progress 
              value={uploadProgress} 
              className="h-2 w-full transition-all duration-300 ease-in-out"
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "relative rounded-lg border-2 border-dashed transition-all duration-300",
        // Base state
        "border-zinc-200 bg-zinc-50/50 dark:border-zinc-800 dark:bg-zinc-900/50",
        // Active drag state: Blue border and background tint
        isDragging && "border-primary bg-primary/5",
        // Hover state
        !isDragging && "hover:border-zinc-300 hover:bg-zinc-100/50 dark:hover:border-zinc-700 dark:hover:bg-zinc-800/50",
        // Cursor
        "cursor-pointer",
        className
      )}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-label="Upload files"
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileInputChange}
        className="hidden"
        aria-label="File input"
      />

      {/* Content */}
      <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
        {/* Icon */}
        <div
          className={cn(
            "flex h-16 w-16 items-center justify-center rounded-full transition-colors",
            isDragging
              ? "bg-primary/10 text-primary"
              : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-600"
          )}
        >
          {isDragging ? (
            <Upload className="h-8 w-8" />
          ) : (
            <Cloud className="h-8 w-8" />
          )}
        </div>

        {/* Text */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">
            {isDragging ? "Drop files here" : "Drag PDF here or click to browse"}
          </p>
          {accept && (
            <p className="text-xs text-muted-foreground">
              Accepted: {accept}
              {maxSize && ` (Max ${(maxSize / (1024 * 1024)).toFixed(0)}MB)`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

