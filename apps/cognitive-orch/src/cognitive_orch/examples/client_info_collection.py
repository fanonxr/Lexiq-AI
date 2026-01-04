"""Complete Example: Client Information Collection During Conversation

This example shows the complete flow of how the AI collects client information
during a conversation and updates the database.
"""

from typing import Optional

from cognitive_orch.services.memory_service import MemoryService
from cognitive_orch.services.prompt_builder import build_system_prompt
from cognitive_orch.services.llm_service import LLMService
from cognitive_orch.tools.client_info_tools import ClientInfoToolHandler, get_client_info_tools
from cognitive_orch.utils.logging import get_logger

logger = get_logger("client_info_collection_example")


class ConversationWithClientInfo:
    """Example conversation handler that collects client information."""

    def __init__(self):
        """Initialize services and handlers."""
        self.memory_service = MemoryService()
        self.llm_service = LLMService()
        self.tool_handler = ClientInfoToolHandler(memory_service=self.memory_service)

    async def start_conversation(
        self,
        firm_id: str,
        from_number: str,
        firm_persona: str,
    ) -> dict:
        """
        Start a conversation with automatic client info collection.
        
        Args:
            firm_id: The firm's UUID
            from_number: Caller's phone number
            firm_persona: Firm's system prompt/persona
        
        Returns:
            dict: Conversation state including client info and AI response
        """
        logger.info(f"Starting conversation for firm {firm_id} from {from_number}")

        # Step 1: Identify the client (phone only at this point)
        client = await self.memory_service.identify_client(
            firm_id=firm_id,
            phone_number=from_number
        )
        
        # Step 2: Check if we have their info already
        has_email = bool(client.email)
        has_name = bool(client.first_name and client.last_name)
        is_new_client = not has_email and not has_name

        # Step 3: Get dossier if returning client
        dossier = None
        if not is_new_client:
            dossier = await self.memory_service.get_client_dossier(client.id)

        # Step 4: Build system prompt with instructions to collect info
        system_prompt = build_system_prompt(
            firm_persona=firm_persona,
            client_dossier=dossier,
            is_new_client=is_new_client,
            include_tool_instructions=True  # Enables tools
        )

        # Step 5: Get client info tools
        tools = get_client_info_tools()

        # Step 6: Generate initial AI greeting
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        response = await self.llm_service.generate_response(
            messages=messages,
            tools=tools,  # Pass tools to LLM
        )

        return {
            "client_id": client.id,
            "is_new_client": is_new_client,
            "needs_email": not has_email,
            "needs_name": not has_name,
            "ai_greeting": response.message,
            "tools_available": True,
            "conversation_state": {
                "messages": messages,
                "tools": tools,
                "client_id": client.id,
            }
        }

    async def handle_user_message(
        self,
        conversation_state: dict,
        user_message: str,
    ) -> dict:
        """
        Handle a user message with automatic tool execution.
        
        This is where the magic happens:
        1. User says: "My name is John Smith and my email is john@example.com"
        2. AI calls: update_client_info(first_name="John", last_name="Smith", email="john@example.com")
        3. We execute the tool and update the database
        4. AI continues the conversation naturally
        
        Args:
            conversation_state: Current conversation state
            user_message: The user's message
        
        Returns:
            dict: AI response and updated state
        """
        logger.info(f"Processing user message: {user_message[:100]}...")

        # Get state
        messages = conversation_state["messages"]
        tools = conversation_state["tools"]
        client_id = conversation_state["client_id"]

        # Add user message
        messages.append({"role": "user", "content": user_message})

        # Generate AI response (may include tool calls)
        response = await self.llm_service.generate_response(
            messages=messages,
            tools=tools,
        )

        # Check if AI wants to call tools
        if response.tool_calls:
            logger.info(f"AI is calling {len(response.tool_calls)} tool(s)")
            
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response.message,
                "tool_calls": response.tool_calls
            })

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                # Execute the tool
                tool_result = await self.tool_handler.handle_tool_call(
                    tool_name=tool_name,
                    tool_arguments=tool_args,
                    client_id=client_id,
                )
                
                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result),
                })
            
            # Generate final response after tool execution
            response = await self.llm_service.generate_response(
                messages=messages,
                tools=tools,
            )

        # Add final assistant message
        messages.append({
            "role": "assistant",
            "content": response.message
        })

        return {
            "ai_response": response.message,
            "tool_calls_executed": len(response.tool_calls) if response.tool_calls else 0,
            "conversation_state": conversation_state,  # Updated with new messages
        }


# Example usage
async def example_conversation():
    """
    Demonstrate a complete conversation with client info collection.
    """
    handler = ConversationWithClientInfo()
    
    # Start conversation
    result = await handler.start_conversation(
        firm_id="firm-123",
        from_number="+15551234567",
        firm_persona="You are a friendly receptionist for Smith & Associates Law Firm."
    )
    
    print(f"AI: {result['ai_greeting']}")
    # Example output: "Hello! Thank you for calling Smith & Associates. How can I help you today?"
    
    # User provides their info
    result = await handler.handle_user_message(
        conversation_state=result['conversation_state'],
        user_message="Hi, my name is John Smith and my email is john.smith@example.com. "
                     "I need help with a divorce case."
    )
    
    print(f"AI: {result['ai_response']}")
    # Example output: "Thank you, John! I've noted your contact information. "
    #                 "I'm sorry to hear you're going through a divorce. "
    #                 "Let me connect you with one of our family law attorneys..."
    
    # Behind the scenes:
    # - AI called update_client_info(first_name="John", last_name="Smith", email="john.smith@example.com")
    # - Database was updated
    # - Next time John calls, we'll recognize him by email even if phone changed!


# Example: What the AI "sees" in the system prompt
EXAMPLE_SYSTEM_PROMPT_NEW_CLIENT = """
You are a friendly receptionist for Smith & Associates Law Firm.

---

NEW CALLER INFO:
This is the first time this person has called.

INSTRUCTION: Provide a warm, professional greeting and introduction. During the conversation:
1. Collect their full name (first and last)
2. Collect their email address (for follow-ups and documentation)
3. Ask about the nature of their legal matter

Use the update_client_info tool to store their information once collected. Be natural and conversational - don't make it feel like an interrogation.

---

TOOL USAGE INSTRUCTIONS:
You have access to the update_client_info tool for collecting client information.
Always use this tool when the client provides their name, email, or other details.
"""


# Example: What tool calls look like
EXAMPLE_TOOL_CALL = {
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "update_client_info",
        "arguments": {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example.com"
        }
    }
}


# Example: What the database update looks like
EXAMPLE_DATABASE_UPDATE = """
UPDATE clients 
SET 
    first_name = 'John',
    last_name = 'Smith', 
    email = 'john.smith@example.com'
WHERE id = 'client-uuid-123';

-- Result: Next time John calls, we can recognize him by:
-- 1. Phone: +15551234567
-- 2. Email: john.smith@example.com (even if phone changed!)
"""

