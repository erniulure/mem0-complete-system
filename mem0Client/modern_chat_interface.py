"""
现代化聊天界面 - 使用streamlit-chat-prompt组件
"""

import streamlit as st
import base64
import io
import requests
import json
import os
from datetime import datetime
from streamlit_chat_prompt import prompt
import threading
import time
import logging
from typing import Dict, List, Optional
import re

class EnhancedStatusIndicator:
    """增强的状态指示器 - 提供更好的用户体验"""

    @staticmethod
    def show_memory_search_progress():
        """显示记忆搜索进度"""
        progress_container = st.empty()

        # 模拟搜索进度
        search_steps = [
            "🔍 正在搜索相关记忆...",
            "📚 分析历史对话内容...",
            "🧠 匹配语义相关信息...",
            "✨ 构建智能上下文..."
        ]

        for i, step in enumerate(search_steps):
            progress_container.info(f"{step} ({i+1}/{len(search_steps)})")
            time.sleep(0.3)  # 短暂延迟显示进度

        progress_container.empty()

    @staticmethod
    def show_ai_thinking_animation():
        """显示AI思考动画"""
        thinking_container = st.empty()

        thinking_frames = [
            "🤖 AI正在思考中.",
            "🤖 AI正在思考中..",
            "🤖 AI正在思考中...",
            "🧠 分析问题内容.",
            "🧠 分析问题内容..",
            "🧠 分析问题内容...",
            "⚡ 生成智能回复.",
            "⚡ 生成智能回复..",
            "⚡ 生成智能回复..."
        ]

        for frame in thinking_frames:
            thinking_container.info(frame)
            time.sleep(0.2)

        return thinking_container

    @staticmethod
    def show_memory_storage_progress():
        """显示记忆存储进度"""
        storage_steps = [
            "🔍 分析对话重要性...",
            "📝 提取关键信息...",
            "🧠 生成记忆向量...",
            "💾 存储到记忆库...",
            "✅ 记忆存储完成"
        ]

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, step in enumerate(storage_steps):
            progress = (i + 1) / len(storage_steps)
            progress_bar.progress(progress)
            status_text.info(f"{step} ({int(progress * 100)}%)")
            time.sleep(0.5)

        return status_text, progress_bar

class StreamingResponseHandler:
    """流式响应处理器 - 处理AI API的流式响应"""

    @staticmethod
    def parse_sse_line(line: str) -> Dict:
        """解析Server-Sent Events格式的数据行"""
        if line.startswith('data: '):
            data_content = line[6:]  # 移除'data: '前缀
            if data_content.strip() == '[DONE]':
                return {'done': True}
            try:
                import json
                return json.loads(data_content)
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def stream_ai_response(url: str, payload: Dict, headers: Dict, timeout: int = 30):
        """发送流式AI请求并逐步返回响应内容"""
        # 启用流式响应
        payload['stream'] = True

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=True)

            if response.status_code != 200:
                yield f"❌ API调用失败: {response.status_code} - {response.text}"
                return

            accumulated_content = ""

            # 逐行读取流式响应
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    parsed_data = StreamingResponseHandler.parse_sse_line(line)

                    if parsed_data.get('done'):
                        break

                    # 提取增量内容
                    choices = parsed_data.get('choices', [])
                    if choices:
                        delta = choices[0].get('delta', {})
                        content = delta.get('content', '')

                        if content:
                            accumulated_content += content
                            yield accumulated_content

            # 如果没有收到任何内容，返回默认消息
            if not accumulated_content:
                yield "抱歉，我无法处理您的请求。"

        except Exception as e:
            yield f"❌ 处理流式响应时出错: {str(e)}"

