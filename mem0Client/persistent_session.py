#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
持久化会话管理系统
解决页面刷新后需要重新登录的问题
"""

import streamlit as st
import streamlit.components.v1 as components
import hashlib
import hmac
import jwt
import time
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
import psycopg2
from psycopg2.extras import RealDictCursor

class PersistentSessionManager:
    """持久化会话管理器"""
    
    def __init__(self):
        self.secret_key = os.getenv('MEM0_SECRET_KEY', 'mem0-default-secret-key-change-in-production')
        self.session_timeout = int(os.getenv('MEM0_SESSION_TIMEOUT', '86400'))  # 24小时
        
        # 数据库配置
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'mem0'),
            'user': os.getenv('POSTGRES_USER', 'mem0'),
            'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024')
        }
        
        # 初始化会话表
        self._init_session_table()
    
    def _init_session_table(self):
        """初始化会话表"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 创建会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    user_info JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id 
                ON user_sessions(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at 
                ON user_sessions(expires_at)
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"初始化会话表失败: {e}")
    
    def create_session(self, user_info: Dict) -> str:
        """创建新会话"""
        try:
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 计算过期时间
            expires_at = datetime.now() + timedelta(seconds=self.session_timeout)
            
            # 保存到数据库
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_sessions 
                (session_id, user_id, username, user_info, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                session_id,
                user_info['user_id'],
                user_info['username'],
                json.dumps(user_info),
                expires_at
            ))
            
            conn.commit()
            conn.close()
            
            # 保存到浏览器localStorage
            self._save_session_to_browser(session_id)
            
            return session_id
            
        except Exception as e:
            st.error(f"创建会话失败: {e}")
            return None
    
    def _save_session_to_browser(self, session_id: str):
        """保存会话ID到浏览器localStorage"""
        js_code = f"""
        <script>
        localStorage.setItem('mem0_session_id', '{session_id}');
        console.log('Session saved to localStorage:', '{session_id}');
        </script>
        """
        components.html(js_code, height=0)
    
    def _get_session_from_browser(self) -> Optional[str]:
        """从浏览器localStorage获取会话ID"""
        js_code = """
        <script>
        const sessionId = localStorage.getItem('mem0_session_id');
        if (sessionId) {
            window.parent.postMessage({
                type: 'session_id',
                session_id: sessionId
            }, '*');
        }
        </script>
        """
        
        # 使用隐藏的组件来执行JavaScript
        result = components.html(js_code, height=0)
        
        # 检查session_state中是否有会话ID
        return st.session_state.get('browser_session_id')
    
    def validate_session(self, session_id: str) -> Tuple[bool, Optional[Dict]]:
        """验证会话有效性"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 查询会话信息
            cursor.execute("""
                SELECT * FROM user_sessions 
                WHERE session_id = %s AND is_active = TRUE
            """, (session_id,))
            
            session = cursor.fetchone()
            
            if not session:
                conn.close()
                return False, None
            
            # 检查是否过期
            if datetime.now() > session['expires_at']:
                # 标记会话为无效
                cursor.execute("""
                    UPDATE user_sessions 
                    SET is_active = FALSE 
                    WHERE session_id = %s
                """, (session_id,))
                conn.commit()
                conn.close()
                return False, None
            
            # 更新最后活动时间
            cursor.execute("""
                UPDATE user_sessions 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = %s
            """, (session_id,))
            
            conn.commit()
            conn.close()
            
            # 解析用户信息
            user_info_data = session['user_info']
            if isinstance(user_info_data, str):
                user_info = json.loads(user_info_data)
            else:
                user_info = user_info_data
            
            return True, user_info
            
        except Exception as e:
            st.error(f"验证会话失败: {e}")
            return False, None
    
    def destroy_session(self, session_id: str):
        """销毁会话"""
        try:
            # 从数据库中删除
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE session_id = %s
            """, (session_id,))
            
            conn.commit()
            conn.close()
            
            # 从浏览器localStorage中删除
            self._remove_session_from_browser()
            
        except Exception as e:
            st.error(f"销毁会话失败: {e}")
    
    def _remove_session_from_browser(self):
        """从浏览器localStorage中删除会话"""
        js_code = """
        <script>
        localStorage.removeItem('mem0_session_id');
        console.log('Session removed from localStorage');
        </script>
        """
        components.html(js_code, height=0)
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE expires_at < CURRENT_TIMESTAMP AND is_active = TRUE
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"清理过期会话失败: {e}")
    
    def get_active_sessions(self, user_id: str) -> List[Dict]:
        """获取用户的活跃会话"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT session_id, created_at, last_activity, expires_at
                FROM user_sessions 
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY last_activity DESC
            """, (user_id,))
            
            sessions = cursor.fetchall()
            conn.close()
            
            return [dict(session) for session in sessions]
            
        except Exception as e:
            st.error(f"获取活跃会话失败: {e}")
            return []
