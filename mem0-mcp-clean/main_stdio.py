#!/usr/bin/env python3
"""
Mem0 MCP Server with User Isolation - Standard I/O Version
This version uses standard input/output for MCP communication instead of HTTP.
"""

import asyncio
import json
import os
import re
import sys
from contextvars import ContextVar
from typing import Any, Sequence

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from mem0 import MemoryClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize server
server = Server("mem0-mcp-user-isolation")

# User context variable for thread-safe user isolation
current_user_id: ContextVar[str] = ContextVar('current_user_id', default="admin_default")

# Initialize mem0 client (delayed initialization)
mem0_client = None

def get_user_id_from_context() -> str:
    """Get current user ID from context"""
    return current_user_id.get()

def set_user_id_context(user_id: str) -> None:
    """Set user ID in context"""
    if user_id and re.match(r'^[a-zA-Z0-9_-]{1,64}$', user_id):
        current_user_id.set(user_id)
    else:
        print(f"Warning: Invalid user ID format: {user_id}, using default", file=sys.stderr)

def get_mem0_client():
    """Get or create mem0 client with local server support"""
    global mem0_client
    if mem0_client is None:
        # Try to use local mem0 server first
        try:
            import httpx
            # Test if local server is available
            response = httpx.get("http://localhost:8888/health", timeout=2)
            if response.status_code == 200:
                return "local"
        except:
            pass
        
        # Fallback to cloud client if available
        try:
            mem0_client = MemoryClient()
        except Exception as e:
            print(f"Warning: Could not initialize mem0 client: {e}", file=sys.stderr)
            return "local"  # Use local HTTP fallback
    
    return mem0_client

# Custom instructions for mem0 project
CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  

- Code Snippets: Save the actual code for future reference.  
- Explanation: Document a clear description of what the code does and how it works.
- Related Technical Details: Include information about the programming language, dependencies, and system specifications.  
- Key Features: Highlight the main functionalities and important aspects of the snippet.
"""

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="add_coding_preference",
            description="Add a new coding preference to mem0 with user isolation. This tool stores code snippets, implementation details, and coding patterns for future reference. Each user's data is completely isolated.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The content to store in memory, including code, documentation, and context"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID for data isolation (optional, will use context if not provided)",
                        "pattern": "^[a-zA-Z0-9_-]{1,64}$"
                    }
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="get_all_coding_preferences",
            description="Retrieve all stored coding preferences for the current user. Returns user-specific data only.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID for data isolation (optional, will use context if not provided)",
                        "pattern": "^[a-zA-Z0-9_-]{1,64}$"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="search_coding_preferences",
            description="Search through stored coding preferences using semantic search. Searches only the current user's data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string describing what you're looking for"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID for data isolation (optional, will use context if not provided)",
                        "pattern": "^[a-zA-Z0-9_-]{1,64}$"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Handle tool calls."""
    if arguments is None:
        arguments = {}
    
    # Extract user_id from arguments if provided
    user_id = arguments.get("user_id")
    if user_id:
        set_user_id_context(user_id)
    
    current_user = get_user_id_from_context()
    
    try:
        if name == "add_coding_preference":
            text = arguments.get("text", "")
            if not text:
                return [types.TextContent(type="text", text="Error: text parameter is required")]
            
            client = get_mem0_client()
            
            if client == "local":
                # Use direct HTTP request for local server
                import httpx
                response = httpx.post(
                    "http://localhost:8888/memories",
                    json={"text": text, "user_id": current_user}
                )
                response.raise_for_status()
                result = f"Successfully added preference for user {current_user}: {text[:100]}..."
            else:
                # Use cloud client
                messages = [{"role": "user", "content": text}]
                client.add(messages, user_id=current_user, output_format="v1.1")
                result = f"Successfully added preference for user {current_user}: {text[:100]}..."
            
            return [types.TextContent(type="text", text=result)]
            
        elif name == "get_all_coding_preferences":
            client = get_mem0_client()
            
            if client == "local":
                # Use direct HTTP request for local server
                import httpx
                response = httpx.get(
                    "http://localhost:8888/memories",
                    params={"user_id": current_user}
                )
                response.raise_for_status()
                memories = response.json()
                result = json.dumps(memories, indent=2)
            else:
                # Use cloud client
                memories = client.get_all(user_id=current_user, page=1, page_size=50)
                flattened_memories = [memory["memory"] for memory in memories["results"]]
                result = json.dumps(flattened_memories, indent=2)
            
            return [types.TextContent(type="text", text=result)]
            
        elif name == "search_coding_preferences":
            query = arguments.get("query", "")
            if not query:
                return [types.TextContent(type="text", text="Error: query parameter is required")]
            
            client = get_mem0_client()
            
            if client == "local":
                # Use direct HTTP request for local server
                import httpx
                response = httpx.post(
                    "http://localhost:8888/search",
                    json={"query": query, "user_id": current_user}
                )
                response.raise_for_status()
                memories = response.json()
                result = json.dumps(memories, indent=2)
            else:
                # Use cloud client
                memories = client.search(query, user_id=current_user, output_format="v1.1")
                flattened_memories = [memory["memory"] for memory in memories["results"]]
                result = json.dumps(flattened_memories, indent=2)
            
            return [types.TextContent(type="text", text=result)]
            
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        error_msg = f"Error in {name}: {str(e)}"
        print(error_msg, file=sys.stderr)
        return [types.TextContent(type="text", text=error_msg)]

async def main():
    """Main function to run the MCP server."""
    # Set default user context
    set_user_id_context("admin_default")
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mem0-mcp-user-isolation",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    print("🚀 Starting Mem0 MCP Server with User Isolation (stdio)", file=sys.stderr)
    print("🔒 User isolation enabled via context variables", file=sys.stderr)
    asyncio.run(main())