class AsyncMemoryProcessor:
    """异步记忆处理器 - 在后台处理记忆存储任务"""

    def __init__(self):
        self.processing_thread = None
        self.is_running = False

    def start_background_processor(self):
        """启动后台记忆处理线程"""
        if not self.is_running:
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_memory_tasks, daemon=True)
            self.processing_thread.start()

    def _process_memory_tasks(self):
        """后台处理记忆存储任务"""
        while self.is_running:
            try:
                # 检查是否有待处理的记忆任务
                if 'async_memory_tasks' in st.session_state:
                    pending_tasks = [task for task in st.session_state.async_memory_tasks if task['status'] == 'pending']

                    for task in pending_tasks:
                        try:
                            # 标记任务为处理中
                            task['status'] = 'processing'

                            # 获取记忆管理器
                            if 'memory_manager' in st.session_state:
                                memory_manager = st.session_state.memory_manager

                                # 执行记忆存储
                                result = memory_manager.intelligent_store_memory_sync(
                                    task['user_text'],
                                    task['ai_response']
                                )

                                # 更新任务状态
                                task['status'] = 'completed'
                                task['result'] = result

                                # 更新对应的聊天记录
                                chat_index = task['chat_index']
                                if (chat_index < len(st.session_state.chat_history) and
                                    st.session_state.chat_history[chat_index]['role'] == 'assistant'):
                                    st.session_state.chat_history[chat_index]['memory_status'] = 'completed'
                                    st.session_state.chat_history[chat_index]['memory_storage'] = result

                            else:
                                task['status'] = 'failed'
                                task['error'] = 'Memory manager not available'

                        except Exception as e:
                            task['status'] = 'failed'
                            task['error'] = str(e)
                            logging.error(f"异步记忆存储失败: {e}")

                            # 更新聊天记录状态
                            chat_index = task['chat_index']
                            if (chat_index < len(st.session_state.chat_history) and
                                st.session_state.chat_history[chat_index]['role'] == 'assistant'):
                                st.session_state.chat_history[chat_index]['memory_status'] = 'failed'

                # 清理完成的任务（保留最近10个）
                if 'async_memory_tasks' in st.session_state:
                    completed_tasks = [task for task in st.session_state.async_memory_tasks if task['status'] in ['completed', 'failed']]
                    if len(completed_tasks) > 10:
                        # 只保留最近的10个完成任务
                        st.session_state.async_memory_tasks = [
                            task for task in st.session_state.async_memory_tasks
                            if task['status'] == 'pending' or task in completed_tasks[-10:]
                        ]

            except Exception as e:
                logging.error(f"异步记忆处理器错误: {e}")

            # 每秒检查一次
            time.sleep(1)

    def stop(self):
        """停止后台处理器"""
        self.is_running = False

class SimpleImageProcessor:
    """简单的图片处理器备用类"""

    @staticmethod
    def process_image(image_data):
        """简单的图片处理"""
        try:
            from PIL import Image
            import base64
            import io

            if isinstance(image_data, str):
                # base64字符串
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]

                img_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(img_bytes))
            else:
                # 文件对象
                img = Image.open(image_data)

            # 获取基本信息
            width, height = img.size
            format_type = img.format or 'PNG'

            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format=format_type)
            size_bytes = len(buffer.getvalue())
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            return {
                "success": True,
                "base64": img_base64,
                "width": width,
                "height": height,
                "format": format_type,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / 1024 / 1024, 2)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

def ensure_multimodal_processor():
    """确保multimodal_processor已初始化"""
    if 'multimodal_processor' not in st.session_state:
        try:
            from multimodal_model_selector import MultimodalProcessor
            st.session_state.multimodal_processor = MultimodalProcessor()
        except Exception as e:
            st.error(f"❌ 初始化多模态处理器失败: {str(e)}")
            # 创建一个简单的备用处理器
            st.session_state.multimodal_processor = SimpleImageProcessor()

