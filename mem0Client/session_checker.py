#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
会话检查组件
用于在页面加载时检查浏览器中的会话信息
"""

import streamlit as st
import streamlit.components.v1 as components
import time

class SessionChecker:
    """会话检查器"""
    
    def __init__(self):
        self.check_timeout = 3  # 3秒超时
    
    def check_browser_session(self) -> str:
        """检查浏览器中的会话ID（简化版本）"""

        # 如果已经检查过，直接返回
        if hasattr(st.session_state, 'session_check_done'):
            return st.session_state.get('browser_session_id', '')

        # 使用URL参数传递会话ID（更可靠的方法）
        query_params = st.query_params
        if 'session_id' in query_params:
            st.session_state.browser_session_id = query_params['session_id']
            st.session_state.session_check_done = True
            return query_params['session_id']

        # 标记检查完成
        st.session_state.session_check_done = True
        return ''
    
    def set_session_in_browser(self, session_id: str):
        """在浏览器中设置会话ID（通过URL参数）"""
        # 设置到session_state
        st.session_state.browser_session_id = session_id

        # 通过URL参数传递（在下次页面加载时生效）
        st.query_params['session_id'] = session_id
    
    def clear_session_in_browser(self):
        """清除浏览器中的会话ID"""
        # 清除session_state
        if 'browser_session_id' in st.session_state:
            del st.session_state.browser_session_id

        # 清除URL参数
        if 'session_id' in st.query_params:
            del st.query_params['session_id']
    
    def reset_check_state(self):
        """重置检查状态"""
        if 'session_check_done' in st.session_state:
            del st.session_state.session_check_done
        if 'session_check_start_time' in st.session_state:
            del st.session_state.session_check_start_time
        if 'browser_session_id' in st.session_state:
            del st.session_state.browser_session_id
