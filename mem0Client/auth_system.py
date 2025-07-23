#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mem0 记忆管理系统 - 用户验证和多用户隔离模块
支持多种验证方式：简单密码、JWT Token、OAuth等
"""

import streamlit as st
import streamlit.components.v1
import hashlib
import hmac
import jwt
import time
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

# 导入持久化会话管理器
from persistent_session import PersistentSessionManager
from session_checker import SessionChecker

class AuthConfig:
    """认证配置类"""

    def __init__(self):
        # 从环境变量或配置文件加载
        self.auth_mode = os.getenv('MEM0_AUTH_MODE', 'simple')  # simple, jwt, oauth
        self.secret_key = os.getenv('MEM0_SECRET_KEY', 'mem0-default-secret-key-change-in-production')
        self.session_timeout = int(os.getenv('MEM0_SESSION_TIMEOUT', '3600'))  # 1小时
        self.max_login_attempts = int(os.getenv('MEM0_MAX_LOGIN_ATTEMPTS', '5'))
        self.lockout_duration = int(os.getenv('MEM0_LOCKOUT_DURATION', '300'))  # 5分钟

        # 用户数据存储模式：只支持数据库
        self.storage_mode = 'database'

        # 默认管理员账户
        self.default_admin = {
            'username': os.getenv('MEM0_ADMIN_USER', 'admin'),
            'password': os.getenv('MEM0_ADMIN_PASS', 'admin123'),
            'role': 'admin'
        }

class UserManager:
    """用户管理类"""

    def __init__(self, config: AuthConfig):
        self.config = config
        # 导入数据库用户管理器
        try:
            from core.db_user_manager import DatabaseUserManager
            self.db_manager = DatabaseUserManager()
        except ImportError as e:
            st.error(f"❌ 无法导入数据库用户管理器: {e}")
            raise
        

    
    def register_user(self, username: str, password: str, role: str = 'user') -> Tuple[bool, str]:
        """注册新用户"""
        return self.db_manager.register_user(username, password, role)
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """用户认证"""
        return self.db_manager.authenticate_user(username, password)
    

    
    def get_user_list(self) -> List[Dict]:
        """获取用户列表（管理员功能）"""
        return self.db_manager.get_user_list()
    
    def update_user_status(self, username: str, is_active: bool) -> bool:
        """更新用户状态（管理员功能）"""
        return self.db_manager.set_user_active(username, is_active)

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改用户密码"""
        return self.db_manager.change_password(username, old_password, new_password)

    def reset_user_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """重置用户密码（管理员功能）"""
        return self.db_manager.reset_user_password(username, new_password)

    def delete_user(self, username: str) -> Tuple[bool, str]:
        """删除用户（管理员功能）"""
        return self.db_manager.delete_user(username)

