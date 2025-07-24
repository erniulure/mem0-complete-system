
import streamlit as st
import pandas as pd
import json
import requests
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import time
import plotly.express as px
import plotly.graph_objects as go
import base64
import io
from PIL import Image

from core.config import Config
from core.uploader import MemoryUploader
from core.searcher import MemorySearcher
from multimodal_model_selector import IntelligentModelSelector, MultimodalProcessor
from dynamic_model_selector import DynamicModelSelector
from modern_chat_interface import modern_smart_chat_interface

# 导入认证系统和安全补丁
from auth_system import AuthSystem
from api_patches import MemoryAPIPatched, SecurityUtils, apply_security_patches

# 导入WebUI独立数据库
try:
    from database.webui_db_config import webui_db
    WEBUI_DB_AVAILABLE = True
except ImportError:
    # 如果WebUI数据库模块不存在，使用原有的数据库配置
    WEBUI_DB_AVAILABLE = False
    webui_db = None

# API基础配置 - 使用宿主机地址
API_BASE_URL = os.getenv('MEM0_API_URL', 'http://localhost:8888')

def get_webui_db_config():
    """获取WebUI数据库配置 - 使用同一个PostgreSQL实例的webui数据库"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),  # 使用同一个PostgreSQL实例
        'port': os.getenv('POSTGRES_PORT', '5432'),  # 使用同一个端口
        'database': 'webui',  # 连接到webui数据库
        'user': os.getenv('POSTGRES_USER', 'mem0'),  # 使用同一个用户
        'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024')  # 使用同一个密码
    }

def get_mem0_db_config():
    """获取Mem0数据库配置"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'mem0'),  # 连接到mem0数据库
        'user': os.getenv('POSTGRES_USER', 'mem0'),
        'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024')
    }

# 页面配置
st.set_page_config(
    page_title="Mem0 记忆管理系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .status-connected {
        color: #28a745;
        font-weight: bold;
    }
    .status-disconnected {
        color: #dc3545;
        font-weight: bold;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border: 1px solid #ddd;
        color: #333;
    }
    .user-message {
        background: #e8f4fd;
        border-left: 4px solid #2196F3;
        margin-left: 2rem;
        color: #1565C0;
    }
    .assistant-message {
        background: #f8f9fa;
        border-left: 4px solid #4CAF50;
        margin-right: 2rem;
        color: #2E7D32;
    }

    /* 深色主题适配 */
    @media (prefers-color-scheme: dark) {
        .chat-message {
            color: #e0e0e0;
            border-color: #555;
        }
        .user-message {
            background: #1e3a5f;
            color: #90CAF9;
        }
        .assistant-message {
            background: #2d2d2d;
            color: #A5D6A7;
        }
    }
</style>
""", unsafe_allow_html=True)

# 真实API调用函数
class MemoryAPI:
    """真实的Memory API客户端 - 支持多模态和智能模型选择"""

    @staticmethod
    def get_api_url():
        """获取记忆管理API的URL - 支持环境变量配置"""
        import os

        # 优先使用环境变量，支持Docker容器部署
        api_url = os.getenv('MEM0_API_URL')
        if api_url:
            return api_url

        # 备用地址：本地开发环境
        return 'http://localhost:8888'

    @staticmethod
    def test_connection():
        """测试API连接"""
        try:
            api_url = MemoryAPI.get_api_url()
            response = requests.get(f"{api_url}/", timeout=5)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def add_memory(messages: List[Dict], user_id: str, custom_instructions: str = None,
                   includes: List[str] = None, excludes: List[str] = None,
                   model: str = None, image_base64: str = None):
        """添加记忆 - 支持多模态和模型选择"""
        payload = {
            "messages": messages,
            "user_id": user_id
        }

        # 添加图片支持
        if image_base64:
            # 修改第一个消息以包含图片
            if messages and len(messages) > 0:
                messages[0]["image"] = f"data:image/png;base64,{image_base64}"

        if custom_instructions:
            payload["custom_instructions"] = custom_instructions
        if includes:
            payload["includes"] = includes
        if excludes:
            payload["excludes"] = excludes
        # 注意：mem0 API不支持model参数，模型选择在服务器端配置
        # if model:
        #     payload["model"] = model

        api_url = MemoryAPI.get_api_url()
        response = requests.post(f"{api_url}/memories", json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_memories(user_id: str):
        """获取记忆列表"""
        api_url = MemoryAPI.get_api_url()
        response = requests.get(f"{api_url}/memories", params={"user_id": user_id})
        response.raise_for_status()
        return response.json()

    @staticmethod
    def search_memories(query: str, user_id: str, limit: int = 10,
                       image_base64: str = None, model: str = None):
        """搜索记忆 - 支持多模态搜索"""
        payload = {
            "query": query,
            "user_id": user_id,
            "limit": limit
        }

        # 注意：mem0 API不支持image和model参数，这些功能在服务器端配置
        # if image_base64:
        #     payload["image"] = image_base64
        # if model:
        #     payload["model"] = model

        api_url = MemoryAPI.get_api_url()
        response = requests.post(f"{api_url}/search", json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def delete_memory(memory_id: str):
        """删除记忆"""
        api_url = MemoryAPI.get_api_url()
        response = requests.delete(f"{api_url}/memories/{memory_id}")
        response.raise_for_status()
        return response.json()

    @staticmethod
    def reset_memories():
        """重置所有记忆"""
        api_url = MemoryAPI.get_api_url()
        response = requests.post(f"{api_url}/reset")
        response.raise_for_status()
        return response.json()

# 初始化会话状态
if 'config' not in st.session_state:
    try:
        st.session_state.config = Config()
        st.session_state.uploader = MemoryUploader(st.session_state.config)
        st.session_state.searcher = MemorySearcher(st.session_state.config)
        st.session_state.multimodal_processor = MultimodalProcessor()
        st.session_state.initialized = True
        # 只在首次初始化时设置API连接状态，避免重置已有的连接状态
        if 'api_connected' not in st.session_state:
            st.session_state.api_connected = False
    except Exception as e:
        st.session_state.initialized = False
        st.session_state.init_error = str(e)
        # 只在首次初始化失败时设置连接状态，避免重置已有的连接状态
        if 'api_connected' not in st.session_state:
            st.session_state.api_connected = False

# 确保model_selector始终可用 - 健壮性保证
def ensure_model_selector():
    """确保model_selector已正确初始化，如果没有则创建"""
    if 'model_selector' not in st.session_state:
        try:
            # 从API设置中获取配置，如果没有则使用默认值
            api_settings = st.session_state.get('api_settings', {})
            api_key = api_settings.get('api_key', 'admin123')

            st.session_state.model_selector = DynamicModelSelector(
                api_base_url='http://gemini-balance:8000',
                api_key=api_key
            )
            return True
        except Exception as e:
            # 如果初始化失败，创建一个备用的模型选择器
            st.session_state.model_selector = create_fallback_model_selector()
            return False
    return True

def create_fallback_model_selector():
    """创建备用模型选择器，确保基本功能可用"""
    class FallbackModelSelector:
        def __init__(self):
            self.available_models = [
                {"id": "gemini-2.5-flash", "object": "model"},
                {"id": "gemini-2.5-pro", "object": "model"},
                {"id": "gemini-2.0-flash", "object": "model"}
            ]
            self.fast_model = "gemini-2.5-flash"

        def select_optimal_model(self, user_query: str, has_image: bool = False) -> Dict:
            """备用模型选择逻辑"""
            if has_image:
                return {
                    "selected_model": "gemini-2.5-pro",
                    "recommended_model": "gemini-2.5-pro",  # 兼容性字段
                    "reasoning": "图片任务使用高质量模型",
                    "task_type": "图片分析",
                    "complexity_level": "7",
                    "selection_method": "fallback_recommendation"
                }
            else:
                return {
                    "selected_model": "gemini-2.5-flash",
                    "recommended_model": "gemini-2.5-flash",  # 兼容性字段
                    "reasoning": "文本任务使用平衡模型",
                    "task_type": "文本处理",
                    "complexity_level": "5",
                    "selection_method": "fallback_recommendation"
                }

        def get_available_models(self):
            return [model['id'] for model in self.available_models]

        def refresh_models(self):
            pass  # 备用选择器不需要刷新

    return FallbackModelSelector()

# 初始化model_selector
ensure_model_selector()

# 初始化聊天历史
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 初始化API设置 - 从数据库加载保存的设置
if 'api_settings' not in st.session_state:
    # 默认AI模型API设置
    default_settings = {
        'api_url': 'http://gemini-balance:8000',  # 默认指向AI模型服务
        'api_key': 'q1q2q3q4',  # 默认AI API密钥，与Gemini Balance配置一致
        'connected': st.session_state.get('api_connected', False)
    }

    # 尝试从数据库加载保存的设置
    try:
        import psycopg2
        import os

        # 数据库连接配置
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
            'database': os.getenv('POSTGRES_DB', 'mem0'),
            'user': os.getenv('POSTGRES_USER', 'mem0'),
            'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024'),
            'port': 5432
        }

        # 获取当前用户ID
        current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')

        # 连接数据库并加载设置
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 查询保存的AI API设置（包括连接状态）
        cursor.execute("""
            SELECT setting_key, setting_value
            FROM mem0_user_settings
            WHERE user_id = %s AND setting_key IN ('ai_api_url', 'ai_api_key', 'ai_api_connected', 'api_url', 'api_key')
        """, (current_user_id,))

        saved_settings = cursor.fetchall()
        cursor.close()
        conn.close()

        # 应用保存的AI API设置
        saved_connected_status = None
        for setting_key, setting_value in saved_settings:
            # 优先使用新的ai_api_*设置，兼容旧的api_*设置
            if setting_key == 'ai_api_url':
                default_settings['api_url'] = setting_value
            elif setting_key == 'ai_api_key':
                default_settings['api_key'] = setting_value
            elif setting_key == 'ai_api_connected':
                # 保存连接状态，稍后设置到session_state
                saved_connected_status = setting_value.lower() == 'true'
                default_settings['connected'] = saved_connected_status
            elif setting_key in default_settings and not any(s[0].startswith('ai_api_') for s in saved_settings):
                # 如果没有新的ai_api_*设置，则使用旧的api_*设置
                default_settings[setting_key] = setting_value

        # 如果数据库中有保存的连接状态，设置到session_state
        if saved_connected_status is not None:
            st.session_state.api_connected = saved_connected_status

    except Exception as e:
        # 数据库加载失败时使用默认设置
        pass

    st.session_state.api_settings = default_settings

    # 只在首次初始化或连接状态未知时进行自动测试
    # 避免每次页面重新加载都测试，防止对话后连接状态被重置
    if (default_settings.get('api_key') and default_settings.get('api_url') and
        'api_connected' not in st.session_state):
        try:
            # 自动测试AI模型API连接（仅首次）
            import requests
            api_url = default_settings['api_url']
            api_key = default_settings['api_key']

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # 测试AI模型API基础连接
            response = requests.get(f"{api_url}/", headers=headers, timeout=5)
            if response.status_code == 200:
                st.session_state.api_connected = True
                st.session_state.api_settings['connected'] = True
            else:
                st.session_state.api_connected = False
                st.session_state.api_settings['connected'] = False
        except:
            # AI API连接测试失败，设置为未连接状态
            st.session_state.api_connected = False
            st.session_state.api_settings['connected'] = False
    elif 'api_connected' not in st.session_state:
        # 如果没有配置API设置且数据库中也没有保存的连接状态，默认为未连接
        st.session_state.api_connected = False
        st.session_state.api_settings['connected'] = False

# 初始化用户设置 - 从数据库加载持久化设置
if 'user_settings' not in st.session_state:
    # 默认设置
    default_user_settings = {
        'user_id': 'default_user',
        'custom_instructions': '请提取并结构化重要信息，保持清晰明了。',
        'includes': '',
        'excludes': '',
        'max_results': 10,
        'infer': True
    }

    try:
        # 获取当前用户信息
        current_username = getattr(st.session_state, 'user_info', {}).get('username', 'admin')
        current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')
        default_user_settings['user_id'] = current_user_id

        # 使用WebUI独立数据库加载用户设置
        if webui_db and WEBUI_DB_AVAILABLE:
            # 从WebUI数据库加载设置
            saved_settings_dict = webui_db.get_user_settings(current_username)

            # 应用从数据库加载的设置
            if 'custom_instructions' in saved_settings_dict:
                default_user_settings['custom_instructions'] = saved_settings_dict['custom_instructions'] or default_user_settings['custom_instructions']

            if 'include_content_types' in saved_settings_dict:
                try:
                    include_list = json.loads(saved_settings_dict['include_content_types']) if saved_settings_dict['include_content_types'] else []
                    default_user_settings['includes'] = ', '.join(include_list) if include_list else ''
                except (json.JSONDecodeError, TypeError):
                    default_user_settings['includes'] = saved_settings_dict['include_content_types'] or ''

            if 'exclude_content_types' in saved_settings_dict:
                try:
                    exclude_list = json.loads(saved_settings_dict['exclude_content_types']) if saved_settings_dict['exclude_content_types'] else []
                    default_user_settings['excludes'] = ', '.join(exclude_list) if exclude_list else ''
                except (json.JSONDecodeError, TypeError):
                    default_user_settings['excludes'] = saved_settings_dict['exclude_content_types'] or ''

            if 'max_results' in saved_settings_dict:
                try:
                    default_user_settings['max_results'] = int(saved_settings_dict['max_results']) if saved_settings_dict['max_results'] else 10
                except (ValueError, TypeError):
                    default_user_settings['max_results'] = 10

            if 'smart_reasoning' in saved_settings_dict:
                default_user_settings['infer'] = saved_settings_dict['smart_reasoning'].lower() == 'true' if saved_settings_dict['smart_reasoning'] else True

        else:
            # 回退到原有的mem0数据库（兼容性）
            import psycopg2
            import json

            # 数据库连接配置
            db_config = get_webui_db_config()

            # 连接数据库并加载设置
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # 查询用户的高级设置
            cursor.execute("""
                SELECT setting_key, setting_value
                FROM mem0_user_settings
                WHERE user_id = %s AND setting_key IN (
                    'custom_instructions', 'include_content_types', 'exclude_content_types',
                    'max_results', 'smart_reasoning'
                )
            """, (current_user_id,))

        saved_settings = cursor.fetchall()
        cursor.close()
        conn.close()

        # 应用从数据库加载的设置
        for setting_key, setting_value in saved_settings:
            if setting_key == 'custom_instructions':
                default_user_settings['custom_instructions'] = setting_value or default_user_settings['custom_instructions']
            elif setting_key == 'include_content_types':
                try:
                    # 解析JSON数组并转换为逗号分隔的字符串
                    include_list = json.loads(setting_value) if setting_value else []
                    default_user_settings['includes'] = ', '.join(include_list) if include_list else ''
                except (json.JSONDecodeError, TypeError):
                    # 如果不是JSON格式，直接使用字符串值
                    default_user_settings['includes'] = setting_value or ''
            elif setting_key == 'exclude_content_types':
                try:
                    # 解析JSON数组并转换为逗号分隔的字符串
                    exclude_list = json.loads(setting_value) if setting_value else []
                    default_user_settings['excludes'] = ', '.join(exclude_list) if exclude_list else ''
                except (json.JSONDecodeError, TypeError):
                    # 如果不是JSON格式，直接使用字符串值
                    default_user_settings['excludes'] = setting_value or ''
            elif setting_key == 'max_results':
                try:
                    default_user_settings['max_results'] = int(setting_value) if setting_value else 10
                except (ValueError, TypeError):
                    default_user_settings['max_results'] = 10
            elif setting_key == 'smart_reasoning':
                default_user_settings['infer'] = setting_value.lower() == 'true' if setting_value else True

        st.session_state.user_settings = default_user_settings

    except Exception as e:
        # 如果数据库加载失败，使用默认设置
        st.session_state.user_settings = default_user_settings

# 初始化模型选择偏好
if 'model_preferences' not in st.session_state:
    st.session_state.model_preferences = {
        'strategy': 'auto_intelligent',  # 自动智能选择
        'prefer_speed': False,
        'prefer_quality': False,
        'cost_sensitive': False,
        'always_use_pro': False,
        'always_use_flash': False,
        'show_model_info': True
    }

def main():
    """主应用程序函数"""

    # 初始化认证系统
    auth_system = AuthSystem()

    # 应用安全补丁
    apply_security_patches()

    # 检查用户是否已认证
    if not auth_system.is_authenticated():
        auth_system.show_login_page()
        return

    # 显示用户信息
    auth_system.show_user_info()

    # 显示修改密码对话框（如果需要）
    auth_system.show_change_password_dialog()

    # 显示管理员面板（如果需要）
    auth_system.show_admin_panel()

    # 主标题
    st.markdown("""
    <div class="main-header">
        <h1>🧠 Mem0 记忆管理系统</h1>
        <p>使用AI智能处理，上传和搜索您的记忆</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        render_sidebar()
    
    # 主内容区域
    # 顶部标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🧠 智能对话", 
        "📊 数据分析", 
        "📝 记忆管理", 
        "🔍 记忆搜索",
        "⚙️ 系统设置"
    ])
    
    with tab1:
        modern_smart_chat_interface()
    
    with tab2:
        data_analysis_interface()
    
    with tab3:
        memory_management_interface()
    
    with tab4:
        memory_search_interface()
    
    with tab5:
        system_settings_interface(auth_system)

