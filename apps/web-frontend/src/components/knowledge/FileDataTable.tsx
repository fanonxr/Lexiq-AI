"use client";

import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2, RotateCcw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

/**
 * File Data Table Component
 * 
 * Dense table displaying uploaded files with status, metadata, and actions.
 * Used in the Knowledge Base (RAG Manager) page.
 * 
 * @example
 * ```tsx
 * <FileDataTable
 *   files={files}
 *   onDelete={(fileId) => handleDelete(fileId)}
 *   onReindex={(fileId) => handleReindex(fileId)}
 * />
 * ```
 */

/**
 * File status type
 */
export type FileStatus = "processing" | "ready" | "error";

/**
 * File metadata
 */
export interface FileMetadata {
  /**
   * Unique file identifier
   */
  id: string;
  /**
   * File name
   */
  name: string;
  /**
   * Upload date
   */
  date: Date;
  /**
   * File size in bytes
   */
  size: number;
  /**
   * Processing status
   */
  status: FileStatus;
  /**
   * Optional error message
   */
  error?: string;
}

export interface FileDataTableProps {
  /**
   * Array of file metadata
   */
  files: FileMetadata[];
  /**
   * Callback when delete action is clicked
   */
  onDelete?: (fileId: string) => void;
  /**
   * Callback when re-index action is clicked
   */
  onReindex?: (fileId: string) => void;
  /**
   * File ID to highlight (e.g., when hovering over source in chat)
   */
  highlightedFileId?: string | null;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Format file size to human-readable string
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Get status badge component
 */
function getStatusBadge(status: FileStatus) {
  switch (status) {
    case "processing":
      return (
        <Badge status="warning" className="gap-1.5">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </Badge>
      );
    case "ready":
      return (
        <Badge status="success">
          Indexed
        </Badge>
      );
    case "error":
      return (
        <Badge status="error">
          Error
        </Badge>
      );
    default:
      return null;
  }
}

/**
 * File Data Table Component
 * 
 * Features:
 * - Dense table with columns: File Name, Date, Size, Status
 * - Status badges:
 *   - Processing: Yellow badge with spinning loader
 *   - Ready: Green badge "Indexed"
 * - Row actions (delete, re-index)
 */
export function FileDataTable({
  files,
  onDelete,
  onReindex,
  highlightedFileId,
  className,
}: FileDataTableProps) {
  if (files.length === 0) {
    return (
      <div className={cn("rounded-lg border border-zinc-200 bg-white p-8 text-center dark:border-zinc-800 dark:bg-zinc-900", className)}>
        <p className="text-sm text-muted-foreground">
          No files uploaded yet. Upload files to get started.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>File Name</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {files.map((file) => (
            <TableRow
              key={file.id}
              className={cn(
                highlightedFileId === file.id && "bg-primary/5 border-primary/20"
              )}
            >
              <TableCell className="font-medium">{file.name}</TableCell>
              <TableCell className="text-muted-foreground">
                {formatDistanceToNow(file.date, { addSuffix: true })}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatFileSize(file.size)}
              </TableCell>
              <TableCell>
                {getStatusBadge(file.status)}
              </TableCell>
              <TableCell className="text-right">
                <div
                  className="flex items-center justify-end gap-2"
                  role="group"
                  aria-label={`Actions for ${file.name}`}
                >
                  {file.status === "ready" && onReindex && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => onReindex(file.id)}
                      aria-label={`Re-index ${file.name}`}
                      title="Re-index"
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => onDelete(file.id)}
                      aria-label={`Delete ${file.name}`}
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

