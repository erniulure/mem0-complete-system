from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
import httpx
from dotenv import load_dotenv
import json
import os

load_dotenv()

# Initialize FastMCP server for mem0 tools
mcp = FastMCP("mem0-mcp")

# HTTP client for our deployed Mem0 API
class Mem0HTTPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)

    async def add(self, messages, user_id: str, output_format: str = "v1.1"):
        url = f"{self.base_url}/memories"
        payload = {"messages": messages, "user_id": user_id}
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def get_all(self, user_id: str, page: int = 1, page_size: int = 50):
        url = f"{self.base_url}/memories"
        params = {"user_id": user_id}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def search(self, query: str, user_id: str, output_format: str = "v1.1"):
        url = f"{self.base_url}/search"
        payload = {"query": query, "user_id": user_id}
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def update_project(self, custom_instructions: str):
        # This is a no-op for HTTP client
        pass

# Initialize mem0 HTTP client and set default user
mem0_api_url = os.getenv('MEM0_API_URL', 'http://localhost:8888')
mem0_client = Mem0HTTPClient(mem0_api_url)
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "admin_default")
CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  

- Code Snippets: Save the actual code for future reference.  
- Explanation: Document a clear description of what the code does and how it works.
- Related Technical Details: Include information about the programming language, dependencies, and system specifications.  
- Key Features: Highlight the main functionalities and important aspects of the snippet.
"""
mem0_client.update_project(custom_instructions=CUSTOM_INSTRUCTIONS)

@mcp.tool(
    description="""Add a new coding preference to mem0. This tool stores code snippets, implementation details,
    and coding patterns for future reference. Store every code snippet. When storing code, you should include:
    - Complete code with all necessary imports and dependencies
    - Language/framework version information (e.g., "Python 3.9", "React 18")
    - Full implementation context and any required setup/configuration
    - Detailed comments explaining the logic, especially for complex sections
    - Example usage or test cases demonstrating the code
    - Any known limitations, edge cases, or performance considerations
    - Related patterns or alternative approaches
    - Links to relevant documentation or resources
    - Environment setup requirements (if applicable)
    - Error handling and debugging tips
    The preference will be indexed for semantic search and can be retrieved later using natural language queries."""
)
async def add_coding_preference(text: str) -> str:
    """Add a new coding preference to mem0.

    This tool is designed to store code snippets, implementation patterns, and programming knowledge.
    When storing code, it's recommended to include:
    - Complete code with imports and dependencies
    - Language/framework information
    - Setup instructions if needed
    - Documentation and comments
    - Example usage

    Args:
        text: The content to store in memory, including code, documentation, and context
    """
    try:
        messages = [{"role": "user", "content": text}]
        await mem0_client.add(messages, user_id=DEFAULT_USER_ID, output_format="v1.1")
        return f"Successfully added preference: {text}"
    except Exception as e:
        return f"Error adding preference: {str(e)}"

@mcp.tool(
    description="""Retrieve all stored coding preferences for the default user. Call this tool when you need 
    complete context of all previously stored preferences. This is useful when:
    - You need to analyze all available code patterns
    - You want to check all stored implementation examples
    - You need to review the full history of stored solutions
    - You want to ensure no relevant information is missed
    Returns a comprehensive list of:
    - Code snippets and implementation patterns
    - Programming knowledge and best practices
    - Technical documentation and examples
    - Setup and configuration guides
    Results are returned in JSON format with metadata."""
)
async def get_all_coding_preferences() -> str:
    """Get all coding preferences for the default user.

    Returns a JSON formatted list of all stored preferences, including:
    - Code implementations and patterns
    - Technical documentation
    - Programming best practices
    - Setup guides and examples
    Each preference includes metadata about when it was created and its content type.
    """
    try:
        memories = await mem0_client.get_all(user_id=DEFAULT_USER_ID, page=1, page_size=50)
        # Handle the nested results structure: {"results": {"results": [], "relations": []}}
        results = memories.get("results", {}).get("results", [])
        flattened_memories = [memory.get("memory", memory) for memory in results]
        return json.dumps(flattened_memories, indent=2)
    except Exception as e:
        return f"Error getting preferences: {str(e)}"

@mcp.tool(
    description="""Search through stored coding preferences using semantic search. This tool should be called 
    for EVERY user query to find relevant code and implementation details. It helps find:
    - Specific code implementations or patterns
    - Solutions to programming problems
    - Best practices and coding standards
    - Setup and configuration guides
    - Technical documentation and examples
    The search uses natural language understanding to find relevant matches, so you can
    describe what you're looking for in plain English. Always search the preferences before 
    providing answers to ensure you leverage existing knowledge."""
)
async def search_coding_preferences(query: str) -> str:
    """Search coding preferences using semantic search.

    The search is powered by natural language understanding, allowing you to find:
    - Code implementations and patterns
    - Programming solutions and techniques
    - Technical documentation and guides
    - Best practices and standards
    Results are ranked by relevance to your query.

    Args:
        query: Search query string describing what you're looking for. Can be natural language
              or specific technical terms.
    """
    try:
        memories = await mem0_client.search(query, user_id=DEFAULT_USER_ID, output_format="v1.1")
        # Handle the nested results structure: {"results": {"results": [], "relations": []}}
        results = memories.get("results", {}).get("results", [])
        flattened_memories = [memory.get("memory", memory) for memory in results]
        return json.dumps(flattened_memories, indent=2)
    except Exception as e:
        return f"Error searching preferences: {str(e)}"

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
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
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server
    transport_mode = os.getenv('TRANSPORT', 'sse')

    if transport_mode == 'stdio':
        # Stdio mode - for direct JSON configuration
        import asyncio
        from mcp.server.stdio import stdio_server

        async def main():
            async with stdio_server() as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )

        asyncio.run(main())
    else:
        # SSE mode - for web-based transport
        import argparse

        parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
        parser.add_argument('--host', default=os.getenv('HOST', '0.0.0.0'), help='Host to bind to')
        parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8051')), help='Port to listen on')
        args = parser.parse_args()

        # Bind SSE request handling to MCP server
        starlette_app = create_starlette_app(mcp_server, debug=True)

        uvicorn.run(starlette_app, host=args.host, port=args.port)
