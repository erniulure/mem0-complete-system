#!/usr/bin/env python3
"""
Mem0 Client CLI Tool
A command-line interface for uploading and searching memories with Mem0.
"""

import click
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import Config
from core.uploader import MemoryUploader
from core.searcher import MemorySearcher

console = Console()

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🧠 Mem0 Client - Upload and search your memories"""
    pass

@cli.command()
@click.argument('content', type=str)
@click.option('--user-id', '-u', help='User ID for the memory')
@click.option('--metadata', help='Additional metadata as JSON string')
@click.option('--custom-instructions', '--ci', help='Custom instructions for AI processing (overrides config)')
@click.option('--includes', '--inc', help='Content types to specifically include (overrides config)')
@click.option('--excludes', '--exc', help='Content types to exclude from processing (overrides config)')
@click.option('--infer/--no-infer', default=None, help='Whether to infer memories (overrides config)')
@click.option('--batch-size', type=int, help='Batch size for processing long message lists (default: from config)')
@click.option('--disable-batching', is_flag=True, help='Disable automatic batch processing for long messages')
@click.option('--use-defaults', is_flag=True, help='Use persistent settings from config file')
def upload_text(content: str, user_id: Optional[str], metadata: Optional[str],
               custom_instructions: Optional[str], includes: Optional[str], excludes: Optional[str],
               infer: Optional[bool], batch_size: Optional[int], disable_batching: bool, use_defaults: bool):
    """Upload text content to Mem0."""
    try:
        config = Config()
        uploader = MemoryUploader(config)
        
        # Parse metadata if provided
        meta_dict = None
        if metadata:
            try:
                meta_dict = json.loads(metadata)
            except json.JSONDecodeError:
                console.print("❌ Invalid JSON format for metadata")
                return
        
        # Use persistent config settings if requested or no CLI args provided
        final_custom_instructions = custom_instructions
        final_includes = includes
        final_excludes = excludes
        final_infer = infer
        
        if use_defaults or (not custom_instructions and not includes and not excludes and infer is None):
            final_custom_instructions = final_custom_instructions or config.advanced_custom_instructions
            final_includes = final_includes or config.advanced_includes
            final_excludes = final_excludes or config.advanced_excludes
            if final_infer is None:
                final_infer = config.advanced_infer
        
        result = uploader.upload_text(
            content=content,
            user_id=user_id,
            extract_mode="auto",  # Always use auto mode now
            metadata=meta_dict,
            custom_instructions=final_custom_instructions.strip() if final_custom_instructions else None,
            includes=final_includes.strip() if final_includes else None,
            excludes=final_excludes.strip() if final_excludes else None,
            infer=final_infer,
            batch_size=batch_size,
            disable_batching=disable_batching
        )
        
        console.print(Panel(f"✅ Successfully uploaded text memory", title="Upload Complete"))
        
        # Show applied settings
        applied_settings = []
        if final_custom_instructions:
            applied_settings.append(f"🎯 Custom Instructions: {final_custom_instructions}")
        if final_includes:
            applied_settings.append(f"✅ Includes: {final_includes}")
        if final_excludes:
            applied_settings.append(f"❌ Excludes: {final_excludes}")
        if final_infer is not None:
            applied_settings.append(f"🧠 Infer: {final_infer}")
        
        if applied_settings:
            console.print("\n📋 Applied Settings:")
            for setting in applied_settings:
                console.print(f"  {setting}")
        
    except Exception as e:
        console.print(f"❌ Upload failed: {str(e)}")

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--user-id', '-u', help='User ID for the memory')
@click.option('--custom-instructions', '--ci', help='Custom instructions for AI processing (overrides config)')
@click.option('--includes', '--inc', help='Content types to specifically include (overrides config)')
@click.option('--excludes', '--exc', help='Content types to exclude from processing (overrides config)')
@click.option('--infer/--no-infer', default=None, help='Whether to infer memories (overrides config)')
@click.option('--batch-size', type=int, help='Batch size for processing long message lists (default: from config)')
@click.option('--disable-batching', is_flag=True, help='Disable automatic batch processing for long messages')
@click.option('--use-defaults', is_flag=True, help='Use persistent settings from config file')
def upload_file(file_path: str, user_id: Optional[str],
               custom_instructions: Optional[str], includes: Optional[str], excludes: Optional[str],
               infer: Optional[bool], batch_size: Optional[int], disable_batching: bool, use_defaults: bool):
    """Upload a single file to Mem0."""
    try:
        config = Config()
        uploader = MemoryUploader(config)
        
        # Use persistent config settings if requested or no CLI args provided
        final_custom_instructions = custom_instructions
        final_includes = includes
        final_excludes = excludes
        final_infer = infer
        
        if use_defaults or (not custom_instructions and not includes and not excludes and infer is None):
            final_custom_instructions = final_custom_instructions or config.advanced_custom_instructions
            final_includes = final_includes or config.advanced_includes
            final_excludes = final_excludes or config.advanced_excludes
            if final_infer is None:
                final_infer = config.advanced_infer
        
        result = uploader.upload_file(
            file_path=file_path,
            user_id=user_id,
            extract_mode="auto",  # Always use auto mode now
            custom_instructions=final_custom_instructions.strip() if final_custom_instructions else None,
            includes=final_includes.strip() if final_includes else None,
            excludes=final_excludes.strip() if final_excludes else None,
            infer=final_infer,
            batch_size=batch_size,
            disable_batching=disable_batching
        )
        
        console.print(Panel(f"✅ Successfully uploaded file: {file_path}", title="Upload Complete"))
        
        # Show applied settings
        applied_settings = []
        if final_custom_instructions:
            applied_settings.append(f"🎯 Custom Instructions: {final_custom_instructions}")
        if final_includes:
            applied_settings.append(f"✅ Includes: {final_includes}")
        if final_excludes:
            applied_settings.append(f"❌ Excludes: {final_excludes}")
        if final_infer is not None:
            applied_settings.append(f"🧠 Infer: {final_infer}")
        
        if applied_settings:
            console.print("\n📋 Applied Settings:")
            for setting in applied_settings:
                console.print(f"  {setting}")
        
    except Exception as e:
        console.print(f"❌ Upload failed: {str(e)}")

@cli.command()
@click.argument('directory_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--user-id', '-u', help='User ID for the memories')
@click.option('--recursive/--no-recursive', default=True, help='Search subdirectories recursively')
@click.option('--concurrent/--no-concurrent', default=None, help='Use concurrent processing (default: from config)')
@click.option('--custom-instructions', '--ci', help='Custom instructions for AI processing (overrides config)')
@click.option('--includes', '--inc', help='Content types to specifically include (overrides config)')
@click.option('--excludes', '--exc', help='Content types to exclude from processing (overrides config)')
@click.option('--infer/--no-infer', default=None, help='Whether to infer memories (overrides config)')
@click.option('--use-defaults', is_flag=True, help='Use persistent settings from config file')
def upload_directory(directory_path: str, user_id: Optional[str], recursive: bool, concurrent: Optional[bool],
                    custom_instructions: Optional[str], includes: Optional[str], excludes: Optional[str],
                    infer: Optional[bool], use_defaults: bool):
    """Upload all supported files from a directory with enhanced batch processing."""
    try:
        config = Config()
        uploader = MemoryUploader(config)
        
        # Use persistent config settings if requested or no CLI args provided
        final_custom_instructions = custom_instructions
        final_includes = includes
        final_excludes = excludes
        final_infer = infer
        
        if use_defaults or (not custom_instructions and not includes and not excludes and infer is None):
            final_custom_instructions = final_custom_instructions or config.advanced_custom_instructions
            final_includes = final_includes or config.advanced_includes
            final_excludes = final_excludes or config.advanced_excludes
            if final_infer is None:
                final_infer = config.advanced_infer
        
        # Find files first
        import os
        from pathlib import Path
        
        supported_extensions = config.supported_formats
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
            console.print("📭 No supported files found in the directory")
            return
        
        console.print(f"📁 Found {len(file_paths)} files to upload")
        
        # Use enhanced batch upload
        results = uploader.upload_batch(
            file_paths=file_paths,
            user_id=user_id,
            extract_mode="auto",
            custom_instructions=final_custom_instructions.strip() if final_custom_instructions else None,
            includes=final_includes.strip() if final_includes else None,
            excludes=final_excludes.strip() if final_excludes else None,
            infer=final_infer,
            concurrent_upload=concurrent
        )
        
        # Show detailed summary
        success_count = sum(1 for r in results if r["status"] == "success")
        error_count = len(results) - success_count
        total_attempts = sum(r.get("attempts", 0) for r in results)
        
        console.print(Panel(
            f"📊 Enhanced Batch Upload Summary:\n"
            f"✅ Successful: {success_count}/{len(file_paths)}\n"
            f"❌ Failed: {error_count}/{len(file_paths)}\n"
            f"🔄 Total attempts: {total_attempts}\n"
            f"📈 Success rate: {(success_count/len(file_paths)*100):.1f}%",
            title="Batch Upload Complete"
        ))
        
        # Show applied settings
        applied_settings = []
        if final_custom_instructions:
            applied_settings.append(f"🎯 Custom Instructions: {final_custom_instructions}")
        if final_includes:
            applied_settings.append(f"✅ Includes: {final_includes}")
        if final_excludes:
            applied_settings.append(f"❌ Excludes: {final_excludes}")
        if final_infer is not None:
            applied_settings.append(f"🧠 Infer: {final_infer}")
        
        if applied_settings:
            console.print("\n📋 Applied Settings:")
            for setting in applied_settings:
                console.print(f"  {setting}")
        
        # Show errors if any
        if error_count > 0:
            console.print("\n🚨 Failed Files:")
            for result in results:
                if result["status"] == "error":
                    attempts = result.get("attempts", 0)
                    console.print(f"  ❌ {result['file']} (after {attempts} attempts): {result['error']}")
        
    except Exception as e:
        console.print(f"❌ Batch upload failed: {str(e)}")

@cli.command()
@click.argument('query', type=str)
@click.option('--user-id', '-u', help='User ID to search')
@click.option('--limit', '-l', type=int, help='Maximum number of results')
@click.option('--show-full', is_flag=True, help='Show full content instead of truncated')
def search(query: str, user_id: Optional[str], limit: Optional[int], show_full: bool):
    """Search memories by query."""
    try:
        config = Config()
        searcher = MemorySearcher(config)
        
        results = searcher.search_by_query(
            query=query,
            user_id=user_id,
            # limit=limit
        )
        
        # Display results
        max_length = None if show_full else 100
        searcher.display_search_results(results, max_content_length=max_length)
        
    except Exception as e:
        console.print(f"❌ Search failed: {str(e)}")

@cli.command()
@click.option('--days', '-d', type=int, help='Number of days to look back')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--query', '-q', help='Optional search query within time range')
@click.option('--user-id', '-u', help='User ID to search')
@click.option('--limit', '-l', type=int, help='Maximum number of results')
@click.option('--show-full', is_flag=True, help='Show full content instead of truncated')
def search_time(days: Optional[int], start_date: Optional[str], end_date: Optional[str], 
               query: Optional[str], user_id: Optional[str], limit: Optional[int], show_full: bool):
    """Search memories within a time range."""
    try:
        config = Config()
        searcher = MemorySearcher(config)
        
        results = searcher.search_by_time_range(
            days_back=days,
            start_date=start_date,
            end_date=end_date,
            query=query,
            user_id=user_id,
            # limit=limit
        )
        
        # Display results
        max_length = None if show_full else 100
        searcher.display_search_results(results, max_content_length=max_length)
        
    except Exception as e:
        console.print(f"❌ Time range search failed: {str(e)}")

@cli.command()
@click.option('--weeks-back', '-w', type=int, default=1, help='Number of weeks to look back (default: 1)')
@click.option('--user-id', '-u', help='User ID to search')
@click.option('--output', '-o', type=click.Path(), help='Save report data to JSON file')
def weekly_report(weeks_back: int, user_id: Optional[str], output: Optional[str]):
    """Generate data for weekly report."""
    try:
        config = Config()
        searcher = MemorySearcher(config)
        
        report_data = searcher.search_weekly_report_data(
            weeks_back=weeks_back,
            user_id=user_id
        )
        
        # Display summary
        console.print(Panel(
            f"📅 Week: {report_data['week_start']} to {report_data['week_end']}\n"
            f"📝 Current week memories: {report_data['summary']['total_current']}\n"
            f"🔗 Related historical memories: {report_data['summary']['total_related']}",
            title=f"Weekly Report Data (Week {weeks_back} ago)"
        ))
        
        # Show current week memories
        if report_data['week_memories']:
            console.print("\n📅 Current Week Memories:")
            searcher.display_search_results(report_data['week_memories'][:10])
        
        # Show related memories
        if report_data['related_memories']:
            console.print("\n🔗 Related Historical Memories:")
            searcher.display_search_results(report_data['related_memories'][:5])
        
        # Save to file if requested
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            console.print(f"\n💾 Report data saved to: {output}")
        
    except Exception as e:
        console.print(f"❌ Weekly report generation failed: {str(e)}")

@cli.command()
@click.argument('content', type=str)
@click.option('--user-id', '-u', help='User ID to search')
@click.option('--limit', '-l', type=int, help='Maximum number of results')
@click.option('--exclude-days', type=int, help='Exclude recent days from results')
def search_related(content: str, user_id: Optional[str], limit: Optional[int], exclude_days: Optional[int]):
    """Search for memories related to given content."""
    try:
        config = Config()
        searcher = MemorySearcher(config)
        
        # Build exclusion filter if specified
        exclude_range = None
        if exclude_days:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=exclude_days)
            exclude_range = {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            }
        
        results = searcher.search_related_to_content(
            content=content,
            user_id=user_id,
            exclude_time_range=exclude_range,
            # limit=limit
        )
        
        # Display results
        searcher.display_search_results(results)
        
    except Exception as e:
        console.print(f"❌ Related content search failed: {str(e)}")

@cli.command()
@click.option('--user-id', '-u', help='User ID to get stats for')
def stats(user_id: Optional[str]):
    """Show user memory statistics."""
    try:
        config = Config()
        searcher = MemorySearcher(config)
        
        stats_data = searcher.get_user_stats(user_id)
        
        # Create stats table
        table = Table(title="📊 Memory Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("User ID", stats_data["user_id"])
        table.add_row("Total Memories", str(stats_data["total_memories"]))
        table.add_row("Recent (7 days)", str(stats_data["recent_memories_7d"]))
        
        console.print(table)
        
        # Sources breakdown
        if stats_data["sources"]:
            console.print("\n📋 Sources:")
            for source, count in stats_data["sources"].items():
                console.print(f"  • {source}: {count}")
        
        # Extract modes breakdown
        if stats_data["extract_modes"]:
            console.print("\n⚙️  Extract Modes:")
            for mode, count in stats_data["extract_modes"].items():
                console.print(f"  • {mode}: {count}")
        
    except Exception as e:
        console.print(f"❌ Stats retrieval failed: {str(e)}")

@cli.command()
def config_check():
    """Check configuration and API connectivity."""
    try:
        config = Config()
        
        console.print("🔧 Configuration Check:")
        console.print(f"  • API Key: {'✅ Set' if config.mem0_api_key else '❌ Missing'}")
        console.print(f"  • Default User ID: {config.default_user_id}")
        console.print(f"  • Extract Mode: {config.default_extract_mode}")
        console.print(f"  • Supported Formats: {', '.join(config.supported_formats)}")
        
        # Test API connectivity
        if config.mem0_api_key:
            from core.uploader import MemoryUploader
            uploader = MemoryUploader(config)
            console.print("  • API Connection: ✅ Connected")
        else:
            console.print("  • API Connection: ❌ No API key")
            console.print("\n💡 Please set MEM0_API_KEY environment variable")
        
    except Exception as e:
        console.print(f"❌ Configuration check failed: {str(e)}")

if __name__ == '__main__':
    cli() 