def handle_modern_chat_message(user_text: str, image_info: dict = None):
    """处理现代化聊天消息 - 集成智能记忆功能"""
    try:
        # 初始化智能记忆管理器
        if 'memory_manager' not in st.session_state:
            from intelligent_memory_manager import IntelligentMemoryManager
            from api_patches import MemoryAPIPatched

            user_id = getattr(st.session_state, 'user_settings', {}).get('user_id', 'default_user')
            mem0_api_url = MemoryAPIPatched.get_api_url()

            st.session_state.memory_manager = IntelligentMemoryManager(
                mem0_api_url=mem0_api_url,
                user_id=user_id
            )

        memory_manager = st.session_state.memory_manager

        # 智能模型选择
        has_image = image_info is not None and image_info.get("success", False)
        content_for_analysis = user_text or "图片分析请求"

        # 确保model_selector已初始化
        if 'model_selector' not in st.session_state:
            from dynamic_model_selector import DynamicModelSelector
            api_key = st.session_state.get('api_settings', {}).get('api_key', 'q1q2q3q4')
            st.session_state.model_selector = DynamicModelSelector(
                api_base_url='http://gemini-balance:8000',
                api_key=api_key
            )

        # 选择合适的模型
        model_info = st.session_state.model_selector.select_optimal_model(
            user_query=content_for_analysis,
            has_image=has_image
        )

        # 🧠 简化记忆检索：默认总是检索记忆（除非是明显的垃圾内容）
        should_skip_memory = (
            len(user_text.strip()) < 2 or  # 太短
            user_text.strip() in ['hi', 'hello', '你好', 'ok', 'yes', 'no'] or  # 简单问候
            user_text.strip().startswith('/')  # 命令
        )

        if not should_skip_memory:
            # 🎯 使用增强的状态指示器
            search_progress = st.empty()
            search_progress.info("🔍 正在搜索相关记忆...")

            # 🔍 搜索相关记忆（使用同步版本）
            relevant_memories = memory_manager.search_relevant_memories_sync(user_text, limit=5)

            search_progress.success(f"✅ 找到 {len(relevant_memories)} 条相关记忆")
            time.sleep(0.5)  # 短暂显示结果
            search_progress.empty()

            # 📝 构建增强的上下文
            enhanced_user_input = memory_manager.build_context_with_memories(
                user_text, relevant_memories, {'needs_memory': True, 'confidence': 1.0}
            )
        else:
            enhanced_user_input = user_text
            relevant_memories = []

        # 简化的记忆分析结果
        memory_analysis = {
            'needs_memory': not should_skip_memory,
            'confidence': 1.0 if not should_skip_memory else 0.0,
            'trigger_type': 'default' if not should_skip_memory else 'skip',
            'keywords': []
        }

        # 添加用户消息到聊天历史
        user_message = {
            "role": "user",
            "content": user_text,
            "timestamp": st.session_state.get('current_time', ''),
            "model_info": model_info,
            "memory_analysis": memory_analysis,
            "used_memories": len(relevant_memories)
        }

        if image_info:
            user_message["image_info"] = image_info

        st.session_state.chat_history.append(user_message)
        
        # 🤖 智能对话系统 - 集成记忆功能

        # 获取用户ID
        user_id = getattr(st.session_state, 'user_settings', {}).get('user_id', 'default_user')

        # 调用gemini-balance获取AI回复
        gemini_balance_url = os.getenv('GEMINI_BALANCE_URL', 'http://gemini-balance:8000/v1')
        auth_token = st.session_state.get('api_settings', {}).get('api_key') or os.getenv('INTEGRATED_GEMINI_BALANCE_TOKEN', os.getenv('GEMINI_BALANCE_TOKEN', 'q1q2q3q4'))

        # 构建智能对话消息
        messages = [
            {
                "role": "system",
                "content": """你是一个具有记忆能力的智能助手。你能够：
1. 记住用户的个人信息、偏好和历史对话
2. 基于历史记忆提供个性化的回复
3. 自然地引用相关的历史信息
4. 在信息不确定时主动询问用户确认

请用中文回复，保持对话的自然性和连贯性。"""
            }
        ]

        # 添加聊天历史（最近5条，不包括当前消息）
        recent_history = st.session_state.chat_history[-10:] if len(st.session_state.chat_history) > 1 else []
        for msg in recent_history:
            if msg['role'] in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # 添加增强的用户消息（包含记忆上下文和图片）
        user_message_content = enhanced_user_input  # 使用增强的输入而不是原始输入

        # 如果有图片，构建多模态消息格式
        if image_info and image_info.get("success"):
            # 使用OpenAI兼容的多模态消息格式
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message_content
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_info.get('format', 'png').lower()};base64,{image_info['base64']}"
                        }
                    }
                ]
            })
        else:
            # 纯文本消息
            messages.append({
                "role": "user",
                "content": user_message_content
            })

        # 调用gemini-balance API
        payload = {
            "model": model_info.get('selected_model', 'gemini-1.5-flash'),
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

        # 🚀 流式AI响应实现 - 使用真正的流式API
        ai_response = ""

        # 🎯 显示增强的AI思考状态
        thinking_status = st.empty()
        thinking_status.info("🧠 AI正在分析您的问题...")

        # 先添加一个占位符到聊天历史
        placeholder_index = len(st.session_state.chat_history)
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": "⚡ 正在生成回复...",
            "timestamp": st.session_state.get('current_time', ''),
            "model": model_info.get('selected_model', 'unknown'),
            "memory_status": "pending",
            "streaming": True,
            "generation_stage": "thinking"
        })

        # 使用流式API获取回复
        try:
            # 启用流式响应
            payload['stream'] = True

            response = requests.post(
                f"{gemini_balance_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
                stream=True
            )

            if response.status_code != 200:
                raise Exception(f"Gemini Balance API调用失败: {response.status_code} - {response.text}")

            accumulated_content = ""
            first_content_received = False

            # 更新状态：开始接收流式响应
            thinking_status.info("📡 正在接收AI回复...")

            # 处理流式响应
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith('data: '):
                    data_content = line[6:]  # 移除'data: '前缀

                    if data_content.strip() == '[DONE]':
                        break

                    try:
                        import json
                        parsed_data = json.loads(data_content)
                        choices = parsed_data.get('choices', [])

                        if choices:
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')

                            if content:
                                accumulated_content += content

                                # 第一次收到内容时更新状态
                                if not first_content_received:
                                    thinking_status.success("✨ 开始生成回复...")
                                    first_content_received = True

                                # 更新聊天历史中的消息
                                st.session_state.chat_history[placeholder_index]["content"] = accumulated_content
                                st.session_state.chat_history[placeholder_index]["streaming"] = True
                                st.session_state.chat_history[placeholder_index]["generation_stage"] = "streaming"

                    except json.JSONDecodeError:
                        continue

            ai_response = accumulated_content if accumulated_content else "抱歉，我无法处理您的请求。"

            # 完成流式响应，更新最终状态
            thinking_status.success("🎉 AI回复生成完成！")
            time.sleep(0.5)
            thinking_status.empty()

            st.session_state.chat_history[placeholder_index]["content"] = ai_response
            st.session_state.chat_history[placeholder_index]["streaming"] = False
            st.session_state.chat_history[placeholder_index]["memory_status"] = "processing"
            st.session_state.chat_history[placeholder_index]["generation_stage"] = "completed"

        except Exception as e:
            ai_response = f"❌ 获取AI回复时出错: {str(e)}"
            # 更新错误状态
            thinking_status.error(f"❌ AI回复生成失败: {str(e)}")
            time.sleep(1)
            thinking_status.empty()

            # 更新错误消息
            st.session_state.chat_history[placeholder_index]["content"] = ai_response
            st.session_state.chat_history[placeholder_index]["streaming"] = False
            st.session_state.chat_history[placeholder_index]["memory_status"] = "failed"
            st.session_state.chat_history[placeholder_index]["generation_stage"] = "failed"

        # 🧠 智能记忆存储：异步处理，不阻塞用户界面
        memory_storage_result = None

        # AI回复已通过流式响应添加到聊天历史，现在启动异步记忆存储

        # 异步启动记忆存储任务
        try:
            # 使用session state来跟踪异步任务
            if 'async_memory_tasks' not in st.session_state:
                st.session_state.async_memory_tasks = []

            # 创建异步任务信息
            task_info = {
                'user_text': user_text,
                'ai_response': ai_response,
                'chat_index': len(st.session_state.chat_history) - 1,  # 记录对应的聊天记录索引
                'status': 'pending',
                'timestamp': datetime.now()
            }
            st.session_state.async_memory_tasks.append(task_info)

            # 显示增强的后台处理提示
            memory_status = st.empty()
            memory_status.info("🧠 启动智能记忆存储...")
            time.sleep(0.3)
            memory_status.success("✅ 记忆存储任务已加入队列，正在后台处理")
            time.sleep(1)
            memory_status.empty()

        except Exception as memory_error:
            # 记忆存储失败不影响对话功能
            print(f"启动异步记忆存储失败: {memory_error}")
            # 更新聊天记录中的记忆状态
            if st.session_state.chat_history:
                st.session_state.chat_history[-1]["memory_status"] = "failed"

        # AI回复已在上面的异步处理中添加到聊天历史
        # 更新最后一条消息的记忆信息
        if st.session_state.chat_history:
            last_message = st.session_state.chat_history[-1]
            last_message["used_memories"] = len(relevant_memories) if relevant_memories else 0

        # 更新学习状态
        st.session_state.learning_state = "active"

        # 对话成功后自动更新连接状态
        st.session_state.api_connected = True
        if 'api_settings' in st.session_state:
            st.session_state.api_settings['connected'] = True

        # 显示记忆透明度信息（可选）
        if relevant_memories:
            with st.expander(f"🧠 本次对话使用了 {len(relevant_memories)} 条历史记忆", expanded=False):
                for i, memory in enumerate(relevant_memories[:3], 1):
                    st.write(f"**记忆 {i}** (相关度: {memory.get('score', 0.0):.2f})")
                    st.write(memory.get('memory', '')[:200] + "..." if len(memory.get('memory', '')) > 200 else memory.get('memory', ''))
                    st.write("---")

        st.rerun()

    except requests.exceptions.Timeout:
        # 对话失败时更新连接状态
        st.session_state.api_connected = False
        if 'api_settings' in st.session_state:
            st.session_state.api_settings['connected'] = False
        st.error("⏰ 请求超时，请检查网络连接或稍后重试")
        st.info("💡 建议：检查AI服务是否正常运行")
    except requests.exceptions.ConnectionError:
        # 对话失败时更新连接状态
        st.session_state.api_connected = False
        if 'api_settings' in st.session_state:
            st.session_state.api_settings['connected'] = False
        st.error("🔌 无法连接到AI服务，请检查服务状态")
        st.info("💡 建议：确认gemini-balance服务正在运行")
    except Exception as e:
        # 对话失败时更新连接状态
        st.session_state.api_connected = False
        if 'api_settings' in st.session_state:
            st.session_state.api_settings['connected'] = False
        st.error(f"❌ 处理消息时出错: {str(e)}")
        st.info("💡 建议：\n1. 检查网络连接\n2. 确认AI服务正常运行\n3. 如问题持续，请联系管理员")

