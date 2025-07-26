from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
from mem0 import MemoryClient
from dotenv import load_dotenv
import json
import os
import re
from contextvars import ContextVar

load_dotenv()

# Initialize FastMCP server for mem0 tools
mcp = FastMCP("mem0-mcp-user-isolation")

# Initialize mem0 client (delayed initialization)
mem0_client = None

# User context variable for thread-safe user isolation
current_user_id: ContextVar[str] = ContextVar('current_user_id', default="admin_default")

def get_user_id_from_headers(headers):
    """Extract and validate user ID from request headers"""
    for name, value in headers:
        if name.lower() == b'x-user-id':
            user_id = value.decode('utf-8').strip()
            # Validate user ID format
            if re.match(r'^[a-zA-Z0-9_-]{1,64}$', user_id):
                return user_id
            else:
                raise ValueError(f"Invalid user ID format: {user_id}")
    return None

def get_mem0_client():
    """Get or create mem0 client with local server support"""
    global mem0_client
    if mem0_client is None:
        # Always use local HTTP mode for simplicity
        mem0_client = "local"
    return mem0_client

# Custom instructions for mem0 project
CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  

- Code Snippets: Save the actual code for future reference.  
- Explanation: Document a clear description of what the code does and how it works.
- Related Technical Details: Include information about the programming language, dependencies, and system specifications.  
- Key Features: Highlight the main functionalities and important aspects of the snippet.
"""

@mcp.tool(
    description="""Add a new coding preference to mem0 with user isolation. This tool stores code snippets, implementation details,
    and coding patterns for future reference. Each user's data is completely isolated."""
)
async def add_coding_preference(text: str) -> str:
    """Add a new coding preference to mem0 for the current user."""
    try:
        user_id = current_user_id.get()
        client = get_mem0_client()
        
        if client == "local":
            # Use direct HTTP request for local server
            import httpx
            response = httpx.post(
                "http://localhost:8888/memories",
                json={"text": text, "user_id": user_id}
            )
            response.raise_for_status()
            return f"Successfully added preference for user {user_id}: {text[:100]}..."
        else:
            # Use cloud client
            messages = [{"role": "user", "content": text}]
            client.add(messages, user_id=user_id, output_format="v1.1")
            return f"Successfully added preference for user {user_id}: {text[:100]}..."
    except Exception as e:
        return f"Error adding preference: {str(e)}"

@mcp.tool(
    description="""Retrieve all stored coding preferences for the current user. Returns user-specific data only."""
)
async def get_all_coding_preferences() -> str:
    """Get all coding preferences for the current user."""
    try:
        user_id = current_user_id.get()
        client = get_mem0_client()
        
        if client == "local":
            # Use direct HTTP request for local server
            import httpx
            response = httpx.get(
                "http://localhost:8888/memories",
                params={"user_id": user_id}
            )
            response.raise_for_status()
            memories = response.json()
            return json.dumps(memories, indent=2)
        else:
            # Use cloud client
            memories = client.get_all(user_id=user_id, page=1, page_size=50)
            flattened_memories = [memory["memory"] for memory in memories["results"]]
            return json.dumps(flattened_memories, indent=2)
    except Exception as e:
        return f"Error getting preferences: {str(e)}"

@mcp.tool(
    description="""Search through stored coding preferences using semantic search. Searches only the current user's data."""
)
async def search_coding_preferences(query: str) -> str:
    """Search coding preferences for the current user using semantic search."""
    try:
        user_id = current_user_id.get()
        client = get_mem0_client()
        
        if client == "local":
            # Use direct HTTP request for local server
            import httpx
            response = httpx.post(
                "http://localhost:8888/search",
                json={"query": query, "user_id": user_id}
            )
            response.raise_for_status()
            memories = response.json()
            return json.dumps(memories, indent=2)
        else:
            # Use cloud client
            memories = client.search(query, user_id=user_id, output_format="v1.1")
            flattened_memories = [memory["memory"] for memory in memories["results"]]
            return json.dumps(flattened_memories, indent=2)
    except Exception as e:
        return f"Error searching preferences: {str(e)}"

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        # Extract user ID from headers, query params, or path
        user_id = None
        try:
            # Try headers first
            user_id = get_user_id_from_headers(request.headers.raw)

            # Try query parameters
            if not user_id:
                user_id = request.query_params.get('user_id')

            # Try path parameters (if URL is like /user/john_doe)
            if not user_id and hasattr(request, 'path_params'):
                user_id = request.path_params.get('user_id')

            if user_id:
                current_user_id.set(user_id)
                print(f"SSE connection established for user: {user_id}")
            else:
                print("SSE connection established for default user")
        except Exception as e:
            print(f"User ID extraction failed: {e}, using default user")

        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/", endpoint=handle_sse),  # Default root path
            Route("/sse", endpoint=handle_sse),  # SSE endpoint
            Route("/user/{user_id}", endpoint=handle_sse),  # User-specific endpoint
            Route("/user/{user_id}/sse", endpoint=handle_sse),  # User-specific SSE
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    import argparse

    parser = argparse.ArgumentParser(description='Run MCP SSE-based server with user isolation')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    print(f"🚀 Starting MCP server with user isolation on {args.host}:{args.port}")
    print(f"📡 Connect to: http://{args.host}:{args.port}/sse")
    print(f"🔒 Remember to include X-User-ID header!")

    uvicorn.run(starlette_app, host=args.host, port=args.port)
