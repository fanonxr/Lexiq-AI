"""Conversation state models for managing conversation history and metadata."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Individual message in a conversation."""

    role: str = Field(..., description="Message role: user, assistant, system, or tool")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    tool_calls: Optional[List[Dict]] = Field(
        default=None, description="Tool calls made in this message (for assistant messages)"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="Tool call ID (for tool messages)"
    )
    model: Optional[str] = Field(
        default=None, description="Model used to generate this message"
    )
    tokens: Optional[int] = Field(
        default=None, description="Token count for this message"
    )


class ConversationMetadata(BaseModel):
    """Metadata about a conversation."""

    firm_id: Optional[str] = Field(default=None, description="Firm/Organization ID")
    user_id: str = Field(..., description="User ID")
    call_id: Optional[str] = Field(default=None, description="Call ID (if from voice call)")
    model_used: Optional[str] = Field(
        default=None, description="Primary model used in this conversation"
    )
    total_tokens: int = Field(default=0, description="Total tokens used in conversation")
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Conversation start time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )


class ConversationState(BaseModel):
    """Complete conversation state including messages and metadata."""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    messages: List[Message] = Field(
        default_factory=list, description="Conversation message history"
    )
    metadata: ConversationMetadata = Field(..., description="Conversation metadata")
    tool_execution_history: List[Dict] = Field(
        default_factory=list, description="History of tool executions"
    )

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        model: Optional[str] = None,
        tokens: Optional[int] = None,
    ) -> None:
        """Add a message to the conversation."""
        message = Message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            model=model,
            tokens=tokens,
        )
        self.messages.append(message)
        self.metadata.updated_at = datetime.utcnow()

    def get_messages_for_llm(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """Get messages formatted for LLM API (role and content only).
        
        Args:
            max_messages: Maximum number of messages to return (truncates from oldest).
                          If None, returns all messages.
        
        Returns:
            List of message dictionaries with 'role' and 'content' keys.
        """
        messages = self.messages
        if max_messages and len(messages) > max_messages:
            # Keep the most recent messages
            messages = messages[-max_messages:]
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]

    def truncate_old_messages(self, max_messages: int) -> int:
        """Truncate old messages, keeping only the most recent ones.
        
        Args:
            max_messages: Maximum number of messages to keep.
        
        Returns:
            Number of messages removed.
        """
        if len(self.messages) <= max_messages:
            return 0
        
        removed_count = len(self.messages) - max_messages
        self.messages = self.messages[-max_messages:]
        self.metadata.updated_at = datetime.utcnow()
        
        return removed_count

    def add_tool_execution(self, tool_name: str, parameters: Dict, result: Dict) -> None:
        """Add a tool execution to the history."""
        execution = {
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.tool_execution_history.append(execution)
        self.metadata.updated_at = datetime.utcnow()

    def model_dump_json(self, **kwargs) -> str:
        """Serialize to JSON with proper datetime handling."""
        # Pydantic v2 handles datetime serialization automatically in mode="json"
        return super().model_dump_json(mode="json", **kwargs)