class AuthSystem:
    """认证系统主类"""

    def __init__(self):
        self.config = AuthConfig()
        self.user_manager = UserManager(self.config)
        self.session_manager = PersistentSessionManager()
        self.session_checker = SessionChecker()

        # 初始化session state - 使用Streamlit内置会话管理
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.session_state.login_time = None




    
    def is_authenticated(self) -> bool:
        """检查用户是否已认证（支持持久化会话）"""
        # 首先检查内存中的认证状态
        if st.session_state.get('authenticated', False):
            # 检查会话是否过期
            if st.session_state.get('login_time'):
                login_time = datetime.fromisoformat(st.session_state.login_time)
                if datetime.now() - login_time > timedelta(seconds=self.config.session_timeout):
                    self.logout()
                    return False
            return True

        # 如果内存中没有认证状态，检查持久化会话
        return self._check_persistent_session()

    def _check_persistent_session(self) -> bool:
        """检查持久化会话"""
        try:
            # 清理过期会话
            self.session_manager.cleanup_expired_sessions()

            # 从浏览器获取会话ID
            session_id = self.session_checker.check_browser_session()

            if not session_id:
                return False

            # 验证会话
            is_valid, user_info = self.session_manager.validate_session(session_id)

            if is_valid and user_info:
                # 恢复会话状态到内存
                st.session_state.authenticated = True
                st.session_state.user_info = user_info
                st.session_state.login_time = datetime.now().isoformat()
                st.session_state.session_id = session_id

                # 更新用户设置
                if 'user_settings' not in st.session_state:
                    st.session_state.user_settings = {}
                st.session_state.user_settings['user_id'] = user_info['user_id']

                return True

            return False

        except Exception as e:
            st.error(f"检查持久化会话失败: {e}")
            return False

    def get_current_user(self) -> Optional[Dict]:
        """获取当前用户信息"""
        if self.is_authenticated():
            return st.session_state.user_info
        return None
    
    def get_current_user_id(self) -> str:
        """获取当前用户ID"""
        user = self.get_current_user()
        if user:
            return user.get('user_id', user.get('username', 'anonymous'))
        return 'anonymous'
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """用户登录（支持持久化会话）"""
        success, message, user_info = self.user_manager.authenticate_user(username, password)

        if success:
            # 设置内存会话状态
            st.session_state.authenticated = True
            st.session_state.user_info = user_info
            st.session_state.login_time = datetime.now().isoformat()

            # 创建持久化会话
            session_id = self.session_manager.create_session(user_info)
            if session_id:
                st.session_state.session_id = session_id
                # 在浏览器中设置会话ID
                self.session_checker.set_session_in_browser(session_id)

            # 更新用户设置中的user_id
            if 'user_settings' not in st.session_state:
                st.session_state.user_settings = {}
            st.session_state.user_settings['user_id'] = user_info['user_id']

            # 重新运行页面
            st.rerun()

        return success, message
    
    def logout(self):
        """用户登出（清除持久化会话）"""
        # 销毁持久化会话
        if st.session_state.get('session_id'):
            self.session_manager.destroy_session(st.session_state.session_id)

        # 清除浏览器中的会话
        self.session_checker.clear_session_in_browser()

        # 清除内存会话状态
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.login_time = None
        st.session_state.session_id = None

        # 清除用户设置
        if 'user_settings' in st.session_state:
            st.session_state.user_settings['user_id'] = 'anonymous'

        # 重置会话检查状态
        self.session_checker.reset_check_state()

        # 简单重新运行
        st.rerun()
    
    def register(self, username: str, password: str, confirm_password: str) -> Tuple[bool, str]:
        """用户注册"""
        if password != confirm_password:
            return False, "两次输入的密码不一致"
        
        return self.user_manager.register_user(username, password)
    
    def require_auth(self, redirect_to_login: bool = True) -> bool:
        """要求用户认证装饰器"""
        if not self.is_authenticated():
            if redirect_to_login:
                self.show_login_page()
                st.stop()
            return False
        return True
    
    def require_admin(self) -> bool:
        """要求管理员权限"""
        if not self.is_authenticated():
            self.show_login_page()
            st.stop()
        
        user = self.get_current_user()
        if user.get('role') != 'admin':
            st.error("❌ 需要管理员权限")
            st.stop()
        
        return True
    
    def show_login_page(self):
        """显示登录页面"""
        st.title("🔐 Mem0 记忆管理系统 - 用户登录")
        
        # 创建标签页
        tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
        
        with tab1:
            self._show_login_form()
        
        with tab2:
            self._show_register_form()
    
    def _show_login_form(self):
        """显示登录表单"""
        st.subheader("用户登录")
        
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                login_button = st.form_submit_button("🔑 登录", type="primary")
            with col2:
                if st.form_submit_button("🔄 重置"):
                    st.rerun()
            
            if login_button:
                if username and password:
                    success, message = self.login(username, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("请输入用户名和密码")
        
        # 显示默认管理员信息
        with st.expander("ℹ️ 默认管理员账户"):
            st.info(f"""
            **默认管理员账户:**
            - 用户名: `{self.config.default_admin['username']}`
            - 密码: `{self.config.default_admin['password']}`
            
            ⚠️ **安全提醒**: 首次登录后请立即修改默认密码！
            """)
    
    def _show_register_form(self):
        """显示注册表单"""
        st.subheader("用户注册")
        
        with st.form("register_form"):
            username = st.text_input("用户名", placeholder="请输入用户名（3-20个字符）")
            password = st.text_input("密码", type="password", placeholder="请输入密码（至少6位）")
            confirm_password = st.text_input("确认密码", type="password", placeholder="请再次输入密码")
            
            register_button = st.form_submit_button("📝 注册", type="secondary")
            
            if register_button:
                if username and password and confirm_password:
                    success, message = self.register(username, password, confirm_password)
                    if success:
                        st.success(message)
                        st.info("注册成功！请切换到登录标签页进行登录。")
                    else:
                        st.error(message)
                else:
                    st.warning("请填写所有字段")
    
    def show_user_info(self):
        """显示用户信息"""
        if self.is_authenticated():
            user = self.get_current_user()

            with st.sidebar:
                st.markdown("---")
                st.markdown("### 👤 用户信息")
                st.write(f"**用户名**: {user['username']}")
                st.write(f"**用户ID**: {user['user_id']}")
                st.write(f"**角色**: {user['role']}")

                # 修改密码按钮
                if st.button("🔑 修改密码", type="secondary"):
                    st.session_state.show_change_password = True
                    st.rerun()

                # 管理员功能
                if user.get('role') == 'admin':
                    if st.button("� 用户管理", type="secondary"):
                        st.session_state.show_admin_panel = True
                        st.rerun()

                if st.button("�🚪 退出登录", type="secondary"):
                    self.logout()
                    st.rerun()

    def show_change_password_dialog(self):
        """显示修改密码对话框"""
        if not st.session_state.get('show_change_password', False):
            return

        st.markdown("### 🔑 修改密码")

        with st.form("change_password_form"):
            old_password = st.text_input("原密码", type="password")
            new_password = st.text_input("新密码", type="password", help="至少6位字符")
            confirm_password = st.text_input("确认新密码", type="password")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.form_submit_button("✅ 确认修改", type="primary"):
                    if new_password != confirm_password:
                        st.error("两次输入的新密码不一致")
                    elif old_password and new_password:
                        user = self.get_current_user()
                        success, message = self.user_manager.change_password(
                            user['username'], old_password, new_password
                        )
                        if success:
                            st.success(message)
                            st.session_state.show_change_password = False
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.warning("请填写所有字段")

            with col2:
                if st.form_submit_button("❌ 取消"):
                    st.session_state.show_change_password = False
                    st.rerun()

    def show_admin_panel(self):
        """显示管理员面板"""
        if not st.session_state.get('show_admin_panel', False):
            return

        user = self.get_current_user()
        if not user or user.get('role') != 'admin':
            st.error("❌ 需要管理员权限")
            return

        st.markdown("## 👥 用户管理面板")

        # 关闭按钮
        if st.button("❌ 关闭管理面板"):
            st.session_state.show_admin_panel = False
            st.rerun()

        # 用户列表
        st.markdown("### 📋 用户列表")
        users = self.user_manager.get_user_list()

        if users:
            # 创建用户表格
            user_data = []
            for user_info in users:
                user_data.append({
                    "用户名": user_info['username'],
                    "用户ID": user_info['user_id'],
                    "角色": user_info['role'],
                    "状态": "✅ 活跃" if user_info['is_active'] else "❌ 禁用",
                    "创建时间": user_info['created_at'][:10] if user_info['created_at'] else "未知",
                    "最后登录": user_info['last_login'][:10] if user_info['last_login'] else "从未登录"
                })

            df = pd.DataFrame(user_data)
            st.dataframe(df, use_container_width=True)

            # 用户操作
            st.markdown("### 🔧 用户操作")

            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("#### 重置密码")
                with st.form("reset_password_form"):
                    username = st.selectbox("选择用户", [u['username'] for u in users if u['role'] != 'admin'])
                    new_password = st.text_input("新密码", type="password", help="至少6位字符")

                    if st.form_submit_button("🔄 重置密码", type="primary"):
                        if username and new_password:
                            success, message = self.user_manager.reset_user_password(username, new_password)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
                        else:
                            st.warning("请填写所有字段")

            with col2:
                st.markdown("#### 用户状态管理")
                with st.form("user_status_form"):
                    username = st.selectbox("选择用户", [u['username'] for u in users if u['role'] != 'admin'], key="status_user")
                    action = st.radio("操作", ["启用用户", "禁用用户", "删除用户"])

                    if st.form_submit_button("✅ 执行操作", type="secondary"):
                        if username:
                            if action == "启用用户":
                                success = self.user_manager.update_user_status(username, True)
                                if success:
                                    st.success(f"用户 {username} 已启用")
                                    st.rerun()
                            elif action == "禁用用户":
                                success = self.user_manager.update_user_status(username, False)
                                if success:
                                    st.warning(f"用户 {username} 已禁用")
                                    st.rerun()
                            elif action == "删除用户":
                                success, message = self.user_manager.delete_user(username)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        else:
                            st.warning("请选择用户")
        else:
            st.info("暂无用户数据")

        # 系统统计
        st.markdown("### 📊 系统统计")
        col1, col2, col3 = st.columns(3)

        with col1:
            total_users = len(users)
            st.metric("总用户数", total_users)

        with col2:
            active_users = len([u for u in users if u['is_active']])
            st.metric("活跃用户", active_users)

        with col3:
            admin_users = len([u for u in users if u['role'] == 'admin'])
            st.metric("管理员数", admin_users)