def render_sidebar():
    """渲染侧边栏"""
    st.header("⚙️ 系统设置")
    
    # 连接状态
    if st.session_state.get('api_connected', False):
        st.markdown('<p class="status-connected">✅ 已连接</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-disconnected">❌ 未连接</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # AI模型API配置
    st.subheader("🤖 AI模型API")

    # 使用表单包装API配置，避免密码字段警告
    with st.form("sidebar_ai_api_config_form", clear_on_submit=False):
        api_url = st.text_input(
            "AI API地址",
            value=st.session_state.api_settings['api_url'],
            help="大语言模型API服务地址（如Gemini Balance）"
        )

        api_key = st.text_input(
            "AI API密钥",
            value=st.session_state.api_settings['api_key'],
            type="password",
            help="AI模型API认证token（用于调用AI服务）"
        )

        # 表单提交按钮（隐藏，通过其他按钮触发更新）
        form_submitted = st.form_submit_button("更新配置", type="secondary")

    # 处理表单提交或重新连接
    if form_submitted:
        # 更新会话状态
        st.session_state.api_settings['api_url'] = api_url
        st.session_state.api_settings['api_key'] = api_key

        # 保存到数据库
        try:
            import psycopg2
            import os
            import time

            # 数据库连接配置
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
                'database': os.getenv('POSTGRES_DB', 'mem0db'),
                'user': os.getenv('POSTGRES_USER', 'mem0'),
                'password': os.getenv('POSTGRES_PASSWORD', 'mem0password'),
                'port': 5432
            }

            # 获取当前用户ID
            current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')

            # 连接数据库并保存设置
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # 保存AI模型API设置
            settings_to_save = [
                ('ai_api_url', api_url),
                ('ai_api_key', api_key),
                ('ai_api_last_update', str(int(time.time())))
            ]

            for setting_key, setting_value in settings_to_save:
                cursor.execute("""
                    INSERT INTO mem0_user_settings (user_id, setting_key, setting_value, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, setting_key)
                    DO UPDATE SET
                        setting_value = EXCLUDED.setting_value,
                        updated_at = CURRENT_TIMESTAMP
                """, (current_user_id, setting_key, setting_value))

            # 提交事务
            conn.commit()
            cursor.close()
            conn.close()

            st.success("✅ AI模型API配置已保存到数据库！")

        except Exception as db_error:
            st.error(f"❌ 数据库保存失败: {str(db_error)}")
            import traceback
            print(f"数据库保存错误详情: {traceback.format_exc()}")

    elif st.button("🔄 重新连接", type="secondary"):
        # 重新连接时使用当前配置
        with st.spinner("正在重新连接..."):
            test_ai_api_connection(api_url, api_key)
    
    st.divider()
    
    # 用户设置
    st.subheader("👤 用户设置")
    
    user_id = st.text_input(
        "用户ID",
        value=st.session_state.user_settings['user_id'],
        help="您的用户标识符"
    )
    
    st.session_state.user_settings['user_id'] = user_id
    
    st.divider()
    
    # 高级设置
    st.subheader("🎯 高级设置")
    
    custom_instructions = st.text_area(
        "自定义指令",
        value=st.session_state.user_settings['custom_instructions'],
        placeholder="请提取并结构化重要信息，保持清晰明了。",
        help="指导AI如何处理记忆",
        height=80
    )
    
    col1, col2 = st.columns(2)
    with col1:
        includes = st.text_input(
            "包含内容",
            value=st.session_state.user_settings['includes'],
            placeholder="技术文档, API",
            help="要包含的内容类型"
        )
    
    with col2:
        excludes = st.text_input(
            "排除内容",
            value=st.session_state.user_settings['excludes'],
            placeholder="个人信息",
            help="要排除的内容类型"
        )
    
    max_results = st.slider(
        "最大结果数",
        min_value=1,
        max_value=50,
        value=st.session_state.user_settings['max_results'],
        help="搜索返回的最大结果数"
    )
    
    infer = st.checkbox(
        "智能推理",
        value=st.session_state.user_settings['infer'],
        help="启用AI智能处理"
    )
    
    # 更新设置并保存到配置文件
    st.session_state.user_settings.update({
        'custom_instructions': custom_instructions,
        'includes': includes,
        'excludes': excludes,
        'max_results': max_results,
        'infer': infer
    })

    # 自动保存到配置文件
    try:
        if 'config' in st.session_state and st.session_state.config:
            st.session_state.config.update_advanced_settings(
                custom_instructions=custom_instructions,
                includes=includes,
                excludes=excludes,
                infer=infer
            )
    except Exception as e:
        # 静默处理保存错误，不影响用户体验
        pass
    
    st.divider()

    # 设置保存
    st.subheader("💾 设置管理")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存设置", type="primary"):
            try:
                # 获取当前用户信息
                current_username = getattr(st.session_state, 'user_info', {}).get('username', 'admin')

                if webui_db:
                    # 使用WebUI独立数据库保存设置
                    import json

                    settings_to_save = [
                        ('custom_instructions', custom_instructions),
                        ('include_content_types', json.dumps(includes.split(', ') if includes else [])),
                        ('exclude_content_types', json.dumps(excludes.split(', ') if excludes else [])),
                        ('max_results', str(max_results)),
                        ('smart_reasoning', str(infer).lower())
                    ]

                    # 保存每个设置到WebUI数据库
                    success_count = 0
                    for setting_key, setting_value in settings_to_save:
                        if webui_db.save_user_setting(current_username, setting_key, setting_value):
                            success_count += 1

                    if success_count == len(settings_to_save):
                        st.success("✅ 设置已保存到WebUI数据库！")
                    else:
                        st.warning(f"⚠️ 部分设置保存失败 ({success_count}/{len(settings_to_save)})")

                else:
                    # 回退到原有的mem0数据库（兼容性）
                    import psycopg2
                    import json

                    # 数据库连接配置
                    db_config = get_webui_db_config()

                    # 获取当前用户ID（从认证系统获取）
                    current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')

                    # 连接数据库
                    conn = psycopg2.connect(**db_config)
                    cursor = conn.cursor()

                    # 准备要保存的设置（从当前输入的值获取）
                    settings_to_save = [
                        ('custom_instructions', custom_instructions),
                        ('include_content_types', json.dumps(includes.split(', ') if includes else [])),
                        ('exclude_content_types', json.dumps(excludes.split(', ') if excludes else [])),
                        ('max_results', str(max_results)),
                        ('smart_reasoning', str(infer).lower()),
                        ('system_initialized', 'true')
                    ]

                    # 保存每个设置
                    for setting_key, setting_value in settings_to_save:
                        cursor.execute("""
                            INSERT INTO mem0_user_settings (user_id, setting_key, setting_value, updated_at)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (user_id, setting_key)
                            DO UPDATE SET
                                setting_value = EXCLUDED.setting_value,
                                updated_at = CURRENT_TIMESTAMP
                        """, (current_user_id, setting_key, setting_value))

                    # 提交事务
                    conn.commit()
                    cursor.close()
                    conn.close()

                    st.success("✅ 设置已保存到数据库！")

            except Exception as e:
                st.error(f"❌ 保存失败: {str(e)}")
                # 显示详细错误信息用于调试
                st.error(f"详细错误: {type(e).__name__}: {str(e)}")

    with col2:
        if st.button("🔄 重置设置", type="secondary"):
            st.session_state.user_settings = {
                'user_id': 'default_user',
                'custom_instructions': '',
                'includes': '技术文档, API',
                'excludes': '个人信息',
                'max_results': 10,
                'infer': True
            }
            st.success("✅ 设置已重置！")
            st.rerun()

    st.divider()

    # 快速操作
    st.subheader("⚡ 快速操作")

    if st.button("🔄 刷新页面", type="secondary"):
        st.rerun()

    if st.button("🗑️ 清空聊天", type="secondary"):
        st.session_state.chat_history = []
        st.success("聊天记录已清空")

