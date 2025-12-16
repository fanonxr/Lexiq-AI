"use client";

import * as React from "react";
import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Verification Chat Component
 * 
 * Compact chat interface for testing and verifying the knowledge base.
 * Allows users to ask questions and see responses with source citations.
 * 
 * @example
 * ```tsx
 * <VerificationChat
 *   messages={messages}
 *   onSendMessage={(message) => handleSend(message)}
 *   isLoading={isLoading}
 *   onSourceHover={(sourceId) => highlightFile(sourceId)}
 * />
 * ```
 */

/**
 * Chat message
 */
export interface ChatMessage {
  /**
   * Message role (user or assistant)
   */
  role: "user" | "assistant";
  /**
   * Message content
   */
  content: string;
  /**
   * Optional source file IDs for assistant messages
   */
  sources?: string[];
}

export interface VerificationChatProps {
  /**
   * Callback when a message is sent
   */
  onSendMessage: (message: string) => void;
  /**
   * Array of chat messages
   */
  messages: ChatMessage[];
  /**
   * Whether a message is being processed
   * @default false
   */
  isLoading?: boolean;
  /**
   * Callback when hovering over a source citation
   * Used to highlight the corresponding file in the table
   */
  onSourceHover?: (sourceId: string) => void;
  /**
   * Callback when leaving a source citation
   */
  onSourceLeave?: () => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Verification Chat Component
 * 
 * Features:
 * - Compact chat interface
 * - Header: "Simulator: Ask your Knowledge Base"
 * - Input: "Ask a question about your fees..."
 * - Message history
 * - Context source highlighting (hover over answer highlights file in table)
 */
export function VerificationChat({
  onSendMessage,
  messages,
  isLoading = false,
  onSourceHover,
  onSourceLeave,
  className,
}: VerificationChatProps) {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [inputValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    onSendMessage(inputValue.trim());
    setInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSourceHover = (sourceId: string) => {
    onSourceHover?.(sourceId);
  };

  const handleSourceLeave = () => {
    onSourceLeave?.();
  };

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">
          Simulator: Ask your Knowledge Base
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4 p-4">
        {/* Message History */}
        <div
          className="flex-1 space-y-4 overflow-y-auto min-h-[200px] max-h-[400px]"
          role="log"
          aria-live="polite"
          aria-label="Chat messages"
        >
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              <p>Start a conversation to test your knowledge base</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={cn(
                  "flex gap-3",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-[80%] rounded-lg px-4 py-2 text-sm",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>

                  {/* Source citations for assistant messages */}
                  {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                    <div className="mt-2 space-y-1 border-t border-border pt-2">
                      <p className="text-xs font-medium text-muted-foreground">Sources:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.sources.map((sourceId, sourceIndex) => (
                          <button
                            key={sourceIndex}
                            className="text-xs text-primary hover:underline"
                            onMouseEnter={() => handleSourceHover(sourceId)}
                            onMouseLeave={handleSourceLeave}
                            onClick={() => handleSourceHover(sourceId)}
                          >
                            {sourceId}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {message.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-lg bg-muted px-4 py-2">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your fees..."
            disabled={isLoading}
            className="min-h-[60px] max-h-[120px] resize-none"
            rows={1}
          />
          <Button
            type="submit"
            size="icon"
            disabled={!inputValue.trim() || isLoading}
            className="h-[60px] w-[60px] shrink-0"
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

