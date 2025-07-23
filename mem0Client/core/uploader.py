"""Upload and memory management with Mem0 API."""

import os
import time
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.local_client import MemoryClient
from rich.console import Console
from rich.progress import Progress, TaskID
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import Config
from core.parser import FileParser
from core.utils import (
    DebugLogger, ApiParameterBuilder, ErrorPatterns,
    MessageProcessor
)

console = Console()


class MemoryUploader:
    """Handles uploading and managing memories with Mem0."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the uploader with configuration."""
        self.config = config or Config()
        
        # Validate configuration
        if not self.config.validate():
            raise ValueError("Invalid configuration. Please check your API key.")
        
        # Initialize Mem0 client
        os.environ['MEM0_API_KEY'] = self.config.mem0_api_key
        self.client = MemoryClient()
        
        # Initialize debug logger
        self.logger = DebugLogger(self.config.debug_logging)
        
        console.print(f"✅ Initialized Mem0 client for user: {self.config.default_user_id}")
    
    def _is_retryable_error(self, exception: Exception) -> bool:
        """Check if an error should be retried."""
        return ErrorPatterns.is_retryable_error(exception)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda retry_state: console.print(f"⏳ Retry attempt {retry_state.attempt_number}/3 in {retry_state.next_action.sleep:.1f}s..."),
        reraise=True
    )
    def _add_with_retry(self, messages: List, **kwargs) -> Dict[str, Any]:
        """
        Add messages to Mem0 with retry mechanism.
        
        Retries up to 3 times with exponential backoff (2s, 4s, 8s).
        Handles API timeouts, 502 errors, and other temporary failures.
        """
        if self.config.debug_logging:
            console.print("🔄 Attempting API call to Mem0...")
        
        result = self.client.add(messages, **kwargs)
        
        if self.config.debug_logging:
            console.print("✅ API call successful")
        
        return result
    
    def upload_text(self, 
                   content: str, 
                   user_id: Optional[str] = None,
                   extract_mode: str = "auto",
                   metadata: Optional[Dict[str, Any]] = None,
                   custom_instructions: Optional[str] = None,
                   includes: Optional[str] = None,
                   excludes: Optional[str] = None,
                   infer: Optional[bool] = None,
                   batch_size: Optional[int] = None,
                   disable_batching: bool = False) -> Dict[str, Any]:
        """
        Upload text content to Mem0.
        
        Args:
            content: Text content to upload
            user_id: User ID for the memory (defaults to config)
            extract_mode: Processing mode ("auto" or "raw")
            metadata: Additional metadata
            custom_instructions: Custom instructions for AI processing
            includes: Content types to specifically include
            excludes: Content types to exclude from processing
            infer: Whether to infer memories (True) or store raw messages (False)
            batch_size: Number of messages per batch (optional)
            disable_batching: Whether to disable batch processing
            
        Returns:
            Upload result from Mem0
        """
        user_id = user_id or self.config.default_user_id
        
        # Parse content
        messages, parsed_metadata = FileParser.parse_plain_text(content, extract_mode)
        
        # For text uploads, no metadata needed (as per user request)
        final_metadata = metadata or {}
        
        # Determine effective batch settings
        effective_batch_size = batch_size or self.config.message_batch_size
        use_batching = (not disable_batching and 
                       self.config.enable_message_batching and 
                       len(messages) > self.config.message_batch_threshold)
        
        try:
            # Prepare additional parameters for Mem0 using utility
            add_params = ApiParameterBuilder.build_upload_params(
                user_id=user_id,
                custom_instructions=custom_instructions,
                includes=includes,
                excludes=excludes,
                infer=infer,
                metadata=final_metadata
            )
            
            # Log the parameters being sent to Mem0 (if debug enabled)
            if self.logger.enable_debug:
                console.print("\n🔍 [DEBUG] Mem0.add() 调用参数:")
                console.print(f"  📱 user_id: {user_id}")
                console.print(f"  📦 batch_processing: {use_batching}")
                if use_batching:
                    console.print(f"  📏 batch_size: {effective_batch_size}")
                
                # Log messages using utility
                MessageProcessor.log_messages_debug(messages, self.logger)
                
                # Log custom processing parameters
                if custom_instructions:
                    instr_preview = MessageProcessor.truncate_content_preview(custom_instructions, 50)
                    console.print(f"  🎯 custom_instructions: '{instr_preview}'")
                if includes:
                    console.print(f"  ✅ includes: '{includes}'")
                if excludes:
                    console.print(f"  ❌ excludes: '{excludes}'")
                if infer is not None:
                    console.print(f"  🧠 infer: {infer}")
                
                # Log metadata using utility
                MessageProcessor.log_metadata_debug(final_metadata, self.logger)
                console.print("")
            
            # Add to Mem0 (messages as first positional argument)
            if use_batching:
                # Use batch processing for long message lists
                console.print(f"🔄 Message count ({len(messages)}) exceeds threshold ({self.config.message_batch_threshold}), using batch processing")
                
                results = self._upload_messages_in_batches(
                    messages=messages,
                    user_id=user_id,
                    add_params=add_params,
                    batch_size=effective_batch_size,
                    metadata=final_metadata
                )
                
                # Return summary of batch results
                successful_batches = [r for r in results if not r.get("failed", False)]
                failed_batches = [r for r in results if r.get("failed", False)]
                
                result = {
                    "batch_processing": True,
                    "total_batches": len(results),
                    "successful_batches": len(successful_batches),
                    "failed_batches": len(failed_batches),
                    "batch_results": results
                }
                
                if successful_batches:
                    # Use the first successful result as primary
                    result.update(successful_batches[0])
                
            else:
                # Direct upload for shorter message lists
                result = self._add_with_retry(messages, **add_params)
            
            console.print(f"✅ Uploaded text memory for user: {user_id}")
            if custom_instructions or includes or excludes or infer is not None:
                console.print(f"📋 Applied custom processing settings")
            return result
            
        except Exception as e:
            console.print(f"❌ Failed to upload text: {str(e)}")
            raise
    
    def upload_file(self, 
                   file_path: str,
                   user_id: Optional[str] = None,
                   extract_mode: Optional[str] = None,
                   custom_instructions: Optional[str] = None,
                   includes: Optional[str] = None,
                   excludes: Optional[str] = None,
                   infer: Optional[bool] = None,
                   batch_size: Optional[int] = None,
                   disable_batching: bool = False) -> Dict[str, Any]:
        """
        Upload a file to Mem0.
        
        Args:
            file_path: Path to the file
            user_id: User ID for the memory (defaults to config)
            extract_mode: Processing mode (defaults to config)
            custom_instructions: Custom instructions for AI processing
            includes: Content types to specifically include
            excludes: Content types to exclude from processing
            infer: Whether to infer memories (True) or store raw messages (False)
            batch_size: Number of messages per batch (optional)
            disable_batching: Whether to disable batch processing
            
        Returns:
            Upload result from Mem0
        """
        user_id = user_id or self.config.default_user_id
        extract_mode = extract_mode or self.config.default_extract_mode
        
        # Validate file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.config.max_file_size_mb:
            raise ValueError(f"File too large: {file_size_mb:.1f}MB > {self.config.max_file_size_mb}MB")
        
        # Parse file
        try:
            messages, metadata = FileParser.parse_file(file_path, extract_mode)
        except Exception as e:
            console.print(f"❌ Failed to parse file {file_path}: {str(e)}")
            raise
        
        # For file uploads, only keep filename and timestamps (for JSON chats)
        # No need for upload_time, user_id, extract_mode etc.
        
        # Determine effective batch settings
        effective_batch_size = batch_size or self.config.message_batch_size
        use_batching = (not disable_batching and 
                       self.config.enable_message_batching and 
                       len(messages) > self.config.message_batch_threshold)
        
        try:
            # Extract timestamp from metadata if available (for JSON chat files)
            timestamp = None
            if metadata and "updated" in metadata:
                try:
                    # Convert updated timestamp (ISO format) to Unix timestamp
                    from datetime import datetime
                    dt = datetime.fromisoformat(metadata["updated"].replace('Z', '+00:00'))
                    timestamp = int(dt.timestamp())
                    console.print(f"🕐 Using timestamp from file: {metadata['updated']} (Unix: {timestamp})")
                except Exception as e:
                    console.print(f"⚠️ Could not parse timestamp from metadata: {e}")
            
            # Prepare additional parameters for Mem0 using utility
            add_params = ApiParameterBuilder.build_upload_params(
                user_id=user_id,
                custom_instructions=custom_instructions,
                includes=includes,
                excludes=excludes,
                infer=infer,
                metadata=metadata,
                timestamp=timestamp
            )
            
            # Log the parameters being sent to Mem0 (if debug enabled)
            if self.config.debug_logging:
                console.print(f"\n🔍 [DEBUG] Mem0.add() 调用参数 (文件: {os.path.basename(file_path)}):")
                console.print(f"  📱 user_id: {user_id}")
                console.print(f"  📦 batch_processing: {use_batching}")
                if use_batching:
                    console.print(f"  📏 batch_size: {effective_batch_size}")
                
                # Log messages with truncation
                if messages:
                    for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                        if isinstance(msg, dict) and 'content' in msg:
                            content_preview = msg['content'][:20] + "..." if len(msg['content']) > 20 else msg['content']
                            role = msg.get('role', 'unknown')
                            console.print(f"  💬 messages[{i}]: role='{role}', content='{content_preview}'")
                        elif isinstance(msg, str):
                            content_preview = msg[:20] + "..." if len(msg) > 20 else msg
                            console.print(f"  💬 messages[{i}]: '{content_preview}'")
                    if len(messages) > 3:
                        console.print(f"  💬 ... and {len(messages) - 3} more messages")
                
                # Log custom processing parameters
                if custom_instructions:
                    instr_preview = custom_instructions[:50] + "..." if len(custom_instructions) > 50 else custom_instructions
                    console.print(f"  🎯 custom_instructions: '{instr_preview}'")
                if includes:
                    console.print(f"  ✅ includes: '{includes}'")
                if excludes:
                    console.print(f"  ❌ excludes: '{excludes}'")
                if infer is not None:
                    console.print(f"  🧠 infer: {infer}")
                if timestamp is not None:
                    console.print(f"  🕐 timestamp: {timestamp}")
                
                # Log metadata (excluding lengthy fields)
                metadata_summary = {}
                for key, value in metadata.items():
                    if key in ['upload_time', 'user_id', 'extract_mode', 'file_name', 'file_type']:
                        metadata_summary[key] = value
                    elif isinstance(value, str) and len(value) > 30:
                        metadata_summary[key] = value[:30] + "..."
                    else:
                        metadata_summary[key] = value
                console.print(f"  📋 metadata: {metadata_summary}")
                console.print("")
            
            # Add to Mem0 (messages as first positional argument)
            try:
                if use_batching:
                    # Use batch processing for long message lists
                    console.print(f"🔄 Message count ({len(messages)}) exceeds threshold ({self.config.message_batch_threshold}), using batch processing")
                    
                    results = self._upload_messages_in_batches(
                        messages=messages,
                        user_id=user_id,
                        add_params=add_params,
                        batch_size=effective_batch_size,
                        metadata=metadata
                    )
                    
                    # Return summary of batch results
                    successful_batches = [r for r in results if not r.get("failed", False)]
                    failed_batches = [r for r in results if r.get("failed", False)]
                    
                    result = {
                        "batch_processing": True,
                        "total_batches": len(results),
                        "successful_batches": len(successful_batches),
                        "failed_batches": len(failed_batches),
                        "batch_results": results
                    }
                    
                    if successful_batches:
                        # Use the first successful result as primary
                        result.update(successful_batches[0])
                        
                else:
                    # Direct upload for shorter message lists
                    result = self._add_with_retry(messages, **add_params)
                
                console.print(f"✅ Uploaded file: {file_path} for user: {user_id}")
                if custom_instructions or includes or excludes or infer is not None:
                    console.print(f"📋 Applied custom processing settings")
                return result
                
            except Exception as api_error:
                raise api_error
            
        except Exception as e:
            console.print(f"❌ Failed to upload file {file_path}: {str(e)}")
            raise
    
    def upload_batch(self, 
                    file_paths: List[str],
                    user_id: Optional[str] = None,
                    extract_mode: Optional[str] = None,
                    custom_instructions: Optional[str] = None,
                    includes: Optional[str] = None,
                    excludes: Optional[str] = None,
                    infer: Optional[bool] = None,
                    concurrent_upload: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Upload multiple files in batch with improved error handling and optional concurrency.
        
        Features:
        - Per-file retry with 3 attempts
        - Continues with other files even if one fails  
        - Optional concurrent processing
        - Detailed progress tracking
        
        Args:
            file_paths: List of file paths
            user_id: User ID for the memories
            extract_mode: Processing mode
            custom_instructions: Custom instructions for AI processing
            includes: Content types to specifically include
            excludes: Content types to exclude from processing
            infer: Whether to infer memories
            concurrent_upload: Whether to process files concurrently (None = use config default)
            
        Returns:
            List of upload results with detailed status for each file
        """
        user_id = user_id or self.config.default_user_id
        use_concurrent = concurrent_upload if concurrent_upload is not None else self.config.concurrent_upload
        max_workers = self.config.max_concurrent_files if use_concurrent else 1
        
        console.print(f"📦 Starting batch upload: {len(file_paths)} files")
        console.print(f"🔄 Processing mode: {'concurrent' if use_concurrent else 'sequential'}")
        if use_concurrent:
            console.print(f"⚡ Max concurrent files: {max_workers}")
        
        results = []
        
        def upload_single_file_with_retry(file_path: str) -> Dict[str, Any]:
            """Upload a single file with retry logic."""
            max_retries = 3
            
            for attempt in range(1, max_retries + 1):
                try:
                    console.print(f"📄 Uploading {file_path} (attempt {attempt}/{max_retries})")
                    
                    result = self.upload_file(
                        file_path=file_path,
                        user_id=user_id,
                        extract_mode=extract_mode,
                        custom_instructions=custom_instructions,
                        includes=includes,
                        excludes=excludes,
                        infer=infer
                    )
                    
                    console.print(f"✅ {file_path} uploaded successfully")
                    return {
                        "file": file_path,
                        "status": "success", 
                        "result": result,
                        "attempts": attempt
                    }
                    
                except Exception as e:
                    error_msg = str(e)
                    console.print(f"❌ {file_path} failed attempt {attempt}/{max_retries}: {error_msg}")
                    
                    if attempt == max_retries:
                        # Final failure
                        console.print(f"🚨 {file_path} failed after {max_retries} attempts, giving up")
                        return {
                            "file": file_path,
                            "status": "error",
                            "error": error_msg,
                            "attempts": attempt,
                            "final_failure": True
                        }
                    else:
                        # Wait before retry
                        wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                        console.print(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
            
            # Should never reach here
            return {
                "file": file_path,
                "status": "error", 
                "error": "Unknown error",
                "attempts": max_retries
            }
        
        # Execute uploads
        if use_concurrent and len(file_paths) > 1:
            # Concurrent processing
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
                with Progress() as progress:
                    task = progress.add_task("Uploading files...", total=len(file_paths))
                    
                    # Submit all tasks
                    future_to_filepath = {
                        executor.submit(upload_single_file_with_retry, file_path): file_path
                        for file_path in file_paths
                    }
                    
                    # Collect results as they complete
                    for future in cf.as_completed(future_to_filepath):
                        result = future.result()
                        results.append(result)
                        progress.advance(task)
                        
                        # Continue processing other files regardless of individual failures
                        continue
        else:
            # Sequential processing
            with Progress() as progress:
                task = progress.add_task("Uploading files...", total=len(file_paths))
                
                for file_path in file_paths:
                    result = upload_single_file_with_retry(file_path)
                    results.append(result)
                    progress.advance(task)
                    
                    # Continue with next file regardless of current file's result
                    continue
        
        # Generate summary
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = len(results) - success_count
        total_attempts = sum(r.get("attempts", 0) for r in results)
        
        console.print(f"\n📊 Batch Upload Summary:")
        console.print(f"  ✅ Successful: {success_count}/{len(file_paths)}")
        console.print(f"  ❌ Failed: {error_count}/{len(file_paths)}")
        console.print(f"  🔄 Total attempts: {total_attempts}")
        console.print(f"  📈 Success rate: {(success_count/len(file_paths)*100):.1f}%")
        
        # Show failed files
        if error_count > 0:
            console.print(f"\n🚨 Failed files:")
            for result in results:
                if result["status"] == "error":
                    console.print(f"  ❌ {result['file']}: {result['error']}")
        
        return results
    
    def upload_directory(self, 
                        directory_path: str,
                        user_id: Optional[str] = None,
                        extract_mode: Optional[str] = None,
                        recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Upload all supported files from a directory.
        
        Args:
            directory_path: Path to the directory
            user_id: User ID for the memories
            extract_mode: Processing mode
            recursive: Whether to search subdirectories
            
        Returns:
            List of upload results
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Find all supported files
        supported_extensions = self.config.supported_formats
        file_paths = []
        
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in supported_extensions):
                        file_paths.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in supported_extensions):
                    file_paths.append(file_path)
        
        if not file_paths:
            console.print(f"⚠️  No supported files found in {directory_path}")
            return []
        
        console.print(f"📁 Found {len(file_paths)} files to upload")
        return self.upload_batch(file_paths, user_id, extract_mode)
    
    def _upload_messages_in_batches(self,
                                  messages: List[Dict[str, str]],
                                  user_id: str,
                                  add_params: Dict[str, Any],
                                  batch_size: int = 2,
                                  metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Upload long message lists in incremental batches to ensure all messages are processed.
        
        Uses incremental batching approach:
        - Batch 1: messages[0:batch_size]
        - Batch 2: messages[0:batch_size*2]  
        - Batch 3: messages[0:batch_size*3]
        - ...
        
        This ensures Mem0 can build context incrementally and process all messages.
        
        Args:
            messages: List of messages to upload
            user_id: User ID for the memories
            add_params: Additional parameters for Mem0 API
            batch_size: Number of NEW messages to add per batch (default: 8)
            metadata: Base metadata to include in each batch
            
        Returns:
            List of upload results from each batch
        """
        if len(messages) <= batch_size:
            # If messages are within limit, upload directly
            if self.config.debug_logging:
                console.print(f"📤 Uploading {len(messages)} messages directly (within batch size limit)")
            
            result = self._add_with_retry(messages, **add_params)
            return [result]
        
        # Calculate incremental batches
        results = []
        total_batches = (len(messages) + batch_size - 1) // batch_size
        
        console.print(f"📦 Using incremental batching: {len(messages)} messages in {total_batches} batches (batch size: {batch_size})")
        
        for batch_num in range(1, total_batches + 1):
            # Incremental batch: include all messages from start up to current batch end
            end_index = min(batch_num * batch_size, len(messages))
            batch_messages = messages[0:end_index]
            
            # Calculate how many new messages are in this batch
            new_messages_count = min(batch_size, len(messages) - (batch_num - 1) * batch_size)
            
            # Use original metadata without adding batch info
            batch_add_params = add_params.copy()
            if metadata:
                batch_add_params["metadata"] = metadata
            
            try:
                if self.config.debug_logging:
                    console.print(f"📤 Uploading incremental batch {batch_num}/{total_batches}")
                    console.print(f"    📊 Total messages: {len(batch_messages)} (new: {new_messages_count})")
                    
                    # Log batch messages summary (show first 2 and last 2)
                    if len(batch_messages) <= 4:
                        # Show all if 4 or fewer messages
                        for j, msg in enumerate(batch_messages):
                            if isinstance(msg, dict) and 'content' in msg:
                                content_preview = msg['content'][:15] + "..." if len(msg['content']) > 15 else msg['content']
                                role = msg.get('role', 'unknown')
                                console.print(f"    💬 [{j+1}] {role}: '{content_preview}'")
                    else:
                        # Show first 2 and last 2
                        for j in range(2):
                            msg = batch_messages[j]
                            if isinstance(msg, dict) and 'content' in msg:
                                content_preview = msg['content'][:15] + "..." if len(msg['content']) > 15 else msg['content']
                                role = msg.get('role', 'unknown')
                                console.print(f"    💬 [{j+1}] {role}: '{content_preview}'")
                        
                        console.print(f"    💬 ... {len(batch_messages) - 4} messages ...")
                        
                        for j in range(len(batch_messages) - 2, len(batch_messages)):
                            msg = batch_messages[j]
                            if isinstance(msg, dict) and 'content' in msg:
                                content_preview = msg['content'][:15] + "..." if len(msg['content']) > 15 else msg['content']
                                role = msg.get('role', 'unknown')
                                console.print(f"    💬 [{j+1}] {role}: '{content_preview}'")
                
                result = self._add_with_retry(batch_messages, **batch_add_params)
                results.append(result)
                
                if self.config.debug_logging:
                    console.print(f"✅ Incremental batch {batch_num}/{total_batches} uploaded successfully")
                
            except Exception as e:
                error_msg = f"❌ Failed to upload incremental batch {batch_num}/{total_batches}: {str(e)}"
                console.print(error_msg)
                
                # Add error info to results
                results.append({
                    "error": str(e),
                    "batch_number": batch_num,
                    "total_messages_in_batch": len(batch_messages),
                    "new_messages_in_batch": new_messages_count,
                    "failed": True
                })
                
                # Add a small delay before continuing to avoid overwhelming the API
                console.print(f"⏳ Waiting 3 seconds before continuing to next batch...")
                time.sleep(3)
                
                # Continue with next batch instead of failing completely
                continue
        
        # Summary
        successful_batches = sum(1 for r in results if not r.get("failed", False))
        failed_batches = len(results) - successful_batches
        
        console.print(f"📊 Incremental batch upload summary: {successful_batches} successful, {failed_batches} failed")
        
        return results 