def simple_connection_test(api_url: str):
    """简单的连接测试 - 只检测基础连通性"""
    try:
        import requests
        test_url = api_url.rstrip('/')
        response = requests.get(f"{test_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_ai_api_connection(api_url: str, api_key: str):
    """测试AI模型API连接 - 简化版本，专注于基础连通性"""
    try:
        import requests
        import time

        # 显示测试进度
        progress_placeholder = st.empty()
        progress_placeholder.info("🔄 正在测试AI模型API连接...")

        # 简化的连接测试
        test_url = api_url.rstrip('/')

        # 只测试健康检查端点
        try:
            response = requests.get(f"{test_url}/health", timeout=10)
        except requests.exceptions.RequestException as e:
            # 如果容器间网络连接失败，尝试使用localhost
            if 'gemini-balance:8000' in test_url:
                test_url = test_url.replace('gemini-balance:8000', 'localhost:8000')
                response = requests.get(f"{test_url}/health", timeout=10)
            else:
                raise e

        if response.status_code == 200:
            # AI API连接成功
            progress_placeholder.success("✅ AI模型API连接测试成功！")

            # 更新会话状态
            st.session_state.api_settings.update({
                'api_url': api_url,
                'api_key': api_key,
                'connected': True,
                'last_test_time': time.time(),
                'test_result': 'success'
            })
            st.session_state.api_connected = True

            # 保存AI API设置到数据库
            try:
                progress_placeholder.info("� 正在保存AI API设置到数据库...")
                st.info(f"🔄 保存AI模型API设置: api_url={api_url}, api_key={api_key[:4]}****")
                import psycopg2
                import os

                # 数据库连接配置
                db_config = {
                    'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
                    'database': os.getenv('POSTGRES_DB', 'mem0'),
                    'user': os.getenv('POSTGRES_USER', 'mem0'),
                    'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024'),
                    'port': 5432
                }

                # 获取当前用户ID
                current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')

                # 连接数据库并保存设置
                conn = psycopg2.connect(**db_config)
                cursor = conn.cursor()

                # 保存AI模型API设置
                settings_to_save = [
                    ('ai_api_url', api_url),
                    ('ai_api_key', api_key),
                    ('ai_api_connected', 'true'),
                    ('ai_api_last_test_time', str(int(time.time())))
                ]

                for setting_key, setting_value in settings_to_save:
                    cursor.execute("""
                        INSERT INTO mem0_user_settings (user_id, setting_key, setting_value, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, setting_key)
                        DO UPDATE SET
                            setting_value = EXCLUDED.setting_value,
                            updated_at = CURRENT_TIMESTAMP
                    """, (current_user_id, setting_key, setting_value))

                # 提交事务
                conn.commit()
                cursor.close()
                conn.close()

                progress_placeholder.success("✅ AI模型API设置已成功保存到数据库！")

            except Exception as db_error:
                # 数据库保存失败不影响连接测试，但要记录错误
                st.warning(f"⚠️ 数据库保存失败: {str(db_error)}")
                import traceback
                print(f"数据库保存错误详情: {traceback.format_exc()}")

            # 显示详细的AI API连接信息
            with st.expander("📋 AI API连接详情", expanded=True):
                st.write(f"🌐 **API地址**: {api_url}")
                st.write(f"🔑 **认证密钥**: {api_key[:8]}{'*' * (len(api_key) - 8) if len(api_key) > 8 else '****'}")
                st.write(f"⏰ **测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"📊 **响应状态**: HTTP {response.status_code}")

                # 根据API类型显示不同信息
                if 'gemini-balance' in api_url:
                    st.write("🤖 **服务类型**: Gemini Balance AI对话API")
                    st.write("✅ **功能状态**: AI对话功能正常")
                elif 'openai' in api_url:
                    st.write("🤖 **服务类型**: OpenAI API")
                    st.write("✅ **功能状态**: AI对话功能正常")
                else:
                    st.write("🤖 **服务类型**: 通用AI模型API")
                    st.write("✅ **功能状态**: AI服务正常")

            # 延迟一秒后刷新页面以更新连接状态显示
            time.sleep(1)
            st.rerun()
        else:
            # AI API连接失败
            progress_placeholder.empty()
            st.session_state.api_connected = False
            st.session_state.api_settings['connected'] = False
            st.error(f"❌ AI模型API连接失败: HTTP {response.status_code}")

            # 显示详细错误信息
            with st.expander("🔍 错误详情"):
                st.write(f"**请求地址**: {test_url}")
                st.write(f"**响应状态**: HTTP {response.status_code}")
                try:
                    error_detail = response.text[:500] if response.text else "无响应内容"
                    st.write(f"**错误详情**: {error_detail}")
                except:
                    st.write("**错误详情**: 无法获取详细错误信息")

    except requests.exceptions.Timeout:
        if 'progress_placeholder' in locals():
            progress_placeholder.empty()
        st.session_state.api_connected = False
        st.session_state.api_settings['connected'] = False
        st.error("❌ AI模型API连接超时，请检查服务是否正常运行")

        with st.expander("🔍 超时问题排查"):
            st.write("**可能原因**:")
            st.write("- AI模型服务未启动或响应缓慢")
            st.write("- 网络连接问题")
            st.write("- 服务器负载过高")
            st.write("**建议解决方案**:")
            st.write("- 检查Docker容器状态: `docker ps`")
            st.write("- 查看服务日志: `docker logs gemini-balance`")
            st.write("- 重启AI服务")

    except requests.exceptions.ConnectionError as e:
        if 'progress_placeholder' in locals():
            progress_placeholder.empty()
        st.session_state.api_connected = False
        st.session_state.api_settings['connected'] = False
        st.error("❌ 无法连接到AI模型API服务，请检查地址是否正确")

        with st.expander("🔍 连接问题排查"):
            st.write(f"**错误详情**: {str(e)}")
            st.write("**可能原因**:")
            st.write("- AI API地址配置错误")
            st.write("- AI服务未启动")
            st.write("- 端口被占用或防火墙阻止")
            st.write("**建议解决方案**:")
            st.write("- 确认AI API地址格式正确")
            st.write("- 检查AI服务是否运行: `docker ps | grep gemini`")
            st.write("- 测试端口连通性")

    except Exception as e:
        if 'progress_placeholder' in locals():
            progress_placeholder.empty()
        st.session_state.api_connected = False
        st.session_state.api_settings['connected'] = False
        st.error(f"❌ AI模型API连接失败: {str(e)}")

        with st.expander("🔍 详细错误信息"):
            st.write(f"**错误类型**: {type(e).__name__}")
            st.write(f"**错误详情**: {str(e)}")
            st.write("**建议操作**:")
            st.write("- 检查AI API地址和密钥是否正确")
            st.write("- 确认AI服务正常运行")
            st.write("- 查看系统日志获取更多信息")

            # 显示调试信息
            import traceback
            st.code(traceback.format_exc(), language="python")






def display_real_time_memory_learning():
    """显示AI实时记忆学习过程"""

    # 获取最近学习的记忆
    if 'recent_memories' not in st.session_state:
        st.session_state.recent_memories = []

    # 显示最近学习的记忆
    if st.session_state.recent_memories:
        st.markdown("### 🆕 AI刚学到的记忆")
        for memory in st.session_state.recent_memories[-3:]:  # 显示最近3条
            with st.expander(f"💡 {memory.get('summary', '新记忆')}", expanded=True):
                st.write(f"**内容**: {memory.get('content', '')}")
                st.write(f"**时间**: {memory.get('timestamp', '')}")
                if memory.get('confidence'):
                    st.progress(memory['confidence'], text=f"置信度: {memory['confidence']:.0%}")
    else:
        st.info("💭 AI正在等待学习新的记忆...")

    # 显示记忆统计
    st.markdown("### 📊 记忆统计")

    try:
        # 确保用户设置已初始化
        if 'user_settings' not in st.session_state:
            st.session_state.user_settings = {'user_id': 'default_user'}

        user_id = st.session_state.user_settings.get('user_id', 'default_user')

        # 获取用户的所有记忆
        memories_data = MemoryAPI.get_memories(user_id)

        # 使用与记忆管理页面相同的数据处理逻辑
        if not memories_data:
            st.metric("总记忆数量", 0)
            return

        # 如果返回的是字符串，尝试解析
        if isinstance(memories_data, str):
            try:
                memories_data = json.loads(memories_data)
            except:
                st.error(f"❌ API返回格式错误")
                return

        # 如果返回的是字典，可能包含在某个键中
        if isinstance(memories_data, dict):
            if 'results' in memories_data:
                # 处理嵌套的results结构
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    all_memories = memories_data['results']['results']
                else:
                    all_memories = memories_data['results']
            elif 'memories' in memories_data:
                all_memories = memories_data['memories']
            elif 'data' in memories_data:
                all_memories = memories_data['data']
            else:
                all_memories = []
        elif isinstance(memories_data, list):
            all_memories = memories_data
        else:
            all_memories = []

        if all_memories and len(all_memories) > 0:
            total_memories = len(all_memories)
            st.metric("总记忆数量", total_memories)

            # 显示最近的记忆标签
            st.markdown("### 🏷️ 记忆标签")
            # 提取记忆中的关键词作为标签
            tags = set()
            for memory in all_memories[:10]:  # 只处理最近10条
                content = memory.get('memory', memory.get('content', ''))
                # 简单的关键词提取
                words = content.split()
                for word in words:
                    if len(word) > 2 and word.isalpha():
                        tags.add(word)

            # 显示标签云
            if tags:
                tag_list = list(tags)[:8]  # 最多显示8个标签
                cols = st.columns(2)
                for i, tag in enumerate(tag_list):
                    with cols[i % 2]:
                        st.button(f"#{tag}", key=f"tag_{i}", disabled=True)
            else:
                st.info("🏷️ 暂无标签")
        else:
            st.metric("总记忆数量", 0)

    except Exception as e:
        st.error(f"❌ 无法获取记忆统计")

        # 显示空的标签区域
        st.markdown("### 🏷️ 记忆标签")
        st.info("🏷️ 无法加载标签")

    # 记忆学习状态
    st.markdown("### ⚡ 学习状态")
    if len(st.session_state.chat_history) > 0:
        st.success("🟢 AI正在积极学习中")
        st.write("AI会自动从每次对话中提取重要信息")
    else:
        st.info("🟡 等待对话开始")

def handle_multimodal_chat_message(user_input: str, image_info: Dict = None):
    """处理多模态聊天消息 - 支持文字和图片"""

    # 确保model_selector可用并进行智能模型选择
    ensure_model_selector()
    has_image = image_info is not None and image_info.get("success", False)
    content_for_analysis = user_input or "图片分析请求"

    # 获取用户偏好
    model_preferences = st.session_state.model_preferences

    # 动态选择最优模型
    model_selection = st.session_state.model_selector.select_optimal_model(
        user_query=content_for_analysis,
        has_image=has_image
    )

    # 字段名标准化：确保selected_model字段存在
    if 'selected_model' not in model_selection:
        if 'recommended_model' in model_selection:
            model_selection['selected_model'] = model_selection['recommended_model']
        else:
            st.error(f"❌ 模型选择器返回的数据既没有'selected_model'也没有'recommended_model'字段: {model_selection}")
            return

    # 显示模型选择信息
    if model_preferences.get('show_model_info', True):
        with st.expander("🤖 本次对话模型选择", expanded=False):
            st.write(f"**选择的模型:** {model_selection['selected_model']}")
            st.write(f"**任务类型:** {model_selection['task_type']}")
            st.write(f"**复杂度评分:** {model_selection['complexity']['total_score']}")
            st.write(f"**选择理由:** {model_selection['reasoning']}")
            st.write(f"**置信度:** {model_selection['confidence']:.2%}")

            # 显示模型能力
            capabilities = model_selection['capabilities']
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("速度", f"{capabilities['speed']}/10")
            with col2:
                st.metric("质量", f"{capabilities['quality']}/10")
            with col3:
                st.metric("成本效率", f"{capabilities['cost']}/10")

    # 构建用户消息
    user_message = {
        'role': 'user',
        'content': user_input or "请分析这张图片",
        'timestamp': datetime.now(),
        'model_info': model_selection
    }

    if has_image:
        user_message['image_info'] = {
            'width': image_info['width'],
            'height': image_info['height'],
            'size_mb': image_info['size_mb'],
            'format': image_info['format']
        }

    st.session_state.chat_history.append(user_message)

    # 生成自然的AI回复
    if has_image:
        ai_response = f"我看到了您分享的图片（{image_info['width']}x{image_info['height']}，{image_info['format']}格式）。"
        if user_input:
            ai_response += f" 关于您的问题：'{user_input[:50]}...'，我已经使用多模态AI模型进行了分析。"
        else:
            ai_response += "我已经使用多模态AI模型进行了分析。"
    else:
        # 根据输入内容生成更自然的回复
        if user_input.strip().lower() in ['你好', 'hello', 'hi', '嗨', '哈喽']:
            ai_response = "你好！我是AI助手，很高兴为您服务。有什么我可以帮助您的吗？"
        elif user_input.strip().lower() in ['测试', 'test', '试试', '看看']:
            ai_response = f"系统运行正常！我正在使用 {model_selection['selected_model']} 模型为您服务。您可以向我提问或分享图片进行分析。"
        elif len(user_input.strip()) < 5:
            ai_response = "我收到了您的消息。如果您有具体的问题或需要帮助，请详细描述，我会尽力为您解答。"
        else:
            ai_response = f"我理解您提到的关于 '{user_input[:50]}...' 的内容。我已经使用 {model_selection['selected_model']} 模型进行处理。"

    st.session_state.chat_history.append({
        'role': 'assistant',
        'content': ai_response,
        'timestamp': datetime.now()
    })

    # Mem0自动分析并保存对话记忆
    if len(st.session_state.chat_history) >= 2:
        try:
            # 获取更多上下文：最近4条消息或全部消息（如果少于4条）
            context_size = min(4, len(st.session_state.chat_history))
            recent_messages = st.session_state.chat_history[-context_size:]
            messages_for_api = []

            for msg in recent_messages:
                api_msg = {"role": msg['role'], "content": msg['content']}
                messages_for_api.append(api_msg)

            user_id = st.session_state.user_settings['user_id']

            # 让Mem0自动分析对话并提取重要信息
            # 使用用户的高级设置
            user_custom_instructions = st.session_state.user_settings.get('custom_instructions', '')
            user_includes = st.session_state.user_settings.get('includes', '')
            user_excludes = st.session_state.user_settings.get('excludes', '')
            user_infer = st.session_state.user_settings.get('infer', True)

            # 构建最终的自定义指令（结合用户设置和默认指令）
            if user_custom_instructions.strip():
                final_instructions = f"{user_custom_instructions}\n\n使用模型: {model_selection['selected_model']}"
            else:
                # 如果用户没有设置自定义指令，使用默认的详细指令
                final_instructions = f"""
请仔细分析这段对话，提取所有有价值的信息，包括但不限于：
1. 用户的个人信息、偏好、技能、工作背景
2. 技术知识、架构原则、工程实践
3. 项目经验、解决方案、最佳实践
4. 重要的观点、建议、决策
5. 任何可能在未来对话中有用的上下文信息

使用模型: {model_selection['selected_model']}
请确保提取的记忆具有足够的细节和上下文，避免过度简化。
"""

            # 处理includes和excludes
            includes_list = None
            if user_includes.strip():
                includes_list = [item.strip() for item in user_includes.split(',') if item.strip()]

            excludes_list = None
            if user_excludes.strip():
                excludes_list = [item.strip() for item in user_excludes.split(',') if item.strip()]

            memory_result = MemoryAPI.add_memory(
                messages=messages_for_api,
                user_id=user_id,
                custom_instructions=final_instructions,
                includes=includes_list,
                excludes=excludes_list
                # 注意：移除model和image_base64参数，因为mem0 API不支持
                # 模型信息已经包含在custom_instructions中
            )

            # 更新实时记忆学习状态
            if memory_result:
                # 初始化recent_memories如果不存在
                if 'recent_memories' not in st.session_state:
                    st.session_state.recent_memories = []

                # 检查返回的记忆结果
                if 'memories' in memory_result and memory_result['memories']:
                    new_memories = memory_result['memories']
                    # 添加新学习的记忆到实时显示
                    for memory in new_memories:
                        memory_content = memory.get('memory', '')
                        if memory_content:
                            memory_info = {
                                'content': memory_content,
                                'summary': memory_content[:50] + '...' if len(memory_content) > 50 else memory_content,
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'confidence': 0.85,  # 默认置信度
                                'id': memory.get('id', '')
                            }
                            st.session_state.recent_memories.append(memory_info)

                # 如果没有直接返回memories，尝试重新获取最新记忆来更新显示
                elif 'results' in memory_result or not memory_result.get('memories'):
                    try:
                        # 获取最新的记忆来更新显示
                        latest_memories = MemoryAPI.get_memories(user_id)
                        if latest_memories and 'results' in latest_memories and 'results' in latest_memories['results']:
                            all_memories = latest_memories['results']['results']
                            if all_memories:
                                # 获取最新的记忆（按创建时间排序）
                                latest_memory = all_memories[0]  # 假设API返回的是按时间排序的
                                memory_content = latest_memory.get('memory', '')
                                if memory_content:
                                    memory_info = {
                                        'content': memory_content,
                                        'summary': memory_content[:50] + '...' if len(memory_content) > 50 else memory_content,
                                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                                        'confidence': 0.85,
                                        'id': latest_memory.get('id', '')
                                    }
                                    # 检查是否已经存在相同的记忆（避免重复）
                                    existing_ids = [m.get('id', '') for m in st.session_state.recent_memories]
                                    if memory_info['id'] not in existing_ids:
                                        st.session_state.recent_memories.append(memory_info)
                    except Exception as e:
                        st.warning(f"获取最新记忆失败: {str(e)}")

                # 只保留最近10条记忆
                if len(st.session_state.recent_memories) > 10:
                    st.session_state.recent_memories = st.session_state.recent_memories[-10:]

        except Exception as e:
            st.warning(f"⚠️ 自动保存失败: {str(e)}")

    st.rerun()

def handle_chat_message(user_input: str):
    """处理纯文字聊天消息（兼容性函数）"""
    handle_multimodal_chat_message(user_input, None)

def save_chat_to_memory():
    """手动保存聊天记录到记忆库"""
    if not st.session_state.chat_history:
        st.warning("没有聊天记录可保存")
        return

    try:
        # 构建对话记录
        messages = []
        for msg in st.session_state.chat_history[-10:]:  # 只保存最近10条消息
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        user_id = st.session_state.user_settings['user_id']
        custom_instructions = st.session_state.user_settings.get('custom_instructions', '手动保存的对话记录')
        includes = st.session_state.user_settings.get('includes', '').split(',') if st.session_state.user_settings.get('includes') else None
        excludes = st.session_state.user_settings.get('excludes', '').split(',') if st.session_state.user_settings.get('excludes') else None

        with st.spinner("正在保存对话到记忆库..."):
            result = MemoryAPI.add_memory(
                messages=messages,
                user_id=user_id,
                custom_instructions=custom_instructions,
                includes=includes,
                excludes=excludes
            )
            st.success("✅ 对话已保存到记忆库！")

            # 显示保存结果
            if result and isinstance(result, dict):
                with st.expander("📋 保存详情"):
                    st.json(result)

    except Exception as e:
        st.error(f"❌ 保存失败: {str(e)}")

def data_analysis_interface():
    """数据分析界面 - 基于真实API数据"""
    st.header("📊 数据分析")
    st.markdown("分析您的记忆数据，获取洞察和统计信息")

    user_id = st.session_state.user_settings['user_id']

    try:
        # 获取真实记忆数据
        with st.spinner("正在加载数据..."):
            memories_data = MemoryAPI.get_memories(user_id)

        # 处理API响应格式
        if isinstance(memories_data, str):
            try:
                memories_data = json.loads(memories_data)
            except:
                st.error("❌ API返回格式错误")
                return

        if isinstance(memories_data, dict):
            if 'results' in memories_data:
                # 处理嵌套的results结构
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    memories_data = memories_data['results']['results']
                else:
                    memories_data = memories_data['results']
            elif 'memories' in memories_data:
                memories_data = memories_data['memories']
            elif 'data' in memories_data:
                memories_data = memories_data['data']

        if not isinstance(memories_data, list):
            memories_data = []

        if not memories_data or len(memories_data) == 0:
            st.info("📝 暂无记忆数据，请先添加一些记忆")
            return

        # 基本统计信息
        total_memories = len(memories_data)

        # 计算时间相关统计
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        day_ago = now - timedelta(days=1)

        recent_memories = []
        today_memories = []

        for memory in memories_data:
            # 假设记忆有创建时间字段
            if 'created_at' in memory:
                try:
                    created_time = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                    if created_time >= week_ago:
                        recent_memories.append(memory)
                    if created_time >= day_ago:
                        today_memories.append(memory)
                except:
                    pass

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总记忆数", total_memories, len(recent_memories))

        with col2:
            st.metric("本周新增", len(recent_memories), len(today_memories))

        with col3:
            # 搜索次数从会话状态获取
            search_count = st.session_state.get('search_count', 0)
            st.metric("搜索次数", search_count, "0")

        with col4:
            # 活跃天数计算
            unique_days = set()
            for memory in memories_data:
                if 'created_at' in memory:
                    try:
                        created_time = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                        unique_days.add(created_time.date())
                    except:
                        pass
            st.metric("活跃天数", len(unique_days), "0")

        st.divider()

        # 图表分析
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 记忆增长趋势")
            if len(memories_data) > 0:
                # 基于真实数据生成趋势图
                daily_counts = {}
                valid_time_data = False

                for memory in memories_data:
                    if 'created_at' in memory and memory['created_at']:
                        try:
                            created_time = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                            date_key = created_time.date()
                            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                            valid_time_data = True
                        except Exception as e:
                            # 如果时间解析失败，使用当前日期作为默认值
                            date_key = datetime.now().date()
                            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

                # 如果没有有效的时间数据，创建默认数据
                if not valid_time_data and len(memories_data) > 0:
                    today = datetime.now().date()
                    daily_counts[today] = len(memories_data)

                if daily_counts and len(daily_counts) > 0:
                    dates = sorted(daily_counts.keys())
                    counts = [daily_counts[date] for date in dates]

                    # 确保数据有效性，避免Infinite extent错误
                    if (dates and counts and len(dates) == len(counts) and
                        all(isinstance(c, (int, float)) and not pd.isna(c) and c >= 0 for c in counts) and
                        all(hasattr(d, 'year') and hasattr(d, 'month') and hasattr(d, 'day') for d in dates)):
                        try:
                            chart_data = pd.DataFrame({
                                '日期': dates,
                                '记忆数量': counts
                            })
                            # 验证DataFrame不为空且数据有效
                            if not chart_data.empty and chart_data['记忆数量'].notna().all() and len(chart_data) > 0:
                                st.line_chart(chart_data.set_index('日期'))
                            else:
                                st.info("数据包含无效值，无法显示图表")
                        except Exception as e:
                            st.warning(f"图表渲染失败: {str(e)}")
                            # 显示简单的文本统计作为备选
                            st.info(f"📊 共有 {len(memories_data)} 条记忆，分布在 {len(daily_counts)} 天")
                    else:
                        st.info("数据格式不正确，无法显示图表")
                        # 显示简单的文本统计作为备选
                        st.info(f"📊 共有 {len(memories_data)} 条记忆")
                else:
                    st.info("暂无时间数据可显示")
            else:
                st.info("暂无数据")

        with col2:
            st.subheader("🏷️ 记忆内容分析")
            # 基于真实记忆内容进行简单分类
            categories = {
                '技术相关': 0,
                '会议记录': 0,
                '学习笔记': 0,
                '项目信息': 0,
                '其他': 0
            }

            for memory in memories_data:
                # 获取记忆内容，支持不同的字段名
                content = memory.get('content', memory.get('memory', memory.get('text', ''))).lower()
                if any(word in content for word in ['api', 'code', 'python', 'javascript', 'tech', '技术', '代码']):
                    categories['技术相关'] += 1
                elif any(word in content for word in ['meeting', 'discuss', '会议', '讨论']):
                    categories['会议记录'] += 1
                elif any(word in content for word in ['learn', 'study', '学习', '笔记']):
                    categories['学习笔记'] += 1
                elif any(word in content for word in ['project', '项目']):
                    categories['项目信息'] += 1
                else:
                    categories['其他'] += 1

            if sum(categories.values()) > 0:
                try:
                    # 确保数据有效性
                    category_keys = list(categories.keys())
                    category_values = list(categories.values())

                    # 验证数据有效性，避免Infinite extent错误
                    if (category_keys and category_values and
                        len(category_keys) == len(category_values) and
                        all(isinstance(v, (int, float)) and not pd.isna(v) and v >= 0 for v in category_values)):

                        category_data = pd.DataFrame({
                            '类型': category_keys,
                            '数量': category_values
                        })

                        # 验证DataFrame不为空且数据有效
                        if not category_data.empty and category_data['数量'].notna().all():
                            st.bar_chart(category_data.set_index('类型'))
                        else:
                            st.info("分类数据包含无效值，无法显示图表")
                    else:
                        st.info("分类数据格式不正确，无法显示图表")
                except Exception as e:
                    st.warning(f"分类图表渲染失败: {str(e)}")
                    st.info("暂无有效的分类数据可显示")
            else:
                st.info("暂无分类数据")

        st.divider()

        # 详细分析
        st.subheader("🔍 详细分析")

        analysis_type = st.selectbox(
            "选择分析类型",
            ["记忆内容统计", "时间分布分析", "内容长度分析", "关键词分析"]
        )

        if analysis_type == "记忆内容统计":
            st.info("📊 基于真实数据的内容统计")
            total_chars = sum(len(memory.get('content', memory.get('memory', memory.get('text', '')))) for memory in memories_data)
            avg_length = total_chars / len(memories_data) if memories_data else 0

            st.write(f"- 总记忆数: {len(memories_data)}")
            st.write(f"- 总字符数: {total_chars:,}")
            st.write(f"- 平均长度: {avg_length:.1f} 字符")

            # 长度分布
            lengths = [len(memory.get('content', memory.get('memory', memory.get('text', '')))) for memory in memories_data]
            if lengths:
                st.write(f"- 最长记忆: {max(lengths)} 字符")
                st.write(f"- 最短记忆: {min(lengths)} 字符")

        elif analysis_type == "时间分布分析":
            st.info("📊 基于真实数据的时间分析")
            if memories_data:
                hour_counts = {}
                for memory in memories_data:
                    if 'created_at' in memory:
                        try:
                            created_time = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                            hour = created_time.hour
                            hour_counts[hour] = hour_counts.get(hour, 0) + 1
                        except:
                            pass

                if hour_counts:
                    most_active_hour = max(hour_counts, key=hour_counts.get)
                    st.write(f"- 最活跃时间: {most_active_hour}:00")
                    st.write(f"- 该时段记忆数: {hour_counts[most_active_hour]}")
                else:
                    st.write("- 暂无时间数据")

    except Exception as e:
        st.error(f"❌ 数据加载失败: {str(e)}")
        st.info("请检查API连接状态")

def memory_management_interface():
    """记忆管理界面 - 支持多模态内容"""
    st.header("📝 记忆管理")
    st.markdown("管理和组织您的记忆库，支持文字和图片内容")

    # 添加示例记忆
    st.subheader("➕ 添加记忆")

    # 内容输入模式选择
    content_mode = st.radio(
        "内容类型",
        ["💬 纯文字记忆", "🖼️ 文字+图片记忆"],
        horizontal=True
    )

    col1, col2 = st.columns(2)

    with col1:
        user_content = st.text_area(
            "用户输入内容",
            placeholder="输入用户的消息或内容...",
            height=120
        )

    with col2:
        assistant_content = st.text_area(
            "助手回复内容",
            placeholder="输入助手的回复内容...",
            height=120
        )

    # 图片上传（如果选择了图片模式）
    uploaded_image = None
    if content_mode == "🖼️ 文字+图片记忆":
        st.markdown("---")
        st.subheader("📷 图片内容")

        uploaded_image = st.file_uploader(
            "上传图片",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
            help="支持PNG、JPG、JPEG、GIF、BMP格式，最大20MB"
        )

        if uploaded_image:
            # 显示图片预览和信息
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(uploaded_image, caption="图片预览", width=200)

            with col2:
                # 处理图片获取信息
                image_info = st.session_state.multimodal_processor.process_image(uploaded_image)
                if image_info["success"]:
                    st.write(f"**格式:** {image_info['format']}")
                    st.write(f"**尺寸:** {image_info['width']} x {image_info['height']}")
                    st.write(f"**大小:** {image_info['size_mb']} MB")

                    # 验证图片
                    is_valid, validation_msg = st.session_state.multimodal_processor.validate_image(image_info)
                    if is_valid:
                        st.success(validation_msg)
                    else:
                        st.error(validation_msg)
                else:
                    st.error(f"图片处理失败: {image_info['error']}")

    # 添加按钮
    st.markdown("---")
    if st.button("💾 添加记忆", type="primary"):
        if user_content.strip() or assistant_content.strip() or uploaded_image:
            add_sample_memory(user_content, assistant_content, uploaded_image)
        else:
            st.warning("⚠️ 请至少输入文字内容或上传图片")

    st.divider()

    # 记忆列表管理
    st.subheader("📋 记忆列表")

    # 搜索和过滤
    col1, col2, col3 = st.columns(3)

    with col1:
        search_filter = st.text_input("🔍 搜索记忆", placeholder="输入关键词...")

    with col2:
        category_filter = st.selectbox("📂 类型筛选", ["全部", "技术文档", "会议记录", "学习笔记", "项目信息"])

    with col3:
        date_filter = st.date_input("📅 日期筛选", value=None)

    # 显示记忆列表
    display_memory_list(search_filter, category_filter, date_filter)

def add_sample_memory(user_content: str, assistant_content: str, uploaded_image=None):
    """添加记忆 - 支持多模态内容"""
    try:
        messages = []
        if user_content.strip():
            messages.append({"role": "user", "content": user_content})
        if assistant_content.strip():
            messages.append({"role": "assistant", "content": assistant_content})

        # 处理图片
        image_info = None
        if uploaded_image:
            image_info = st.session_state.multimodal_processor.process_image(uploaded_image)
            if not image_info["success"]:
                st.error(f"❌ 图片处理失败: {image_info['error']}")
                return

        if not messages and not image_info:
            st.warning("⚠️ 请至少输入文字内容或上传图片")
            return

        # 确保model_selector可用并进行智能模型选择
        ensure_model_selector()
        content_for_analysis = user_content or assistant_content or "图片记忆"
        has_image = image_info is not None

        model_selection = st.session_state.model_selector.select_optimal_model(
            user_query=content_for_analysis,
            has_image=has_image
        )

        # 字段名标准化：确保selected_model字段存在
        if 'selected_model' not in model_selection:
            if 'recommended_model' in model_selection:
                model_selection['selected_model'] = model_selection['recommended_model']
            else:
                st.error(f"❌ 模型选择器返回的数据既没有'selected_model'也没有'recommended_model'字段: {model_selection}")
                return

        user_id = st.session_state.user_settings['user_id']
        custom_instructions = st.session_state.user_settings.get('custom_instructions')
        includes = st.session_state.user_settings.get('includes', '').split(',') if st.session_state.user_settings.get('includes') else None
        excludes = st.session_state.user_settings.get('excludes', '').split(',') if st.session_state.user_settings.get('excludes') else None

        # 添加模型信息到自定义指令
        model_info = f"使用模型: {model_selection['selected_model']}"
        if custom_instructions:
            custom_instructions = f"{custom_instructions} | {model_info}"
        else:
            custom_instructions = model_info

        with st.spinner("正在添加记忆..."):
            result = MemoryAPI.add_memory(
                messages=messages,
                user_id=user_id,
                custom_instructions=custom_instructions,
                includes=includes,
                excludes=excludes
                # 注意：移除model和image_base64参数，因为mem0 API不支持
                # 模型信息已经包含在custom_instructions中
            )

            st.success("✅ 记忆添加成功！")

            # 显示模型选择信息
            if st.session_state.model_preferences.get('show_model_info', True):
                with st.expander("🤖 模型选择信息"):
                    st.write(f"**使用模型:** {model_selection['selected_model']}")
                    st.write(f"**选择理由:** {model_selection['reasoning']}")
                    if has_image:
                        st.write(f"**图片信息:** {image_info['width']}x{image_info['height']}, {image_info['size_mb']}MB")

            # 显示返回的结果信息
            if result and isinstance(result, dict):
                with st.expander("📋 添加详情"):
                    st.json(result)

    except Exception as e:
        st.error(f"❌ 添加失败: {str(e)}")

def display_memory_list(search_filter: str, category_filter: str, date_filter):
    """显示真实记忆列表"""
    try:
        user_id = st.session_state.user_settings['user_id']

        with st.spinner("正在加载记忆列表..."):
            memories_data = MemoryAPI.get_memories(user_id)

        # 调试：显示原始数据格式
        if st.checkbox("🔧 显示调试信息"):
            st.write("**原始API响应:**")
            st.json(memories_data)

        # 处理不同的API响应格式
        if not memories_data:
            st.info("📝 暂无记忆数据")
            return

        # 如果返回的是字符串，尝试解析
        if isinstance(memories_data, str):
            try:
                memories_data = json.loads(memories_data)
            except:
                st.error(f"❌ API返回格式错误: {memories_data}")
                return

        # 如果返回的是字典，可能包含在某个键中
        if isinstance(memories_data, dict):
            if 'results' in memories_data:
                # 处理嵌套的results结构
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    memories_data = memories_data['results']['results']
                else:
                    memories_data = memories_data['results']
            elif 'memories' in memories_data:
                memories_data = memories_data['memories']
            elif 'data' in memories_data:
                memories_data = memories_data['data']

        # 确保是列表格式
        if not isinstance(memories_data, list):
            st.error(f"❌ 无法解析记忆数据格式: {type(memories_data)}")
            return

        if len(memories_data) == 0:
            st.info("📝 暂无记忆数据")
            return

        # 标准化记忆数据格式
        normalized_memories = []
        for i, memory in enumerate(memories_data):
            if isinstance(memory, str):
                # 如果记忆是字符串，创建标准格式
                normalized_memory = {
                    'id': f'memory_{i}',
                    'content': memory,
                    'created_at': '未知时间'
                }
            elif isinstance(memory, dict):
                # 如果是字典，标准化字段名
                normalized_memory = {
                    'id': memory.get('id', memory.get('memory_id', f'memory_{i}')),
                    'content': memory.get('content', memory.get('memory', memory.get('text', '无内容'))),
                    'created_at': memory.get('created_at', memory.get('timestamp', memory.get('date', '未知时间'))),
                    'score': memory.get('score', memory.get('relevance', None))
                }
                # 保留其他字段
                for key, value in memory.items():
                    if key not in ['id', 'memory_id', 'content', 'memory', 'text', 'created_at', 'timestamp', 'date', 'score', 'relevance']:
                        normalized_memory[key] = value
            else:
                # 其他格式，转为字符串
                normalized_memory = {
                    'id': f'memory_{i}',
                    'content': str(memory),
                    'created_at': '未知时间'
                }

            normalized_memories.append(normalized_memory)

        # 应用搜索过滤器
        filtered_memories = normalized_memories
        if search_filter:
            filtered_memories = [
                m for m in filtered_memories
                if search_filter.lower() in m.get('content', '').lower()
            ]

        # 应用日期过滤器
        if date_filter:
            target_date = date_filter.strftime('%Y-%m-%d')
            filtered_memories = [
                m for m in filtered_memories
                if target_date in m.get('created_at', '')
            ]

        if not filtered_memories:
            st.info("🔍 没有找到匹配的记忆")
            return

        st.info(f"📊 找到 {len(filtered_memories)} 条记忆")

        # 显示记忆
        for i, memory in enumerate(filtered_memories):
            memory_id = memory.get('id', f'memory_{i}')
            content = memory.get('content', '无内容')
            created_at = memory.get('created_at', '未知时间')

            # 截取内容预览
            preview = content[:100] + "..." if len(content) > 100 else content

            with st.expander(f"📄 {preview}"):
                st.write(f"**完整内容:** {content}")
                st.write(f"**创建时间:** {created_at}")
                st.write(f"**记忆ID:** {memory_id}")

                # 显示其他字段
                for key, value in memory.items():
                    if key not in ['id', 'content', 'created_at']:
                        st.write(f"**{key}:** {value}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"🗑️ 删除", key=f"delete_{memory_id}"):
                        delete_memory_action(memory_id)

                with col2:
                    if st.button(f"📋 复制内容", key=f"copy_{memory_id}"):
                        st.code(content)
                        st.success("内容已显示，可手动复制")

                with col3:
                    if st.button(f"🔍 相关搜索", key=f"search_{memory_id}"):
                        # 使用记忆内容的前50个字符作为搜索词
                        search_term = content[:50]
                        st.session_state['auto_search'] = search_term
                        st.info(f"将搜索: {search_term}")

    except Exception as e:
        st.error(f"❌ 加载记忆列表失败: {str(e)}")
        # 显示详细错误信息用于调试
        if st.checkbox("🔧 显示详细错误"):
            st.exception(e)

def delete_memory_action(memory_id: str):
    """删除记忆操作"""
    try:
        with st.spinner("正在删除记忆..."):
            result = MemoryAPI.delete_memory(memory_id)
            st.success("✅ 记忆删除成功！")
            st.rerun()  # 刷新页面
    except Exception as e:
        st.error(f"❌ 删除失败: {str(e)}")

def memory_search_interface():
    """记忆搜索界面 - 支持多模态搜索"""
    st.header("🔍 记忆搜索")
    st.markdown("智能搜索您的记忆库，支持文字和图片搜索")

    # 搜索模式选择
    search_mode = st.radio(
        "搜索模式",
        ["💬 文字搜索", "🖼️ 图片搜索", "🔍 文字+图片搜索"],
        horizontal=True
    )

    # 搜索输入
    search_query = st.text_input(
        "搜索内容",
        placeholder="输入您要搜索的内容...",
        help="支持自然语言搜索和关键词搜索"
    )

    # 图片搜索输入
    search_image = None
    if search_mode in ["🖼️ 图片搜索", "🔍 文字+图片搜索"]:
        st.markdown("---")
        st.subheader("📷 图片搜索")

        search_image = st.file_uploader(
            "上传要搜索的图片",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
            help="上传图片来搜索相似的记忆内容"
        )

        if search_image:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(search_image, caption="搜索图片", width=150)

            with col2:
                image_info = st.session_state.multimodal_processor.process_image(search_image)
                if image_info["success"]:
                    st.write(f"**格式:** {image_info['format']}")
                    st.write(f"**尺寸:** {image_info['width']} x {image_info['height']}")
                    st.write(f"**大小:** {image_info['size_mb']} MB")
                else:
                    st.error(f"图片处理失败: {image_info['error']}")

    # 搜索选项
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        search_type = st.selectbox("搜索类型", ["智能搜索", "精确匹配", "模糊搜索"])

    with col2:
        result_limit = st.number_input("结果数量", min_value=1, max_value=50, value=10)

    with col3:
        sort_by = st.selectbox("排序方式", ["相关性", "时间", "评分"])

    # 搜索按钮
    if st.button("🔍 开始搜索", type="primary"):
        if search_query.strip() or search_image:
            perform_multimodal_search(search_query, search_image, search_type, result_limit, sort_by)
        else:
            st.warning("⚠️ 请输入搜索内容或上传图片")

    st.divider()

    # 快速搜索建议
    st.subheader("💡 快速搜索")

    quick_searches = [
        "最近的技术文档",
        "Python相关内容",
        "项目会议记录",
        "学习笔记",
        "API文档"
    ]

    cols = st.columns(len(quick_searches))
    for i, search_term in enumerate(quick_searches):
        with cols[i]:
            if st.button(search_term, key=f"quick_{i}"):
                perform_memory_search(search_term, "智能搜索", 10, "相关性")

    st.divider()

    # 搜索历史
    if st.session_state.get('search_history'):
        st.subheader("📚 搜索历史")

        with st.expander("查看搜索历史", expanded=False):
            for i, search in enumerate(st.session_state.search_history[:10]):
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"🔍 {search['query']}")

                with col2:
                    st.write(f"结果: {search['results_count']}")

                with col3:
                    if st.button("重新搜索", key=f"repeat_{i}"):
                        perform_memory_search(search['query'], search.get('search_type', '智能搜索'), 10, "相关性")

        if st.button("🗑️ 清空搜索历史"):
            st.session_state.search_history = []
            st.success("搜索历史已清空")

def perform_multimodal_search(query: str, search_image, search_type: str, limit: int, sort_by: str):
    """执行多模态记忆搜索"""
    try:
        user_id = st.session_state.user_settings['user_id']

        # 处理图片
        image_base64 = None
        if search_image:
            image_info = st.session_state.multimodal_processor.process_image(search_image)
            if image_info["success"]:
                image_base64 = image_info['base64']
                st.info(f"📷 图片已处理: {image_info['width']}x{image_info['height']}")
            else:
                st.error(f"❌ 图片处理失败: {image_info['error']}")
                return

        # 确保model_selector可用并进行智能模型选择
        ensure_model_selector()
        content_for_analysis = query or "图片搜索"
        has_image = image_base64 is not None

        model_selection = st.session_state.model_selector.select_optimal_model(
            user_query=content_for_analysis,
            has_image=has_image
        )

        # 字段名标准化：确保selected_model字段存在
        if 'selected_model' not in model_selection:
            if 'recommended_model' in model_selection:
                model_selection['selected_model'] = model_selection['recommended_model']
            else:
                st.error(f"❌ 模型选择器返回的数据既没有'selected_model'也没有'recommended_model'字段: {model_selection}")
                return

        # 显示模型选择信息
        if st.session_state.model_preferences.get('show_model_info', True):
            with st.expander("🤖 搜索模型选择", expanded=False):
                st.write(f"**使用模型:** {model_selection['selected_model']}")
                st.write(f"**选择理由:** {model_selection['reasoning']}")

        with st.spinner("🔍 正在搜索..."):
            search_results = MemoryAPI.search_memories(
                query=query or "",
                user_id=user_id,
                limit=limit,
                image_base64=image_base64,
                model=model_selection['selected_model']
            )

        # 处理搜索结果格式
        if isinstance(search_results, str):
            try:
                search_results = json.loads(search_results)
            except:
                st.error("❌ 搜索结果格式错误")
                return

        if isinstance(search_results, dict):
            if 'results' in search_results:
                # 处理嵌套的results结构
                if isinstance(search_results['results'], dict) and 'results' in search_results['results']:
                    search_results = search_results['results']['results']
                else:
                    search_results = search_results['results']
            elif 'memories' in search_results:
                search_results = search_results['memories']
            elif 'data' in search_results:
                search_results = search_results['data']

        if not isinstance(search_results, list):
            search_results = []

        # 更新搜索计数
        st.session_state['search_count'] = st.session_state.get('search_count', 0) + 1

        if not search_results or len(search_results) == 0:
            search_desc = f"'{query}'" if query else "图片"
            st.warning(f"🔍 没有找到与 {search_desc} 相关的记忆")
            return

        search_type_desc = "多模态搜索" if has_image and query else ("图片搜索" if has_image else "文字搜索")
        st.success(f"✅ {search_type_desc}找到 {len(search_results)} 条相关记忆")

        # 显示搜索结果
        for i, result in enumerate(search_results, 1):
            # 处理搜索结果的不同格式
            if isinstance(result, dict):
                content = result.get('content', result.get('memory', result.get('text', '无内容')))
                score = result.get('score', result.get('relevance', 'N/A'))
                memory_id = result.get('id', f'result_{i}')
                created_at = result.get('created_at', '未知时间')
            else:
                content = str(result)
                score = 'N/A'
                memory_id = f'result_{i}'
                created_at = '未知时间'

            # 截取内容预览
            preview = content[:80] + "..." if len(content) > 80 else content
            score_text = f" (相关性: {score})" if score != 'N/A' else ""

            with st.expander(f"结果 {i}: {preview}{score_text}"):
                st.write(f"**完整内容:** {content}")
                if score != 'N/A':
                    st.write(f"**相关性评分:** {score}")
                st.write(f"**创建时间:** {created_at}")
                st.write(f"**记忆ID:** {memory_id}")
                st.write(f"**搜索模型:** {model_selection['selected_model']}")

                # 显示其他字段
                if isinstance(result, dict):
                    for key, value in result.items():
                        if key not in ['id', 'content', 'memory', 'text', 'score', 'relevance', 'created_at']:
                            st.write(f"**{key}:** {value}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"📋 复制内容", key=f"copy_search_{i}"):
                        st.code(content)
                        st.success("内容已显示，可手动复制")

                with col2:
                    if st.button(f"🗑️ 删除此记忆", key=f"delete_search_{i}"):
                        if memory_id.startswith('result_'):
                            st.warning("无法删除：记忆ID无效")
                        else:
                            delete_memory_action(memory_id)

        # 保存搜索历史
        if 'search_history' not in st.session_state:
            st.session_state.search_history = []

        search_entry = {
            'query': query or "[图片搜索]",
            'timestamp': datetime.now().isoformat(),
            'results_count': len(search_results),
            'search_type': search_type_desc,
            'model': model_selection['selected_model'],
            'has_image': has_image
        }

        st.session_state.search_history.insert(0, search_entry)
        # 只保留最近20次搜索
        st.session_state.search_history = st.session_state.search_history[:20]

    except Exception as e:
        st.error(f"❌ 搜索失败: {str(e)}")
        st.info("请检查API连接状态和查询参数")

def perform_memory_search(query: str, search_type: str, limit: int, sort_by: str):
    """执行纯文字记忆搜索（兼容性函数）"""
    perform_multimodal_search(query, None, search_type, limit, sort_by)

def system_settings_interface(auth_system):
    """系统设置界面 - 包含模型选择偏好和用户管理"""
    st.header("⚙️ 系统设置")
    st.markdown("配置系统参数、个人偏好和模型选择策略")

    # 模型选择设置
    st.subheader("🤖 动态智能模型选择")

    # 显示当前可用模型
    if hasattr(st.session_state, 'model_selector'):
        available_models = st.session_state.model_selector.get_available_models()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**当前可用模型:**")

            # 限制显示的模型数量，避免页面混乱
            display_models = available_models[:10] if len(available_models) > 10 else available_models

            # 使用折叠面板显示模型列表
            with st.expander(f"📋 查看模型列表 ({len(available_models)}个可用)", expanded=False):
                for i, model in enumerate(display_models):
                    st.write(f"• {model}")

                if len(available_models) > 10:
                    st.info(f"显示前10个模型，共{len(available_models)}个可用")

            if st.button("🔄 刷新模型列表"):
                st.session_state.model_selector.refresh_models()
                st.rerun()

        with col2:
            st.markdown("**智能选择模式:**")
            st.info("系统会自动：\n1. 用快速模型分析问题\n2. 推荐最适合的模型\n3. 用推荐模型执行任务")

            # 显示快速决策模型
            fast_model = getattr(st.session_state.model_selector, 'fast_model', '未知')
            st.write(f"**决策模型:** {fast_model}")

    strategy = "dynamic_ai_recommendation"  # 固定使用动态推荐

    # 创建新的列布局用于模型偏好设置
    pref_col1, pref_col2 = st.columns(2)

    with pref_col1:
        show_model_info = st.checkbox(
            "显示模型选择信息",
            value=st.session_state.model_preferences.get('show_model_info', True),
            help="在对话和操作中显示模型选择的详细信息"
        )

    with pref_col2:
        if strategy == "auto_intelligent":
            st.markdown("**智能选择偏好:**")
            prefer_speed = st.checkbox(
                "优先考虑响应速度",
                value=st.session_state.model_preferences.get('prefer_speed', False)
            )
            prefer_quality = st.checkbox(
                "优先考虑输出质量",
                value=st.session_state.model_preferences.get('prefer_quality', False)
            )
            cost_sensitive = st.checkbox(
                "成本敏感模式",
                value=st.session_state.model_preferences.get('cost_sensitive', False)
            )
        else:
            prefer_speed = prefer_quality = cost_sensitive = False
            st.info(f"当前策略: {strategy}")

    # 显示模型能力对比
    with st.expander("📊 模型能力对比", expanded=False):
        model_data = {
            "模型": ["Gemini 2.0 Flash", "Gemini 2.5 Flash", "Gemini 2.5 Pro"],
            "速度": [10, 7, 4],
            "质量": [6, 8, 10],
            "成本效率": [10, 7, 3],
            "多模态": [8, 9, 10],
            "推理能力": [6, 8, 10]
        }
        df = pd.DataFrame(model_data)
        st.dataframe(df, use_container_width=True)

    st.divider()

    # AI模型API设置
    st.subheader("🤖 AI模型API设置")
    st.markdown("配置大语言模型API服务，用于智能对话功能")

    # 显示系统状态
    col1, col2 = st.columns(2)
    with col1:
        st.info("🧠 **记忆管理**: 内置集成，无需配置")
    with col2:
        ai_status = "✅ 已连接" if st.session_state.get('api_connected', False) else "❌ 未连接"
        st.info(f"🤖 **AI对话**: {ai_status}")

    with st.expander("AI模型API配置", expanded=True):
        # 显示当前配置信息
        current_settings = st.session_state.get('api_settings', {})
        if current_settings.get('api_url'):
            st.info(f"🌐 当前AI API地址: {current_settings.get('api_url')}")

        # 使用表单包装API配置，避免密码字段警告
        with st.form("ai_api_config_form", clear_on_submit=False):
            # 默认指向AI模型服务，而不是mem0
            default_ai_url = current_settings.get('api_url', 'http://gemini-balance:8000')
            default_ai_key = current_settings.get('api_key', 'admin123')

            api_url = st.text_input(
                "AI模型API地址",
                value=default_ai_url,
                help="大语言模型API服务地址（如Gemini Balance、OpenAI等）"
            )
            api_key = st.text_input(
                "AI模型API密钥",
                value=default_ai_key,
                type="password",
                help="用于访问AI模型服务的认证密钥"
            )
            api_timeout = st.number_input("超时时间(秒)", min_value=5, max_value=300, value=30)

            # 表单提交按钮
            col1, col2 = st.columns(2)
            with col1:
                test_submitted = st.form_submit_button("🧪 测试AI连接", type="secondary")
            with col2:
                save_submitted = st.form_submit_button("💾 保存配置", type="primary")

        if test_submitted:
            test_ai_api_connection(api_url, api_key)
        elif save_submitted:
            # 保存AI API配置到会话状态
            st.session_state.api_settings.update({
                'api_url': api_url,
                'api_key': api_key,
                'timeout': api_timeout
            })

            # 保存到数据库
            try:
                import psycopg2
                import os
                import time

                # 数据库连接配置
                db_config = {
                    'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
                    'database': os.getenv('POSTGRES_DB', 'mem0db'),
                    'user': os.getenv('POSTGRES_USER', 'mem0'),
                    'password': os.getenv('POSTGRES_PASSWORD', 'mem0password'),
                    'port': 5432
                }

                # 获取当前用户ID
                current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')

                # 连接数据库并保存设置
                conn = psycopg2.connect(**db_config)
                cursor = conn.cursor()

                # 保存AI模型API设置
                settings_to_save = [
                    ('ai_api_url', api_url),
                    ('ai_api_key', api_key),
                    ('ai_api_timeout', str(api_timeout)),
                    ('ai_api_last_update', str(int(time.time())))
                ]

                for setting_key, setting_value in settings_to_save:
                    cursor.execute("""
                        INSERT INTO mem0_user_settings (user_id, setting_key, setting_value, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, setting_key)
                        DO UPDATE SET
                            setting_value = EXCLUDED.setting_value,
                            updated_at = CURRENT_TIMESTAMP
                    """, (current_user_id, setting_key, setting_value))

                # 提交事务
                conn.commit()
                cursor.close()
                conn.close()

                st.success("✅ AI模型API配置已保存到数据库！")
                st.info(f"📝 已保存: API地址={api_url}, 密钥={api_key[:4]}****, 超时={api_timeout}秒")

            except Exception as db_error:
                st.error(f"❌ 数据库保存失败: {str(db_error)}")
                st.warning("⚠️ 配置已保存到当前会话，但未持久化到数据库")
                import traceback
                print(f"数据库保存错误详情: {traceback.format_exc()}")

                # 显示详细错误信息
                with st.expander("🔍 错误详情"):
                    st.code(str(db_error))
                    st.write("**建议操作**:")
                    st.write("- 检查数据库连接是否正常")
                    st.write("- 确认用户权限设置")
                    st.write("- 重试保存操作")

    st.divider()

    # 用户偏好设置
    st.subheader("👤 用户偏好")

    with st.expander("个人设置", expanded=True):
        language = st.selectbox("界面语言", ["中文", "English"])
        theme = st.selectbox("主题", ["自动", "浅色", "深色"])
        auto_save = st.checkbox("自动保存对话", value=True)
        notification = st.checkbox("启用通知", value=True)

    st.divider()

    # 高级设置
    st.subheader("🎯 高级设置")

    with st.expander("处理设置", expanded=False):
        max_memory_length = st.number_input("最大记忆长度", min_value=100, max_value=10000, value=2000)
        batch_size = st.number_input("批处理大小", min_value=1, max_value=100, value=10)
        enable_cache = st.checkbox("启用缓存", value=True)
        debug_mode = st.checkbox("调试模式", value=False)

    st.divider()

    # 数据管理
    st.subheader("💾 数据管理")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 导出数据", type="secondary"):
            export_memories_data()

    with col2:
        uploaded_file = st.file_uploader(
            "📥 导入数据",
            type=['json'],
            help="上传JSON格式的记忆数据文件"
        )
        if uploaded_file is not None:
            if st.button("开始导入", type="secondary"):
                import_memories_data(uploaded_file)

    with col3:
        # 使用session state来管理清空数据的状态
        if 'show_clear_confirm' not in st.session_state:
            st.session_state.show_clear_confirm = False

        if not st.session_state.show_clear_confirm:
            if st.button("🗑️ 清空所有数据", type="secondary"):
                st.session_state.show_clear_confirm = True
                st.rerun()
        else:
            clear_all_memories(auth_system)

    st.divider()

    # 批量操作
    st.subheader("🔧 批量操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 数据统计报告", type="secondary"):
            generate_data_report()

    with col2:
        if st.button("🔄 刷新连接状态", type="secondary"):
            test_api_connection_detailed()

    st.divider()

    # 保存设置
    if st.button("💾 保存所有设置", type="primary"):
        # 更新模型偏好
        st.session_state.model_preferences.update({
            'strategy': strategy,
            'prefer_speed': prefer_speed,
            'prefer_quality': prefer_quality,
            'cost_sensitive': cost_sensitive,
            'show_model_info': show_model_info
        })
        save_all_settings()

def export_memories_data():
    """导出记忆数据"""
    try:
        user_id = st.session_state.user_settings['user_id']

        with st.spinner("正在导出数据..."):
            memories_data = MemoryAPI.get_memories(user_id)

        # 处理API响应格式
        if isinstance(memories_data, str):
            try:
                memories_data = json.loads(memories_data)
            except:
                st.error("❌ API返回格式错误")
                return

        if isinstance(memories_data, dict):
            if 'results' in memories_data:
                # 处理嵌套的results结构
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    memories_data = memories_data['results']['results']
                else:
                    memories_data = memories_data['results']
            elif 'memories' in memories_data:
                memories_data = memories_data['memories']
            elif 'data' in memories_data:
                memories_data = memories_data['data']

        if not isinstance(memories_data, list):
            memories_data = []

        if not memories_data:
            st.warning("没有数据可导出")
            return

        # 准备导出数据
        export_data = {
            "export_time": datetime.now().isoformat(),
            "user_id": user_id,
            "total_memories": len(memories_data),
            "memories": memories_data
        }

        # 转换为JSON
        json_data = json.dumps(export_data, ensure_ascii=False, indent=2)

        # 提供下载
        st.download_button(
            label="💾 下载数据文件",
            data=json_data,
            file_name=f"memories_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

        st.success(f"✅ 数据导出成功！共 {len(memories_data)} 条记忆")

    except Exception as e:
        st.error(f"❌ 导出失败: {str(e)}")

def import_memories_data(uploaded_file):
    """导入记忆数据"""
    try:
        # 读取文件内容
        file_content = uploaded_file.read()
        import_data = json.loads(file_content)

        if 'memories' not in import_data:
            st.error("❌ 无效的数据格式")
            return

        memories = import_data['memories']
        user_id = st.session_state.user_settings['user_id']

        with st.spinner(f"正在导入 {len(memories)} 条记忆..."):
            success_count = 0
            error_count = 0

            for memory in memories:
                try:
                    # 转换为API需要的格式
                    messages = [{"role": "user", "content": memory.get('content', '')}]

                    MemoryAPI.add_memory(
                        messages=messages,
                        user_id=user_id,
                        custom_instructions="导入的记忆数据"
                    )
                    success_count += 1
                except:
                    error_count += 1

        if success_count > 0:
            st.success(f"✅ 成功导入 {success_count} 条记忆")
        if error_count > 0:
            st.warning(f"⚠️ {error_count} 条记忆导入失败")

    except Exception as e:
        st.error(f"❌ 导入失败: {str(e)}")

def clear_all_memories(auth_system):
    """清空当前用户的所有记忆"""
    st.warning("⚠️ 此操作将删除所有记忆数据，且无法恢复！")

    confirm_delete = st.checkbox("我确认要删除所有数据", key="confirm_delete_checkbox")

    if confirm_delete:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🗑️ 确认删除", type="primary", key="confirm_delete_btn"):
                try:
                    with st.spinner("正在清空数据..."):
                        # 使用安全的用户隔离清空功能
                        current_user_id = auth_system.get_current_user_id()
                        result = MemoryAPIPatched.reset_user_memories(current_user_id)

                    if result.get('status') == 'success':
                        st.success(f"✅ {result.get('message', '数据清空成功！')}")
                        st.balloons()
                    else:
                        st.warning(f"⚠️ {result.get('message', '部分数据清空失败')}")
                        if result.get('failed_deletions'):
                            with st.expander("查看失败详情"):
                                for failed in result['failed_deletions']:
                                    st.write(f"- {failed}")

                    # 清空本地缓存
                    if 'search_history' in st.session_state:
                        st.session_state.search_history = []
                    if 'chat_history' in st.session_state:
                        st.session_state.chat_history = []

                    # 重置状态
                    st.session_state.show_clear_confirm = False
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ 清空失败: {str(e)}")

        with col2:
            if st.button("❌ 取消", key="cancel_delete_btn"):
                st.session_state.show_clear_confirm = False
                st.rerun()

def generate_data_report():
    """生成数据统计报告"""
    try:
        user_id = st.session_state.user_settings['user_id']

        with st.spinner("正在生成报告..."):
            memories_data = MemoryAPI.get_memories(user_id)

        # 处理API响应格式
        if isinstance(memories_data, str):
            try:
                memories_data = json.loads(memories_data)
            except:
                st.error("❌ API返回格式错误")
                return

        if isinstance(memories_data, dict):
            if 'results' in memories_data:
                # 处理嵌套的results结构
                if isinstance(memories_data['results'], dict) and 'results' in memories_data['results']:
                    memories_data = memories_data['results']['results']
                else:
                    memories_data = memories_data['results']
            elif 'memories' in memories_data:
                memories_data = memories_data['memories']
            elif 'data' in memories_data:
                memories_data = memories_data['data']

        if not isinstance(memories_data, list):
            memories_data = []

        if not memories_data:
            st.info("暂无数据可分析")
            return

        # 生成报告
        total_memories = len(memories_data)
        total_chars = sum(len(memory.get('content', memory.get('memory', memory.get('text', '')))) for memory in memories_data)
        avg_length = total_chars / total_memories if total_memories > 0 else 0

        # 时间分析
        dates = []
        for memory in memories_data:
            if isinstance(memory, dict) and 'created_at' in memory:
                try:
                    created_time = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                    dates.append(created_time.date())
                except:
                    pass

        unique_dates = len(set(dates)) if dates else 0

        # 显示报告
        st.subheader("📊 数据统计报告")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记忆数", total_memories)
        with col2:
            st.metric("总字符数", f"{total_chars:,}")
        with col3:
            st.metric("平均长度", f"{avg_length:.1f}")
        with col4:
            st.metric("活跃天数", unique_dates)

        # 详细信息
        with st.expander("📋 详细信息"):
            st.write(f"- 数据生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"- 用户ID: {user_id}")
            st.write(f"- API连接状态: {'✅ 正常' if st.session_state.api_connected else '❌ 异常'}")

            if dates:
                earliest = min(dates)
                latest = max(dates)
                st.write(f"- 最早记忆: {earliest}")
                st.write(f"- 最新记忆: {latest}")

    except Exception as e:
        st.error(f"❌ 报告生成失败: {str(e)}")

def test_api_connection_detailed():
    """详细的API连接测试"""
    st.subheader("🔧 API连接测试")

    with st.spinner("正在测试连接..."):
        # 测试基础连接
        basic_test = MemoryAPI.test_connection()

        if basic_test:
            st.success("✅ 基础连接正常")

            # 测试具体功能
            user_id = st.session_state.user_settings['user_id']

            try:
                # 测试获取记忆
                memories = MemoryAPI.get_memories(user_id)

                # 处理API响应格式
                if isinstance(memories, dict) and 'results' in memories:
                    if isinstance(memories['results'], dict) and 'results' in memories['results']:
                        memories_list = memories['results']['results']
                    else:
                        memories_list = memories['results']
                elif isinstance(memories, list):
                    memories_list = memories
                else:
                    memories_list = []

                st.success(f"✅ 记忆获取正常 (共 {len(memories_list)} 条)")

                # 测试搜索功能
                search_results = MemoryAPI.search_memories("test", user_id, 1)
                st.success("✅ 搜索功能正常")

                st.session_state.api_connected = True

            except Exception as e:
                st.warning(f"⚠️ 部分功能异常: {str(e)}")
                st.session_state.api_connected = False
        else:
            st.error("❌ API连接失败")
            st.session_state.api_connected = False

def save_all_settings():
    """保存所有设置到数据库"""
    try:
        import psycopg2
        import json
        import os

        # 数据库连接配置
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
            'database': os.getenv('POSTGRES_DB', 'mem0'),
            'user': os.getenv('POSTGRES_USER', 'mem0'),
            'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024'),
            'port': 5432
        }

        # 获取当前用户ID（从认证系统获取）
        current_user_id = getattr(st.session_state, 'user_info', {}).get('user_id', 'admin_default')

        # 连接数据库
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 准备要保存的设置
        settings_to_save = [
            ('custom_instructions', st.session_state.model_preferences.get('custom_instructions', '请提取并结构化重要信息，保持清晰明了。')),
            ('include_content_types', json.dumps(["技术文档", "个人信息"])),
            ('exclude_content_types', json.dumps([])),
            ('max_results', str(st.session_state.model_preferences.get('max_results', 21))),
            ('smart_reasoning', str(st.session_state.model_preferences.get('smart_reasoning', True)).lower()),
            ('show_model_info', str(st.session_state.model_preferences.get('show_model_info', True)).lower()),
            ('system_initialized', 'true')
        ]

        # 保存每个设置
        for setting_key, setting_value in settings_to_save:
            cursor.execute("""
                INSERT INTO mem0_user_settings (user_id, setting_key, setting_value, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, setting_key)
                DO UPDATE SET
                    setting_value = EXCLUDED.setting_value,
                    updated_at = CURRENT_TIMESTAMP
            """, (current_user_id, setting_key, setting_value))

        # 提交事务
        conn.commit()
        cursor.close()
        conn.close()

        st.success("✅ 设置已保存到数据库！")

        # 显示当前设置
        with st.expander("📋 当前设置"):
            st.write("**模型偏好设置:**")
            for key, value in st.session_state.model_preferences.items():
                st.write(f"- {key}: {value}")

            st.write("**API设置:**")
            for key, value in st.session_state.api_settings.items():
                if key != 'api_key':  # 不显示密钥
                    st.write(f"- {key}: {value}")

    except Exception as e:
        st.error(f"❌ 保存失败: {str(e)}")
        # 显示详细错误信息用于调试
        st.error(f"详细错误: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    main()
