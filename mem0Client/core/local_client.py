"""Local Mem0 API Client for connecting to our local API server."""

import requests
import json
from typing import List, Dict, Any, Optional
from core.config import Config


class LocalMemoryClient:
    """Client for connecting to local Mem0 API server."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the local client."""
        self.config = config or Config()
        self.base_url = self.config.config.get('mem0', {}).get('api_url', 'http://localhost:8888')
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def add(self, messages: List[Dict[str, str]], user_id: str, **kwargs) -> Dict[str, Any]:
        """Add memories from messages."""
        payload = {
            "messages": messages,
            "user_id": user_id
        }
        
        # Add optional parameters
        if 'custom_instructions' in kwargs and kwargs['custom_instructions']:
            payload['custom_instructions'] = kwargs['custom_instructions']
        if 'includes' in kwargs and kwargs['includes']:
            payload['includes'] = kwargs['includes'].split(',') if isinstance(kwargs['includes'], str) else kwargs['includes']
        if 'excludes' in kwargs and kwargs['excludes']:
            payload['excludes'] = kwargs['excludes'].split(',') if isinstance(kwargs['excludes'], str) else kwargs['excludes']
        
        try:
            response = self.session.post(f"{self.base_url}/memories", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to add memories: {str(e)}")
    
    def search(self, query: str, user_id: str, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Search memories."""
        payload = {
            "query": query,
            "user_id": user_id,
            "limit": limit
        }
        
        try:
            response = self.session.post(f"{self.base_url}/search", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to search memories: {str(e)}")
    
    def get_all(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Get all memories for a user."""
        try:
            response = self.session.get(f"{self.base_url}/memories", params={"user_id": user_id})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get memories: {str(e)}")
    
    def delete(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        """Delete a memory."""
        try:
            response = self.session.delete(f"{self.base_url}/memories/{memory_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to delete memory: {str(e)}")
    
    def reset(self, **kwargs) -> Dict[str, Any]:
        """Reset all memories."""
        try:
            response = self.session.post(f"{self.base_url}/reset")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to reset memories: {str(e)}")


class MemoryClient:
    """Compatibility wrapper to replace mem0.MemoryClient."""
    
    def __init__(self):
        """Initialize with local client."""
        self.client = LocalMemoryClient()
    
    def add(self, messages: List[Dict[str, str]], user_id: str, **kwargs) -> Dict[str, Any]:
        """Add memories."""
        return self.client.add(messages, user_id, **kwargs)
    
    def search(self, query: str, user_id: str, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Search memories."""
        return self.client.search(query, user_id, limit, **kwargs)
    
    def get_all(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Get all memories."""
        return self.client.get_all(user_id, **kwargs)
    
    def delete(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        """Delete memory."""
        return self.client.delete(memory_id, **kwargs)
    
    def reset(self, **kwargs) -> Dict[str, Any]:
        """Reset memories."""
        return self.client.reset(**kwargs)