def modern_smart_chat_interface():
    """现代化智能对话界面"""
    st.header("🧠 智能对话 - AI记忆学习中心")
    st.markdown("与AI助手对话，观察AI如何自动学习和记忆您的偏好")

    # 添加自定义CSS样式
    st.markdown("""
    <style>
    .status-indicator {
        padding: 8px 12px;
        border-radius: 6px;
        margin: 4px 0;
        font-size: 0.9em;
        animation: pulse 2s infinite;
    }

    .status-thinking {
        background: linear-gradient(45deg, #e3f2fd, #bbdefb);
        border-left: 4px solid #2196f3;
    }

    .status-streaming {
        background: linear-gradient(45deg, #f3e5f5, #e1bee7);
        border-left: 4px solid #9c27b0;
    }

    .status-memory {
        background: linear-gradient(45deg, #e8f5e8, #c8e6c9);
        border-left: 4px solid #4caf50;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }

    .progress-container {
        background: #f5f5f5;
        border-radius: 10px;
        padding: 10px;
        margin: 8px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # 初始化异步记忆处理器
    if 'async_memory_processor' not in st.session_state:
        st.session_state.async_memory_processor = AsyncMemoryProcessor()
        st.session_state.async_memory_processor.start_background_processor()

    # 初始化异步任务列表
    if 'async_memory_tasks' not in st.session_state:
        st.session_state.async_memory_tasks = []

    # 创建左右分列布局
    chat_col, memory_col = st.columns([2, 1])

    with chat_col:
        st.subheader("💬 对话区域")

        # 显示聊天历史 - 使用现代化的聊天消息组件
        for message in st.session_state.chat_history:
            with st.chat_message(message['role']):
                if message['role'] == 'user':
                    st.write(message['content'])
                    # 显示图片（如果有）
                    if 'image_info' in message and message['image_info']:
                        st.caption("📷 包含图片")
                    # 显示模型信息（如果有）
                    if 'model_info' in message:
                        model_info = message['model_info']
                        st.caption(f"🤖 使用模型: {model_info.get('selected_model', 'unknown')}")
                else:
                    # 显示AI回复内容
                    st.write(message['content'])

                    # 显示模型信息
                    if 'model' in message:
                        st.caption(f"🤖 模型: {message['model']}")

                    # 显示生成阶段状态
                    if 'generation_stage' in message:
                        stage = message['generation_stage']
                        if stage == 'thinking':
                            st.caption("🧠 AI正在思考...")
                        elif stage == 'streaming':
                            st.caption("⚡ 正在生成回复...")
                        elif stage == 'completed':
                            st.caption("✨ 回复生成完成")
                        elif stage == 'failed':
                            st.caption("❌ 生成失败")

                    # 显示流式响应状态（向后兼容）
                    elif message.get('streaming', False):
                        st.caption("⚡ 正在生成回复...")

                    # 显示记忆处理状态
                    if 'memory_status' in message:
                        status = message['memory_status']
                        if status == 'pending':
                            st.caption("⏳ 准备存储记忆...")
                        elif status == 'processing':
                            st.caption("💭 记忆存储中...")
                        elif status == 'completed':
                            if 'memory_storage' in message and message['memory_storage']:
                                result = message['memory_storage']
                                if result.get('stored'):
                                    st.caption(f"✅ {result.get('reason', '记忆已存储')}")
                                else:
                                    st.caption(f"ℹ️ {result.get('reason', '未存储记忆')}")
                        elif status == 'failed':
                            st.caption("⚠️ 记忆存储失败")

                    # 显示使用的记忆数量
                    if 'used_memories' in message and message['used_memories'] > 0:
                        st.caption(f"🧠 使用了 {message['used_memories']} 条相关记忆")

                    # 显示响应时间标记（如果有）
                    if 'response_time' in message:
                        st.caption(f"⚡ {message['response_time']}")

        # 现代化聊天输入组件 - 支持Enter发送，Shift+Enter换行，剪贴板粘贴
        prompt_result = prompt(
            name="chat_input",
            key="modern_chat_prompt",
            placeholder="输入您的消息... (Enter发送，Shift+Enter换行，支持粘贴图片)",
            main_bottom=False,  # 不固定在页面底部，而是在对话区域内
        )

        # 处理现代化聊天输入
        if prompt_result:
            # 获取用户输入的文本
            user_text = prompt_result.text if prompt_result.text else ""
            user_text = user_text.strip()
            
            # 获取用户上传/粘贴的图片
            user_images = prompt_result.images if prompt_result.images else []
            
            if user_text or user_images:
                # 处理图片数据
                image_info = None
                if user_images:
                    try:
                        # 确保多模态处理器已初始化
                        ensure_multimodal_processor()

                        # 使用第一张图片
                        first_image = user_images[0]

                        # first_image 是 FileData 对象，直接使用其 data 属性（base64数据）
                        img_base64 = first_image.data

                        # 处理图片
                        image_info = st.session_state.multimodal_processor.process_image(img_base64)
                        if not image_info["success"]:
                            st.error(f"❌ 图片处理失败: {image_info['error']}")
                            image_info = None
                    except Exception as e:
                        st.error(f"❌ 图片处理异常: {str(e)}")
                        image_info = None
                
                # 发送消息
                if user_text:
                    handle_modern_chat_message(user_text, image_info)

        # 清空对话按钮
        if st.button("🧹 清空对话", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

    with memory_col:
        st.subheader("🧠 AI记忆学习")
        display_real_time_memory_learning()

        # 自动刷新机制 - 如果有活跃的记忆任务，每3秒刷新一次
        if 'async_memory_tasks' in st.session_state:
            active_tasks = [task for task in st.session_state.async_memory_tasks
                          if task['status'] in ['pending', 'processing']]
            if active_tasks:
                # 使用JavaScript自动刷新
                st.markdown("""
                <script>
                setTimeout(function() {
                    window.parent.document.querySelector('[data-testid="stAppViewContainer"]').dispatchEvent(
                        new KeyboardEvent('keydown', {key: 'r', ctrlKey: true})
                    );
                }, 3000);
                </script>
                """, unsafe_allow_html=True)

def display_real_time_memory_learning():
    """显示AI实时记忆学习过程"""

    # 显示异步记忆处理状态
    if 'async_memory_tasks' in st.session_state:
        pending_tasks = [task for task in st.session_state.async_memory_tasks if task['status'] == 'pending']
        processing_tasks = [task for task in st.session_state.async_memory_tasks if task['status'] == 'processing']

        if pending_tasks or processing_tasks:
            st.markdown("### ⚡ 记忆处理状态")
            total_active = len(pending_tasks) + len(processing_tasks)

            if processing_tasks:
                st.info(f"🧠 正在处理 {len(processing_tasks)} 个记忆任务...")
                # 显示处理进度
                for i, task in enumerate(processing_tasks[:3]):  # 最多显示3个
                    elapsed = (datetime.now() - task['timestamp']).total_seconds()
                    st.caption(f"任务 {i+1}: 已处理 {elapsed:.1f}秒")

            if pending_tasks:
                st.caption(f"📝 队列中还有 {len(pending_tasks)} 个任务等待处理")

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

    # 初始化变量
    all_memories = []
    user_id = getattr(st.session_state, 'user_settings', {}).get('user_id', 'default_user')
    import os
    api_base_url = getattr(st.session_state, 'api_base_url', os.getenv('MEM0_API_URL', 'http://localhost:8888'))

    try:

        # 获取记忆列表来计算统计信息
        import requests
        from datetime import datetime, date

        memories_response = requests.get(
            f"{api_base_url}/memories",
            params={"user_id": user_id},
            timeout=10
        )

        if memories_response.status_code == 200:
            memories_data = memories_response.json()

            # 处理API返回的数据结构
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
            total_memories = len(all_memories)
            today = date.today().isoformat()
            today_added = sum(1 for memory in all_memories
                            if memory.get('created_at', '').startswith(today))

            col1, col2 = st.columns(2)
            with col1:
                st.metric("总记忆数量", total_memories)
            with col2:
                st.metric("今日新增", today_added)

        else:
            st.error("❌ 无法获取记忆统计")
            
    except Exception as e:
        st.error(f"❌ 获取统计失败: {str(e)}")

    # 显示记忆标签云
    st.markdown("### 🏷️ 记忆标签")
    
    try:
        # 从已获取的记忆中提取标签
        if 'all_memories' in locals() and all_memories:
            # 提取记忆中的关键词作为标签
            tags = set()
            for memory in all_memories[:10]:  # 只处理最近10条
                content = memory.get('memory', memory.get('content', ''))
                # 简单的关键词提取
                words = content.split()
                for word in words:
                    if len(word) > 2 and word.isalpha():
                        tags.add(word)

            if tags:
                tag_list = list(tags)[:8]  # 最多显示8个标签
                cols = st.columns(2)
                for i, tag in enumerate(tag_list):
                    with cols[i % 2]:
                        st.button(f"#{tag}", disabled=True, key=f"tag_{i}")
            else:
                st.info("🏷️ 暂无标签")
        else:
            st.info("🏷️ 暂无标签")

    except Exception as e:
        st.info("🏷️ 标签加载中...")

    # 学习状态指示器
    st.markdown("### ⚡ 学习状态")
    
    if len(st.session_state.chat_history) > 0:
        st.success("🟢 AI正在积极学习中")
        st.write("AI会自动从每次对话中提取重要信息")
    else:
        st.info("🟡 等待对话开始")
