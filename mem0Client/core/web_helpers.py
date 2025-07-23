"""Web interface helper functions and utilities."""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from core.utils import ResultDisplayer, DateTimeHelper


def perform_search(searcher, query: str, user_id: str, limit: int = 10):
    """Perform a search and display results."""
    try:
        with st.spinner("Searching..."):
            results = searcher.search_by_query(
                query=query,
                user_id=user_id,
                # limit=limit
            )
        
        display_search_results(results, f"🔍 Search Results for: '{query}'")
        
    except Exception as e:
        st.error(f"❌ Search failed: {str(e)}")


def perform_time_search(searcher, user_id: str, days_back: Optional[int] = None, 
                       start_date: Optional[str] = None, end_date: Optional[str] = None,
                       query: Optional[str] = None):
    """Perform time-based search and display results."""
    try:
        with st.spinner("Searching..."):
            results = searcher.search_by_time_range(
                days_back=days_back,
                start_date=start_date,
                end_date=end_date,
                query=query,
                user_id=user_id
            )
        
        time_desc = f"{days_back} days ago" if days_back else f"{start_date} to {end_date}"
        title = f"📅 Time Search Results: {time_desc}"
        if query:
            title += f" (Query: '{query}')"
        
        display_search_results(results, title)
        
    except Exception as e:
        st.error(f"❌ Time search failed: {str(e)}")


def generate_weekly_report(searcher, weeks_back: int, user_id: str):
    """Generate and display weekly report."""
    try:
        with st.spinner("Generating report..."):
            report_data = searcher.search_weekly_report_data(
                weeks_back=weeks_back,
                user_id=user_id
            )
        
        # Report summary
        st.subheader(f"📊 Weekly Report (Week {weeks_back} ago)")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Week Period", f"{report_data['week_start']} to {report_data['week_end']}")
        with col2:
            st.metric("Current Week Memories", report_data['summary']['total_current'])
        with col3:
            st.metric("Related Historical", report_data['summary']['total_related'])
        
        # Current week memories
        if report_data['week_memories']:
            st.subheader("📅 Current Week Memories")
            display_search_results(report_data['week_memories'][:10], "")
        
        # Related memories
        if report_data['related_memories']:
            st.subheader("🔗 Related Historical Memories")
            display_search_results(report_data['related_memories'][:5], "")
        
        # Download report data
        if st.button("💾 Download Report Data"):
            st.download_button(
                label="📄 Download JSON",
                data=json.dumps(report_data, indent=2, ensure_ascii=False),
                file_name=f"weekly_report_{report_data['week_start']}.json",
                mime="application/json"
            )
        
    except Exception as e:
        st.error(f"❌ Report generation failed: {str(e)}")


def display_search_results(results: List[Dict[str, Any]], title: str):
    """Display search results in a table."""
    if not results:
        st.info("📭 No results found")
        return
    
    if title:
        st.subheader(title)
    
    # Convert to DataFrame for better display
    data = ResultDisplayer.prepare_dataframe_data(results)
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    # Detailed view
    if st.checkbox("📋 Show Detailed View"):
        for i, result in enumerate(results[:5]):  # Limit to first 5 for performance
            with st.expander(f"Memory {i+1}: {result.get('id', 'N/A')[:8]}"):
                st.text_area("Content", result.get('memory', ''), height=100, key=f"content_{i}")
                
                metadata = result.get('metadata', {})
                if metadata:
                    st.json(metadata)


def show_stats(searcher, user_id: str):
    """Show user statistics."""
    try:
        with st.spinner("Loading stats..."):
            stats = searcher.get_user_stats(user_id)
        
        st.subheader("📊 User Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Memories", stats['total_memories'])
        with col2:
            st.metric("Recent (7 days)", stats['recent_memories_7d'])
        with col3:
            st.metric("User ID", stats['user_id'])
        
        # Sources chart
        if stats['sources']:
            st.subheader("📋 Sources Breakdown")
            source_df = pd.DataFrame(list(stats['sources'].items()), columns=['Source', 'Count'])
            st.bar_chart(source_df.set_index('Source'))
        
        # Extract modes
        if stats['extract_modes']:
            st.subheader("⚙️ Extract Modes")
            mode_df = pd.DataFrame(list(stats['extract_modes'].items()), columns=['Mode', 'Count'])
            st.bar_chart(mode_df.set_index('Mode'))
        
    except Exception as e:
        st.error(f"❌ Failed to load stats: {str(e)}")


