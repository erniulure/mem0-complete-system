#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mem0 API 补丁模块
修复API中的多用户隔离问题
"""

import requests
import streamlit as st
from typing import Dict, Any, Optional

class MemoryAPIPatched:
    """修复了多用户隔离问题的Memory API类"""
    
    @staticmethod
    def get_api_url():
        """获取API地址"""
        if hasattr(st.session_state, 'api_base_url'):
            return st.session_state.api_base_url
        import os
        return os.getenv('MEM0_API_URL', 'http://localhost:8888')
    
    @staticmethod
    def reset_user_memories(user_id: str) -> Dict[str, Any]:
        """
        重置指定用户的记忆（而不是所有用户的记忆）
        这是对原始reset API的安全补丁
        """
        try:
            api_url = MemoryAPIPatched.get_api_url()
            
            # 首先获取该用户的所有记忆
            memories_response = requests.get(
                f"{api_url}/memories",
                params={"user_id": user_id},
                timeout=30
            )
            memories_response.raise_for_status()
            memories_data = memories_response.json()
            
            # 处理API响应格式
            if isinstance(memories_data, dict) and 'results' in memories_data:
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    all_memories = memories_data['results']['results']
                else:
                    all_memories = memories_data['results']
            elif isinstance(memories_data, list):
                all_memories = memories_data
            else:
                all_memories = []
            
            if not all_memories:
                return {
                    "message": f"用户 {user_id} 没有记忆需要清空",
                    "deleted_count": 0,
                    "status": "success"
                }
            
            # 逐个删除该用户的记忆
            deleted_count = 0
            failed_deletions = []
            
            for memory in all_memories:
                memory_id = memory.get('id')
                if memory_id:
                    try:
                        delete_response = requests.delete(
                            f"{api_url}/memories/{memory_id}",
                            timeout=10
                        )
                        if delete_response.status_code == 200:
                            deleted_count += 1
                        else:
                            failed_deletions.append(memory_id)
                    except Exception as e:
                        failed_deletions.append(f"{memory_id} (错误: {str(e)})")
            
            result = {
                "message": f"已删除用户 {user_id} 的 {deleted_count} 条记忆",
                "deleted_count": deleted_count,
                "total_memories": len(all_memories),
                "status": "success" if not failed_deletions else "partial_success"
            }
            
            if failed_deletions:
                result["failed_deletions"] = failed_deletions
                result["message"] += f"，{len(failed_deletions)} 条删除失败"
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {
                "message": f"API请求失败: {str(e)}",
                "deleted_count": 0,
                "status": "error"
            }
        except Exception as e:
            return {
                "message": f"删除过程中发生错误: {str(e)}",
                "deleted_count": 0,
                "status": "error"
            }
    
    @staticmethod
    def get_user_memory_stats(user_id: str) -> Dict[str, Any]:
        """获取用户记忆统计信息"""
        try:
            api_url = MemoryAPIPatched.get_api_url()
            
            # 获取用户的所有记忆
            memories_response = requests.get(
                f"{api_url}/memories",
                params={"user_id": user_id},
                timeout=30
            )
            memories_response.raise_for_status()
            memories_data = memories_response.json()
            
            # 处理API响应格式
            if isinstance(memories_data, dict) and 'results' in memories_data:
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    all_memories = memories_data['results']['results']
                else:
                    all_memories = memories_data['results']
            elif isinstance(memories_data, list):
                all_memories = memories_data
            else:
                all_memories = []
            
            # 计算统计信息
            from datetime import datetime, date
            
            total_memories = len(all_memories)
            today = date.today().isoformat()
            today_added = sum(1 for memory in all_memories 
                            if memory.get('created_at', '').startswith(today))
            
            # 按日期分组
            date_groups = {}
            for memory in all_memories:
                created_at = memory.get('created_at', '')
                if created_at:
                    memory_date = created_at.split('T')[0]  # 提取日期部分
                    if memory_date not in date_groups:
                        date_groups[memory_date] = 0
                    date_groups[memory_date] += 1
            
            return {
                "user_id": user_id,
                "total_memories": total_memories,
                "today_added": today_added,
                "date_groups": date_groups,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "total_memories": 0,
                "today_added": 0,
                "date_groups": {},
                "status": "error",
                "error": str(e)
            }
    
    @staticmethod
    def verify_user_isolation(user_id: str) -> Dict[str, Any]:
        """验证用户数据隔离是否正常工作"""
        try:
            api_url = MemoryAPIPatched.get_api_url()
            
            # 测试获取指定用户的记忆
            memories_response = requests.get(
                f"{api_url}/memories",
                params={"user_id": user_id},
                timeout=10
            )
            
            if memories_response.status_code == 200:
                memories_data = memories_response.json()
                
                # 验证返回的记忆是否都属于指定用户
                if isinstance(memories_data, dict) and 'results' in memories_data:
                    if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                        all_memories = memories_data['results']['results']
                    else:
                        all_memories = memories_data['results']
                elif isinstance(memories_data, list):
                    all_memories = memories_data
                else:
                    all_memories = []
                
                # 检查是否有其他用户的数据泄露
                foreign_memories = []
                for memory in all_memories:
                    memory_user_id = memory.get('user_id')
                    if memory_user_id and memory_user_id != user_id:
                        foreign_memories.append({
                            'memory_id': memory.get('id'),
                            'foreign_user_id': memory_user_id
                        })
                
                return {
                    "user_id": user_id,
                    "isolation_status": "secure" if not foreign_memories else "compromised",
                    "total_memories": len(all_memories),
                    "foreign_memories": foreign_memories,
                    "status": "success"
                }
            else:
                return {
                    "user_id": user_id,
                    "isolation_status": "unknown",
                    "status": "error",
                    "error": f"API返回状态码: {memories_response.status_code}"
                }
                
        except Exception as e:
            return {
                "user_id": user_id,
                "isolation_status": "unknown",
                "status": "error",
                "error": str(e)
            }

class SecurityUtils:
    """安全工具类"""
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """验证用户ID格式是否安全"""
        if not user_id or not isinstance(user_id, str):
            return False
        
        # 检查长度
        if len(user_id) < 3 or len(user_id) > 50:
            return False
        
        # 检查字符（只允许字母、数字、下划线、连字符）
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            return False
        
        # 禁止的用户ID
        forbidden_ids = ['admin', 'root', 'system', 'anonymous', 'guest', 'test', 'demo']
        if user_id.lower() in forbidden_ids:
            return False
        
        return True
    
    @staticmethod
    def sanitize_user_input(text: str) -> str:
        """清理用户输入"""
        if not text:
            return ""
        
        # 移除潜在的危险字符
        import re
        # 保留中文、英文、数字、常用标点符号
        sanitized = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()[\]{}"\'`~@#$%^&*+=|\\/<>-]', '', text)
        
        # 限制长度
        return sanitized[:1000]
    
    @staticmethod
    def log_security_event(event_type: str, user_id: str, details: str):
        """记录安全事件"""
        from datetime import datetime
        import json
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "details": details,
                "ip_address": "unknown"  # 在实际部署中可以获取真实IP
            }
            
            # 写入安全日志文件
            log_file = "security.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            # 记录日志失败不应该影响主要功能
            print(f"安全日志记录失败: {e}")

def apply_security_patches():
    """应用安全补丁"""
    
    # 在session state中标记已应用补丁
    if 'security_patches_applied' not in st.session_state:
        st.session_state.security_patches_applied = True
        
        # 记录补丁应用事件
        SecurityUtils.log_security_event(
            "security_patch_applied",
            st.session_state.get('user_settings', {}).get('user_id', 'unknown'),
            "多用户隔离安全补丁已应用"
        )
    
    return True
