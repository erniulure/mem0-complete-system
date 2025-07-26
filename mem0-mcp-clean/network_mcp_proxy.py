#!/usr/bin/env python3
"""
Network MCP Proxy - Provides MCP over HTTP for remote Augment clients
This allows Augment on remote machines to connect via HTTP to access local MCP services.
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

class NetworkMCPProxy:
    def __init__(self, remote_host: str, remote_port: int):
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.base_url = f"http://{remote_host}:{remote_port}"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.sessions = {}  # Store session info per user
    
    async def get_user_session(self, user_id: str):
        """Get or create session for user"""
        if user_id not in self.sessions:
            try:
                headers = {"X-User-ID": user_id}
                response = await self.client.get(f"{self.base_url}/sse", headers=headers)
                
                session_id = None
                if response.status_code == 200:
                    # Extract session ID from SSE response
                    lines = response.text.split('\n')
                    for line in lines:
                        if line.startswith('data: /messages/?session_id='):
                            session_id = line.split('session_id=')[1]
                            break
                
                if not session_id:
                    session_id = str(uuid.uuid4())
                
                self.sessions[user_id] = {
                    'session_id': session_id,
                    'established': True
                }
                print(f"Established session for user {user_id}: {session_id}")
                
            except Exception as e:
                print(f"Failed to establish session for {user_id}: {e}")
                self.sessions[user_id] = {
                    'session_id': str(uuid.uuid4()),
                    'established': False
                }
        
        return self.sessions[user_id]
    
    async def call_remote_tool(self, tool_name: str, arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Call tool on remote server"""
        try:
            session = await self.get_user_session(user_id)
            
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
                "X-User-ID": user_id
            }
            
            url = f"{self.base_url}/messages/?session_id={session['session_id']}"
            response = await self.client.post(url, json=mcp_message, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": mcp_message["id"],
                    "error": {
                        "code": -32000,
                        "message": f"HTTP error {response.status_code}: {response.text}"
                    }
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "error": {
                    "code": -32000,
                    "message": f"Request failed: {str(e)}"
                }
            }

# Global proxy instance
proxy = None

async def handle_initialize(request: Request):
    """Handle MCP initialize request"""
    try:
        data = await request.json()
        
        response = {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "experimental": {}
                },
                "serverInfo": {
                    "name": "mem0-network-proxy",
                    "version": "1.0.0"
                }
            }
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32000, "message": str(e)}
        }, status_code=500)

async def handle_list_tools(request: Request):
    """Handle tools/list request"""
    try:
        data = await request.json()
        
        tools = [
            {
                "name": "add_coding_preference",
                "description": "Add a new coding preference to remote mem0 server with user isolation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The content to store in memory"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID for data isolation (optional)"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "get_all_coding_preferences",
                "description": "Retrieve all stored coding preferences from remote server.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID for data isolation (optional)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "search_coding_preferences",
                "description": "Search through stored coding preferences on remote server.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID for data isolation (optional)"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
        
        response = {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {"tools": tools}
        }
        
        return JSONResponse(response)
        
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32000, "message": str(e)}
        }, status_code=500)

async def handle_call_tool(request: Request):
    """Handle tools/call request"""
    try:
        data = await request.json()
        params = data.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Extract user ID from arguments or headers
        user_id = arguments.get("user_id")
        if not user_id:
            user_id = request.headers.get("X-User-ID", "admin_default")
        
        # Ensure user_id is in arguments for remote call
        arguments["user_id"] = user_id
        
        # Forward to remote server
        result = await proxy.call_remote_tool(tool_name, arguments, user_id)
        
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": data.get("id") if 'data' in locals() else None,
            "error": {"code": -32000, "message": str(e)}
        }, status_code=500)

async def handle_mcp_request(request: Request):
    """Handle all MCP requests"""
    try:
        data = await request.json()
        method = data.get("method")
        
        if method == "initialize":
            return await handle_initialize(request)
        elif method == "tools/list":
            return await handle_list_tools(request)
        elif method == "tools/call":
            return await handle_call_tool(request)
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }, status_code=404)
            
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32000, "message": str(e)}
        }, status_code=500)

def create_app(remote_host: str, remote_port: int) -> Starlette:
    """Create Starlette application"""
    global proxy
    proxy = NetworkMCPProxy(remote_host, remote_port)
    
    return Starlette(
        debug=True,
        routes=[
            Route("/mcp", endpoint=handle_mcp_request, methods=["POST"]),
        ],
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Network MCP Proxy')
    parser.add_argument('--remote-host', default='192.168.8.225', help='Remote MCP server host')
    parser.add_argument('--remote-port', type=int, default=8082, help='Remote MCP server port')
    parser.add_argument('--proxy-host', default='0.0.0.0', help='Proxy server host')
    parser.add_argument('--proxy-port', type=int, default=8083, help='Proxy server port')
    
    args = parser.parse_args()
    
    app = create_app(args.remote_host, args.remote_port)
    
    print(f"🌐 Starting Network MCP Proxy")
    print(f"📡 Remote server: http://{args.remote_host}:{args.remote_port}")
    print(f"🔗 Proxy endpoint: http://{args.proxy_host}:{args.proxy_port}/mcp")
    print(f"🚀 Ready for remote Augment connections!")
    
    uvicorn.run(app, host=args.proxy_host, port=args.proxy_port)