def create_advanced_settings_ui(settings_key_prefix: str, advanced_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Create advanced settings UI components and return current values."""
    with st.expander("⚙️ Advanced Settings", expanded=advanced_settings.get('advanced_settings_expanded', False)):
        col1, col2 = st.columns(2)
        
        with col1:
            custom_instructions = st.text_area(
                "自定义指令 (Custom Instructions)",
                value=advanced_settings.get(f'{settings_key_prefix}_custom_instructions', ''),
                placeholder="例如：请专注于提取技术相关的信息，忽略日常闲聊内容...",
                help="指导AI如何处理和提取记忆内容的自定义指令",
                height=80,
                key=f"{settings_key_prefix}_custom_instructions_input"
            )
            
            includes = st.text_input(
                "包含内容 (Includes)",
                value=advanced_settings.get(f'{settings_key_prefix}_includes', ''),
                placeholder="例如：技术知识, 工作经验, 项目信息",
                help="指定要特别包含的信息类型，用逗号分隔",
                key=f"{settings_key_prefix}_includes_input"
            )
            
            # Infer setting
            infer = st.checkbox(
                "推理记忆 (Infer Memories)",
                value=advanced_settings.get(f'{settings_key_prefix}_infer', True),
                help="True: AI会智能推理和提取记忆；False: 存储原始消息内容",
                key=f"{settings_key_prefix}_infer_input"
            )
        
        with col2:
            excludes = st.text_input(
                "排除内容 (Excludes)",
                value=advanced_settings.get(f'{settings_key_prefix}_excludes', ''),
                placeholder="例如：个人信息, 敏感数据, 隐私内容",
                help="指定要排除的信息类型，用逗号分隔",
                key=f"{settings_key_prefix}_excludes_input"
            )
            
            # 预设的排除选项
            exclude_presets = st.multiselect(
                "常用排除选项",
                ["个人姓名", "联系方式", "地址信息", "财务信息", "密码/秘钥", "身份证号", "其他敏感信息"],
                default=advanced_settings.get(f'{settings_key_prefix}_exclude_presets', []),
                help="选择常用的排除类型，会自动添加到排除内容中",
                key=f"{settings_key_prefix}_exclude_presets_input"
            )
    
    # Update session state
    updated_settings = {
        f'{settings_key_prefix}_custom_instructions': custom_instructions,
        f'{settings_key_prefix}_includes': includes,
        f'{settings_key_prefix}_excludes': excludes,
        f'{settings_key_prefix}_exclude_presets': exclude_presets,
        f'{settings_key_prefix}_infer': infer,
        'advanced_settings_expanded': True
    }
    
    return {
        'custom_instructions': custom_instructions,
        'includes': includes,
        'excludes': excludes,
        'exclude_presets': exclude_presets,
        'infer': infer,
        'updated_settings': updated_settings
    }


def create_metadata_ui() -> Dict[str, str]:
    """Create metadata input UI and return values."""
    with st.expander("🏷️ Additional Metadata (Optional)"):
        col1, col2 = st.columns(2)
        with col1:
            source_tag = st.text_input("Source", placeholder="e.g., meeting, idea, note")
        with col2:
            category_tag = st.text_input("Category", placeholder="e.g., work, personal, research")
    
    metadata = {}
    if source_tag:
        metadata['source_tag'] = source_tag
    if category_tag:
        metadata['category_tag'] = category_tag
    
    return metadata


def process_exclude_presets(excludes: str, exclude_presets: List[str]) -> str:
    """Process exclude presets and combine with manual excludes."""
    preset_mapping = {
        "个人姓名": "personal names, individual names",
        "联系方式": "contact information, phone numbers, email addresses",
        "地址信息": "addresses, location information",
        "财务信息": "financial information, bank details, payment info",
        "密码/秘钥": "passwords, keys, credentials, tokens",
        "身份证号": "ID numbers, identification numbers",
        "其他敏感信息": "sensitive personal information, confidential data"
    }
    
    final_excludes = excludes
    if exclude_presets:
        preset_excludes = ", ".join([preset_mapping.get(preset, preset) for preset in exclude_presets])
        if final_excludes:
            final_excludes = f"{final_excludes}, {preset_excludes}"
        else:
            final_excludes = preset_excludes
    
    return final_excludes 