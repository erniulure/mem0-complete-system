#!/usr/bin/env python3
"""
Remote MCP Proxy - Connects local Augment to remote MCP HTTP server
This proxy acts as a bridge between Augment's stdio MCP client and remote HTTP MCP server.
"""

import asyncio
import json
import sys
import httpx
import uuid
from typing import Any, Dict, List
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

class RemoteMCPProxy:
    def __init__(self, remote_host: str, remote_port: int, user_id: str = "admin_default"):
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.user_id = user_id
        self.base_url = f"http://{remote_host}:{remote_port}"
        self.session_id = None
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize MCP server
        self.server = Server("mem0-remote-proxy")
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools from remote server"""
            return [
                types.Tool(
                    name="add_coding_preference",
                    description="Add a new coding preference to remote mem0 server with user isolation.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The content to store in memory"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User ID for data isolation (optional)",
                                "default": self.user_id
                            }
                        },
                        "required": ["text"]
                    }
                ),
                types.Tool(
                    name="get_all_coding_preferences",
                    description="Retrieve all stored coding preferences from remote server.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID for data isolation (optional)",
                                "default": self.user_id
                            }
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="search_coding_preferences",
                    description="Search through stored coding preferences on remote server.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User ID for data isolation (optional)",
                                "default": self.user_id
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> List[types.TextContent]:
            """Forward tool calls to remote server"""
            if arguments is None:
                arguments = {}
            
            # Set default user_id if not provided
            if "user_id" not in arguments:
                arguments["user_id"] = self.user_id
            
            try:
                # Ensure we have a session
                if not self.session_id:
                    await self.establish_session()
                
                # Forward the tool call to remote server
                result = await self.call_remote_tool(name, arguments)
                return [types.TextContent(type="text", text=result)]
                
            except Exception as e:
                error_msg = f"Remote call failed for {name}: {str(e)}"
                print(f"ERROR: {error_msg}", file=sys.stderr)
                return [types.TextContent(type="text", text=error_msg)]
    
    async def establish_session(self):
        """Establish session with remote server"""
        try:
            headers = {"X-User-ID": self.user_id}
            response = await self.client.get(f"{self.base_url}/sse", headers=headers)
            
            # Extract session ID from SSE response
            if response.status_code == 200:
                # Parse the first event to get session info
                lines = response.text.split('\n')
                for line in lines:
                    if line.startswith('data: /messages/?session_id='):
                        self.session_id = line.split('session_id=')[1]
                        print(f"Established session: {self.session_id}", file=sys.stderr)
                        break
                
                if not self.session_id:
                    self.session_id = str(uuid.uuid4())
                    print(f"Generated session: {self.session_id}", file=sys.stderr)
            else:
                raise Exception(f"Failed to establish session: {response.status_code}")
                
        except Exception as e:
            print(f"Session establishment failed: {e}", file=sys.stderr)
            self.session_id = str(uuid.uuid4())
    
    async def call_remote_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call tool on remote server via HTTP"""
        try:
            # Prepare MCP message
            mcp_message = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send to remote server
            headers = {
                "Content-Type": "application/json",
                "X-User-ID": arguments.get("user_id", self.user_id)
            }
            
            url = f"{self.base_url}/messages/"
            if self.session_id:
                url += f"?session_id={self.session_id}"
            
            response = await self.client.post(url, json=mcp_message, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "content" in result["result"]:
                    content = result["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        return content[0].get("text", str(content))
                    return str(content)
                elif "error" in result:
                    return f"Remote error: {result['error']}"
                else:
                    return str(result)
            else:
                return f"HTTP error {response.status_code}: {response.text}"
                
        except Exception as e:
            return f"Request failed: {str(e)}"
    
    async def run(self):
        """Run the proxy server"""
        print(f"🌐 Starting Remote MCP Proxy", file=sys.stderr)
        print(f"📡 Connecting to: {self.base_url}", file=sys.stderr)
        print(f"👤 User ID: {self.user_id}", file=sys.stderr)
        
        # Run MCP server with stdio
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mem0-remote-proxy",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Remote MCP Proxy')
    parser.add_argument('--host', default='192.168.8.225', help='Remote server host')
    parser.add_argument('--port', type=int, default=8082, help='Remote server port')
    parser.add_argument('--user-id', default='admin_default', help='User ID for isolation')
    
    args = parser.parse_args()
    
    proxy = RemoteMCPProxy(args.host, args.port, args.user_id)
    await proxy.run()

if __name__ == "__main__":
    asyncio.run(main())
