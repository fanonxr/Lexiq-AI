"""Prompt Builder Service for Dynamic System Prompt Construction.

This module provides utilities for building system prompts with optional
client context injection for personalized AI interactions.
"""

from typing import Optional

from cognitive_orch.utils.logging import get_logger

logger = get_logger("prompt_builder")


class PromptBuilder:
    """Service for building dynamic system prompts with client context.
    
    This service constructs system prompts by combining:
    - Firm-specific persona/instructions
    - Client dossier (if available)
    - Tool usage policies (if applicable)
    
    The resulting prompt enables the AI to provide personalized,
    context-aware interactions with returning callers.
    """

    def __init__(self):
        """Initialize the prompt builder service."""
        pass

    def build_system_prompt(
        self,
        firm_persona: str,
        client_dossier: Optional[str] = None,
        is_new_client: bool = False,
        include_tool_instructions: bool = False,
    ) -> str:
        """
        Build a complete system prompt with optional client context.
        
        The prompt structure is:
        1. Firm persona (core instructions)
        2. Client dossier (if returning client) OR new client instructions
        3. Tool instructions (if requested)
        
        Args:
            firm_persona: The firm's custom persona/system prompt
            client_dossier: Optional formatted client history from MemoryService
            is_new_client: Whether this is a first-time caller
            include_tool_instructions: Whether to append tool usage instructions
        
        Returns:
            str: Complete system prompt ready for LLM
        
        Example:
            >>> builder = PromptBuilder()
            >>> dossier = "- [2 days ago]: Called about divorce case..."
            >>> prompt = builder.build_system_prompt(
            ...     firm_persona="You are a receptionist for Smith & Associates...",
            ...     client_dossier=dossier
            ... )
        """
        # Start with firm persona
        prompt_parts = [firm_persona.strip()]

        # Add client context if available
        if client_dossier:
            logger.debug("Injecting client dossier into system prompt")
            prompt_parts.append(self._build_client_context_section(client_dossier))
        elif is_new_client:
            logger.debug("Injecting new client instructions into system prompt")
            prompt_parts.append(self._build_new_client_section())

        # Add tool instructions if requested
        if include_tool_instructions:
            logger.debug("Adding tool usage instructions to system prompt")
            prompt_parts.append(self._build_tool_instructions())

        # Join with double newlines for clear separation
        full_prompt = "\n\n".join(prompt_parts)
        
        logger.info(
            f"Built system prompt: {len(full_prompt)} chars, "
            f"has_dossier={client_dossier is not None}, "
            f"is_new_client={is_new_client}, "
            f"has_tools={include_tool_instructions}"
        )
        
        return full_prompt

    @staticmethod
    def _build_client_context_section(dossier: str) -> str:
        """
        Build the client recognition section of the prompt.
        
        This section informs the AI that the caller is recognized and provides
        their interaction history, with instructions on how to use this context.
        
        Args:
            dossier: Formatted client history from MemoryService.get_client_dossier()
        
        Returns:
            str: Formatted client context section
        """
        return f"""---

RECOGNIZED CALLER INFO:
{dossier}

INSTRUCTION: The caller is a known client. Use this context to personalize your greeting and responses. For example:
- Acknowledge their previous interactions naturally (e.g., "I see you called about your divorce case last week")
- Reference scheduled appointments or actions
- Show continuity and attentiveness

However, ALWAYS verify any sensitive details gently before acting on them. People's situations can change.

IMPORTANT: If you don't already have the client's full name and email, politely collect this information during the conversation.
Use the update_client_info tool to store it."""

    @staticmethod
    def _build_new_client_section() -> str:
        """
        Build the new client section for first-time callers.
        
        Returns:
            str: Instructions for handling new clients
        """
        return """---

NEW CALLER INFO:
This is the first time this person has called.

INSTRUCTION: Provide a warm, professional greeting and introduction. During the conversation:
1. Collect their full name (first and last)
2. Collect their email address (for follow-ups and documentation)
3. Ask about the nature of their legal matter

Use the update_client_info tool to store their information once collected. Be natural and conversational - don't make it feel like an interrogation."""

    @staticmethod
    def _build_tool_instructions() -> str:
        """
        Build the tool usage instructions section.
        
        This section provides guidance on when and how to use available tools
        (appointment booking, lead capture, etc.).
        
        Returns:
            str: Tool usage instructions
        """
        return """---

TOOL USAGE INSTRUCTIONS:

You have access to several tools for assisting clients:

1. **Appointment Booking**: Use when a client wants to schedule a consultation
   - Always confirm date, time, and timezone
   - Collect required contact information
   - Verify availability if possible

2. **Lead Capture**: Use when a potential client provides their information
   - Capture name, contact info, case type, and summary
   - Always ask permission before storing information

3. **Information Retrieval**: Use when you need to look up firm information
   - Search the knowledge base for accurate information
   - Never guess about legal specifics or pricing

Remember:
- Always confirm with the caller before taking actions
- Be transparent about what information you're collecting
- If unsure, offer to transfer to a human staff member"""


# Convenience function for direct usage
def build_system_prompt(
    firm_persona: str,
    client_dossier: Optional[str] = None,
    include_tool_instructions: bool = False,
) -> str:
    """
    Build a complete system prompt with optional client context.
    
    This is a convenience function that creates a PromptBuilder instance
    and calls build_system_prompt. Useful for simple invocations.
    
    Args:
        firm_persona: The firm's custom persona/system prompt
        client_dossier: Optional formatted client history from MemoryService
        include_tool_instructions: Whether to append tool usage instructions
    
    Returns:
        str: Complete system prompt ready for LLM
    
    Example:
        >>> from cognitive_orch.services.prompt_builder import build_system_prompt
        >>> dossier = await memory_service.get_client_dossier(client_id)
        >>> prompt = build_system_prompt(
        ...     firm_persona="You are a helpful receptionist...",
        ...     client_dossier=dossier
        ... )
    """
    builder = PromptBuilder()
    is_new_client = client_dossier is None
    return builder.build_system_prompt(
        firm_persona, 
        client_dossier=client_dossier, 
        is_new_client=is_new_client,
        include_tool_instructions=include_tool_instructions
    )

