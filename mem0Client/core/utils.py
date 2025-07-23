"""Common utilities and helper functions."""

import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()


class DebugLogger:
    """Centralized debug logging utility."""
    
    def __init__(self, enable_debug: bool = True):
        self.enable_debug = enable_debug
    
    def log_api_request(self, operation: str, **params):
        """Log API request parameters."""
        if not self.enable_debug:
            return
            
        console.print(f"[DEBUG] {operation} - API Request parameters:")
        for key, value in params.items():
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            console.print(f"  - {key}: {value}")
    
    def log_api_response(self, operation: str, results: Any):
        """Log API response details."""
        if not self.enable_debug:
            return
            
        console.print(f"[DEBUG] {operation} - Raw response received:")
        console.print(f"  • Type: {type(results)}")
        console.print(f"  • Length: {len(results) if results else 'None'}")
        if results and len(results) > 0 and isinstance(results, list):
            console.print(f"  • First result keys: {list(results[0].keys()) if isinstance(results[0], dict) else 'Not a dict'}")
    
    def log_operation_params(self, operation: str, **params):
        """Log operation parameters."""
        if not self.enable_debug:
            return
            
        console.print(f"[DEBUG] {operation} parameters:")
        for key, value in params.items():
            console.print(f"  • {key}: {value}")
    
    def log_error(self, operation: str, error: Exception):
        """Log error information."""
        console.print(f"[ERROR] {operation} failed: {str(error)}")
        console.print(f"[ERROR] Exception type: {type(error)}")
        import traceback
        console.print(f"[ERROR] Traceback: {traceback.format_exc()}")


