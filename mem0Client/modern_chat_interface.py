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

def handle_modern_chat_message(user_text: str, image_info: dict = None):
    """处理现代化聊天消息"""
    try:
        # 智能模型选择
        has_image = image_info is not None and image_info.get("success", False)
        content_for_analysis = user_text or "图片分析请求"

        # 确保model_selector已初始化
        if 'model_selector' not in st.session_state:
            from dynamic_model_selector import DynamicModelSelector
            # 从用户配置中获取API密钥
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
        
        # 添加用户消息到聊天历史
        user_message = {
            "role": "user",
            "content": user_text,
            "timestamp": st.session_state.get('current_time', ''),
            "model_info": model_info
        }
        
        if image_info:
            user_message["image_info"] = image_info
            
        st.session_state.chat_history.append(user_message)
        
        # 简化的生产级对话系统

        # 获取用户ID
        user_id = getattr(st.session_state, 'user_settings', {}).get('user_id', 'default_user')

        # 第一步：调用gemini-balance获取AI回复
        # 使用Docker内部网络地址
        gemini_balance_url = os.getenv('GEMINI_BALANCE_URL', 'http://gemini-balance:8000/v1')
        # 从用户配置中获取API密钥，如果没有则使用环境变量或默认值
        auth_token = st.session_state.get('api_settings', {}).get('api_key') or os.getenv('INTEGRATED_GEMINI_BALANCE_TOKEN', os.getenv('GEMINI_BALANCE_TOKEN', 'q1q2q3q4'))

        # 构建对话消息
        messages = [
            {
                "role": "system",
                "content": "你是一个智能助手，能够帮助用户处理各种问题。请用中文回复。"
            }
        ]

        # 添加聊天历史（最近5条）
        recent_history = st.session_state.chat_history[-10:] if len(st.session_state.chat_history) > 0 else []
        for msg in recent_history:
            if msg['role'] in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": user_text
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

        response = requests.post(
            f"{gemini_balance_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"Gemini Balance API调用失败: {response.status_code} - {response.text}")

        result = response.json()
        ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "抱歉，我无法处理您的请求。")

        # 第二步：异步保存对话记忆到mem0-api（不阻塞用户体验）
        try:
            from api_patches import MemoryAPIPatched
            api_base_url = MemoryAPIPatched.get_api_url()

            # 构建对话记录用于记忆保存
            conversation_content = f"用户: {user_text}\n助手: {ai_response}"

            memory_payload = {
                "messages": [{"role": "user", "content": conversation_content}],
                "user_id": user_id
            }

            # 异步保存记忆（不等待结果）
            requests.post(
                f"{api_base_url}/memories",
                json=memory_payload,
                timeout=5
            )
        except Exception as memory_error:
            # 记忆保存失败不影响对话功能
            print(f"记忆保存失败: {memory_error}")
            pass

        # 添加AI回复到聊天历史
        assistant_message = {
            "role": "assistant",
            "content": ai_response,
            "timestamp": st.session_state.get('current_time', ''),
            "model": model_info.get('selected_model', 'unknown')
        }
        st.session_state.chat_history.append(assistant_message)

        # 更新学习状态
        st.session_state.learning_state = "active"

        st.rerun()

    except requests.exceptions.Timeout:
        st.error("⏰ 请求超时，请检查网络连接或稍后重试")
        st.info("💡 建议：检查AI服务是否正常运行")
    except requests.exceptions.ConnectionError:
        st.error("🔌 无法连接到AI服务，请检查服务状态")
        st.info("💡 建议：确认gemini-balance服务正在运行")
    except Exception as e:
        st.error(f"❌ 处理消息时出错: {str(e)}")
        st.info("💡 建议：\n1. 检查网络连接\n2. 确认AI服务正常运行\n3. 如问题持续，请联系管理员")

def modern_smart_chat_interface():
    """现代化智能对话界面"""
    st.header("🧠 智能对话 - AI记忆学习中心")
    st.markdown("与AI助手对话，观察AI如何自动学习和记忆您的偏好")

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
                    st.write(message['content'])
                    if 'model' in message:
                        st.caption(f"🤖 模型: {message['model']}")

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
                        # 使用第一张图片
                        first_image = user_images[0]
                        
                        # 将PIL图片转换为base64
                        img_buffer = io.BytesIO()
                        first_image.save(img_buffer, format='PNG')
                        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                        
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
