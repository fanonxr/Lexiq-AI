"""Client Information Management Tools for LLM Function Calling.

This module provides tool definitions and handlers that allow the LLM to
collect and update client information during conversations.

These tools are exposed to the AI through function calling (OpenAI format).
"""

from typing import Optional

from cognitive_orch.services.memory_service import MemoryService
from cognitive_orch.utils.logging import get_logger

logger = get_logger("client_info_tools")


# Tool definitions in OpenAI function calling format
CLIENT_INFO_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_client_info",
            "description": "Update the client's contact information and personal details. Use this when the client provides their name, email, or other identifying information during the conversation. This helps us maintain accurate records and follow up with them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {
                        "type": "string",
                        "description": "The client's first name (e.g., 'John')"
                    },
                    "last_name": {
                        "type": "string",
                        "description": "The client's last name (e.g., 'Smith')"
                    },
                    "email": {
                        "type": "string",
                        "description": "The client's email address (e.g., 'john.smith@example.com')"
                    },
                    "external_crm_id": {
                        "type": "string",
                        "description": "External CRM/system identifier if provided (optional)"
                    }
                },
                "required": []  # All fields are optional - update what you have
            }
        }
    }
]


class ClientInfoToolHandler:
    """Handler for client information management tools.
    
    This class processes tool calls from the LLM and executes the
    corresponding database operations.
    """

    def __init__(self, memory_service: Optional[MemoryService] = None):
        """
        Initialize the tool handler.
        
        Args:
            memory_service: Optional MemoryService instance. If not provided,
                          a new instance will be created.
        """
        self.memory_service = memory_service or MemoryService()

    async def handle_tool_call(
        self,
        tool_name: str,
        tool_arguments: dict,
        client_id: str,
    ) -> dict:
        """
        Handle a tool call from the LLM.
        
        Args:
            tool_name: Name of the tool being called
            tool_arguments: Arguments passed to the tool
            client_id: The current client's UUID
        
        Returns:
            dict: Result of the tool execution
        
        Raises:
            ValueError: If tool_name is not recognized
        """
        if tool_name == "update_client_info":
            return await self._handle_update_client_info(tool_arguments, client_id)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _handle_update_client_info(
        self,
        arguments: dict,
        client_id: str,
    ) -> dict:
        """
        Handle the update_client_info tool call.
        
        Args:
            arguments: Tool arguments containing client info to update
            client_id: The client's UUID
        
        Returns:
            dict: Success message and updated fields
        """
        try:
            # Extract arguments
            first_name = arguments.get("first_name")
            last_name = arguments.get("last_name")
            email = arguments.get("email")
            external_crm_id = arguments.get("external_crm_id")

            # Update client info
            await self.memory_service.update_client_info(
                client_id=client_id,
                email=email,
                external_crm_id=external_crm_id,
                first_name=first_name,
                last_name=last_name,
            )

            # Build response
            updated_fields = []
            if first_name or last_name:
                name = f"{first_name or ''} {last_name or ''}".strip()
                updated_fields.append(f"name: {name}")
            if email:
                updated_fields.append(f"email: {email}")
            if external_crm_id:
                updated_fields.append(f"CRM ID: {external_crm_id}")

            logger.info(
                f"Successfully updated client {client_id} with: {', '.join(updated_fields)}"
            )

            return {
                "success": True,
                "message": f"Successfully updated client information: {', '.join(updated_fields)}",
                "updated_fields": updated_fields,
            }

        except Exception as e:
            logger.error(f"Error updating client info: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to update client information: {str(e)}",
                "error": str(e),
            }


# Convenience function for getting tools
def get_client_info_tools() -> list:
    """
    Get the list of client information management tools.
    
    Returns:
        list: Tool definitions in OpenAI function calling format
    """
    return CLIENT_INFO_TOOLS