class FilterBuilder:
    """Build complex filter structures for API calls."""
    
    @staticmethod
    def build_user_filter(user_id: str) -> Dict[str, Any]:
        """Build basic user filter."""
        return {"AND": [{"user_id": user_id}]}
    
    @staticmethod
    def build_time_filter(user_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Build time range filter."""
        return {
            "AND": [
                {"user_id": user_id},
                {"updated_at": {"gte": start_date, "lte": end_date}}
            ]
        }
    
    @staticmethod
    def build_exclude_time_filter(user_id: str, exclude_start: str, exclude_end: str) -> Dict[str, Any]:
        """Build filter that excludes a time range."""
        return {
            "AND": [
                {"user_id": user_id},
                {
                    "NOT": [
                        {"created_at": {
                            "gte": exclude_start,
                            "lte": exclude_end
                        }}
                    ]
                }
            ]
        }
    
    @staticmethod
    def add_additional_filters(base_filter: Dict[str, Any], additional_filters: Dict[str, Any]) -> Dict[str, Any]:
        """Add additional filters to base filter."""
        if additional_filters:
            base_filter["AND"].append(additional_filters)
        return base_filter


class DateTimeHelper:
    """Date and time utilities."""
    
    @staticmethod
    def ensure_datetime_format(date_str: str) -> str:
        """Ensure date string is in full datetime format."""
        if 'T' not in date_str:
            if date_str.endswith('00:00:00') or date_str.endswith('23:59:59'):
                return date_str
            return f"{date_str}T00:00:00"
        return date_str
    
    @staticmethod
    def ensure_end_datetime_format(date_str: str) -> str:
        """Ensure end date string includes end of day time."""
        if 'T' not in date_str:
            return f"{date_str}T23:59:59"
        return date_str
    
    @staticmethod
    def format_display_date(date_str: str) -> str:
        """Format date string for display."""
        if not date_str or date_str == 'N/A':
            return 'N/A'
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return date_str[:10] if len(date_str) >= 10 else date_str


class ResultDisplayer:
    """Handle result display in different formats."""
    
    @staticmethod
    def display_console_results(results: List[Dict[str, Any]], max_content_length: int = 100, title: str = ""):
        """Display search results in console table format."""
        if not results:
            console.print("📭 No results found")
            return
        
        if title:
            console.print(f"\n{title}")
        
        table = Table(title="Memory Search Results")
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Content", style="white", width=50)
        table.add_column("Created", style="green", width=12)
        table.add_column("Source", style="yellow", width=15)
        table.add_column("Score", style="magenta", width=8)
        
        for result in results:
            memory_id = result.get('id', 'N/A')[:8]
            content = result.get('memory', '')
            
            # Truncate content if too long
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            created_at = DateTimeHelper.format_display_date(result.get('created_at', 'N/A'))
            
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'unknown')
            
            score = result.get('score', 0)
            score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
            
            table.add_row(memory_id, content, created_at, source, score_str)
        
        console.print(table)
    
    @staticmethod
    def prepare_dataframe_data(results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Prepare search results for DataFrame display."""
        data = []
        for result in results:
            data.append({
                "ID": result.get('id', 'N/A')[:8],
                "Content": result.get('memory', '')[:100] + "..." if len(result.get('memory', '')) > 100 else result.get('memory', ''),
                "Created": DateTimeHelper.format_display_date(result.get('created_at')),
                "Source": result.get('metadata', {}).get('source', 'unknown'),
                "Score": f"{result.get('score', 0):.2f}" if isinstance(result.get('score'), (int, float)) else str(result.get('score', 'N/A'))
            })
        return data


class ApiParameterBuilder:
    """Build API parameters consistently."""
    
    @staticmethod
    def build_upload_params(user_id: str, custom_instructions: Optional[str] = None,
                           includes: Optional[str] = None, excludes: Optional[str] = None,
                           infer: Optional[bool] = None, metadata: Optional[Dict[str, Any]] = None,
                           timestamp: Optional[int] = None) -> Dict[str, Any]:
        """Build upload API parameters."""
        params = {
            "user_id": user_id,
            "version": "v2"
        }
        
        if custom_instructions:
            params["custom_instructions"] = custom_instructions
        if includes:
            params["includes"] = includes
        if excludes:
            params["excludes"] = excludes
        if infer is not None:
            params["infer"] = infer
        if metadata:
            params["metadata"] = metadata
        if timestamp is not None:
            params["timestamp"] = timestamp
            
        return params
    
    @staticmethod
    def build_search_params(query: str, filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Build search API parameters."""
        return {
            "query": query,
            "version": "v2",
            "filters": filters,
            "top_k": limit
        }
    
    @staticmethod
    def build_get_all_params(filters: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Build get_all API parameters."""
        return {
            "version": "v2",
            "filters": filters,
            "limit": limit
        }


class ErrorPatterns:
    """Common error patterns and utilities."""
    
    RETRYABLE_PATTERNS = [
        '502 bad gateway',
        '503 service unavailable', 
        '504 gateway timeout',
        'timeout',
        'connection',
        'rate limit',
        'server error',
        'internal server error',
        'bad gateway',
        'service unavailable',
        'gateway timeout',
        'connection reset',
        'connection refused',
        'read timeout',
        'connect timeout'
    ]
    
    @classmethod
    def is_retryable_error(cls, exception: Exception) -> bool:
        """Check if an error should be retried."""
        error_msg = str(exception).lower()
        return any(pattern in error_msg for pattern in cls.RETRYABLE_PATTERNS)


class MessageProcessor:
    """Process and prepare messages for upload."""
    
    @staticmethod
    def truncate_content_preview(content: str, max_length: int = 20) -> str:
        """Create truncated preview of content."""
        return content[:max_length] + "..." if len(content) > max_length else content
    
    @staticmethod
    def log_messages_debug(messages: List[Dict[str, str]], logger: DebugLogger, max_display: int = 3):
        """Log messages for debugging."""
        if not logger.enable_debug or not messages:
            return
            
        for i, msg in enumerate(messages[:max_display]):
            if isinstance(msg, dict) and 'content' in msg:
                content_preview = MessageProcessor.truncate_content_preview(msg['content'])
                role = msg.get('role', 'unknown')
                console.print(f"  💬 messages[{i}]: role='{role}', content='{content_preview}'")
            elif isinstance(msg, str):
                content_preview = MessageProcessor.truncate_content_preview(msg)
                console.print(f"  💬 messages[{i}]: '{content_preview}'")
        
        if len(messages) > max_display:
            console.print(f"  💬 ... and {len(messages) - max_display} more messages")
    
    @staticmethod
    def log_metadata_debug(metadata: Dict[str, Any], logger: DebugLogger):
        """Log metadata for debugging."""
        if not logger.enable_debug:
            return
            
        metadata_summary = {}
        for key, value in metadata.items():
            if key in ['upload_time', 'user_id', 'extract_mode', 'file_name', 'file_type']:
                metadata_summary[key] = value
            elif isinstance(value, str) and len(value) > 30:
                metadata_summary[key] = value[:30] + "..."
            else:
                metadata_summary[key] = value
        console.print(f"  📋 metadata: {metadata_summary}") 