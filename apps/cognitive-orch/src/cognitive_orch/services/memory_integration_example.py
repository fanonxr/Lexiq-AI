"""Example Integration: Long-Term Memory in gRPC Handler

This file demonstrates how to integrate the Long-Term Memory feature
into the cognitive orchestrator's gRPC conversation handler.

This is example code for reference - adapt to your actual gRPC handler.
"""

from typing import Optional

from cognitive_orch.services.memory_service import MemoryService
from cognitive_orch.services.prompt_builder import build_system_prompt
from cognitive_orch.services.prompt_service import PromptService
from cognitive_orch.services.llm_service import LLMService
from cognitive_orch.utils.logging import get_logger

logger = get_logger("memory_integration_example")


class ConversationHandlerWithMemory:
    """Example conversation handler with Long-Term Memory integration."""

    def __init__(self):
        """Initialize services."""
        self.memory_service = MemoryService()
        self.prompt_service = PromptService()
        self.llm_service = LLMService()

    async def handle_inbound_call(
        self,
        firm_id: str,
        from_number: str,
        initial_message: Optional[str] = None,
    ) -> dict:
        """
        Handle an inbound call with client memory recognition.

        Args:
            firm_id: The firm receiving the call
            from_number: Caller's phone number
            initial_message: Optional initial user message

        Returns:
            dict: Response with AI greeting and client context
        """
        logger.info(f"Handling call for firm {firm_id} from {from_number}")

        try:
            # Step 1: Identify the client
            client = await self.memory_service.identify_client(firm_id, from_number)
            is_returning = bool(client.last_called_at)
            logger.info(
                f"Client identified: {client.id}, returning={is_returning}"
            )

            # Step 2: Get client dossier (if returning client)
            dossier = None
            if is_returning:
                dossier = await self.memory_service.get_client_dossier(
                    client.id, max_memories=3
                )
                if dossier:
                    logger.info(
                        f"Retrieved dossier for client {client.id} "
                        f"({len(dossier)} chars)"
                    )

            # Step 3: Get firm persona
            firm_persona = await self.prompt_service.get_firm_persona(firm_id)

            # Step 4: Build system prompt with client context
            system_prompt = build_system_prompt(
                firm_persona=firm_persona,
                client_dossier=dossier,
                include_tool_instructions=True,
            )

            # Step 5: Generate AI greeting
            messages = [
                {"role": "system", "content": system_prompt},
            ]

            if initial_message:
                messages.append({"role": "user", "content": initial_message})

            response = await self.llm_service.generate_response(messages=messages)

            # Return response with metadata
            return {
                "client_id": client.id,
                "is_returning_client": is_returning,
                "has_dossier": dossier is not None,
                "ai_response": response.message,
                "system_prompt_length": len(system_prompt),
            }

        except Exception as e:
            logger.error(f"Error handling call: {e}", exc_info=True)
            raise

    async def handle_message_in_conversation(
        self,
        conversation_id: str,
        client_id: str,
        user_message: str,
        conversation_history: list,
    ) -> dict:
        """
        Handle a message within an ongoing conversation.

        Args:
            conversation_id: Unique conversation ID
            client_id: Client UUID
            user_message: The user's message
            conversation_history: List of previous messages

        Returns:
            dict: AI response
        """
        logger.info(f"Processing message in conversation {conversation_id}")

        try:
            # The system prompt with client context should already be
            # the first message in conversation_history from handle_inbound_call
            # Just append the new user message and generate response

            conversation_history.append({"role": "user", "content": user_message})

            response = await self.llm_service.generate_response(
                messages=conversation_history
            )

            return {
                "conversation_id": conversation_id,
                "ai_response": response.message,
                "tokens_used": response.usage.total_tokens,
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise

    async def handle_call_ended(
        self,
        conversation_id: str,
        client_id: str,
        transcript: str,
    ) -> dict:
        """
        Handle call completion and generate memory.

        This should be called asynchronously after the call ends
        (e.g., from a background worker, webhook handler, or event listener).

        Args:
            conversation_id: Unique conversation ID
            client_id: Client UUID
            transcript: Full conversation transcript

        Returns:
            dict: Summary and storage status
        """
        logger.info(
            f"Processing call end for conversation {conversation_id}, "
            f"client {client_id}"
        )

        try:
            # Import here to avoid circular dependency
            from cognitive_orch.services.post_call_worker import generate_memory

            # Generate and store memory
            summary = await generate_memory(
                call_transcript=transcript,
                client_id=client_id,
                include_embedding=True,
            )

            logger.info(f"Memory generated for client {client_id}: {summary[:100]}...")

            return {
                "conversation_id": conversation_id,
                "client_id": client_id,
                "summary": summary,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error generating memory: {e}", exc_info=True)
            return {
                "conversation_id": conversation_id,
                "client_id": client_id,
                "status": "failed",
                "error": str(e),
            }


# Example usage in gRPC handler
async def example_grpc_handler(request):
    """
    Example gRPC handler showing how to integrate memory service.

    This is pseudocode - adapt to your actual gRPC proto definitions.
    """
    handler = ConversationHandlerWithMemory()

    # Handle new conversation
    if request.message_type == "start_conversation":
        result = await handler.handle_inbound_call(
            firm_id=request.firm_id,
            from_number=request.from_number,
            initial_message=request.initial_message,
        )
        return result

    # Handle message in ongoing conversation
    elif request.message_type == "user_message":
        result = await handler.handle_message_in_conversation(
            conversation_id=request.conversation_id,
            client_id=request.client_id,
            user_message=request.message,
            conversation_history=request.history,
        )
        return result

    # Handle call completion
    elif request.message_type == "end_conversation":
        # This should ideally be async/background processing
        result = await handler.handle_call_ended(
            conversation_id=request.conversation_id,
            client_id=request.client_id,
            transcript=request.transcript,
        )
        return result

