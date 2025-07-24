"""
简化的智能记忆管理器
基于简化设计理念：相信mem0内部智能，最小干预原则
"""

import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class IntelligentMemoryManager:
    """简化的智能记忆管理器 - 相信mem0内部智能"""

    def __init__(self, mem0_api_url: str, user_id: str):
        self.mem0_api_url = mem0_api_url.rstrip('/')
        self.user_id = user_id

        # 简化的垃圾过滤规则（只过滤明显无意义的内容）
        self.junk_patterns = [
            r'^(hi|hello|你好|ok|yes|no|嗯|哦|啊)$',  # 简单问候
            r'^.{1,2}$',  # 太短的内容
            r'^[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]*$',  # 只有符号
            r'^(\s)*$',  # 只有空白字符
        ]

    def is_junk_content(self, content: str) -> bool:
        """
        简单的垃圾内容过滤 - 只过滤明显无意义的内容
        """
        if not content or not content.strip():
            return True

        content_clean = content.strip().lower()

        # 检查垃圾模式
        import re
        for pattern in self.junk_patterns:
            if re.match(pattern, content_clean):
                return True

        return False

    def should_retrieve_memory(self, user_input: str) -> bool:
        """
        简化的记忆检索判断 - 默认检索，除非是明显的垃圾内容
        """
        return not self.is_junk_content(user_input)

    def should_store_memory(self, user_input: str, ai_response: str) -> bool:
        """
        简化的记忆存储判断 - 默认存储，除非是明显的垃圾内容
        """
        # 检查用户输入和AI回复是否都是垃圾内容
        user_is_junk = self.is_junk_content(user_input)
        ai_is_junk = self.is_junk_content(ai_response)

        # 如果都是垃圾内容，则不存储
        if user_is_junk and ai_is_junk:
            return False

        # 其他情况默认存储，让mem0的LLM来判断重要性
        return True

    def extract_search_keywords(self, user_input: str) -> List[str]:
        """
        简化的关键词提取 - 基本的词语分割
        """
        import re
        # 简单的词语提取，让mem0的语义搜索来处理复杂性
        words = re.findall(r'\w+', user_input)
        # 过滤太短的词
        keywords = [word for word in words if len(word) > 1]
        return keywords[:5]  # 限制关键词数量

    async def search_relevant_memories(self, user_input: str, limit: int = 5) -> List[Dict]:
        """
        简化的记忆搜索 - 直接使用mem0的语义搜索
        """
        try:
            return await self._search_memories_api(user_input, limit)
        except Exception as e:
            logger.error(f"搜索记忆时出错: {str(e)}")
            return []

    async def _search_memories_api(self, query: str, limit: int) -> List[Dict]:
        """
        调用mem0 API搜索记忆 - 简化版本
        """
        try:
            search_url = f"{self.mem0_api_url}/search"
            payload = {
                "query": query,
                "user_id": self.user_id,
                "limit": limit
            }

            response = requests.post(search_url, json=payload, timeout=30)

            if response.status_code == 200:
                search_results = response.json()

                # 处理嵌套的results结构
                results_data = search_results.get('results', {})
                if isinstance(results_data, dict) and 'results' in results_data:
                    # 新的API格式: {"results": {"results": [...]}}
                    results_list = results_data['results']
                elif isinstance(results_data, list):
                    # 旧的API格式: {"results": [...]}
                    results_list = results_data
                else:
                    results_list = []

                memories = []
                for result in results_list:
                    memory = {
                        'id': result.get('id', ''),
                        'memory': result.get('memory', ''),
                        'score': result.get('score', 0.0),
                        'created_at': result.get('created_at', ''),
                        'updated_at': result.get('updated_at', ''),
                        'metadata': result.get('metadata', {})
                    }
                    memories.append(memory)

                return memories
            else:
                logger.warning(f"记忆搜索API返回: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"调用搜索API时出错: {str(e)}")
            return []



    def build_context_with_memories(self, user_input: str, memories: List[Dict],
                                   analysis_result: Dict = None) -> str:
        """
        简化的上下文构建 - 直接整合记忆到用户输入
        """
        if not memories:
            return user_input

        # 构建简单的上下文
        context_parts = []

        # 添加相关记忆
        if memories:
            context_parts.append("=== 相关历史信息 ===")
            for i, memory in enumerate(memories[:3], 1):
                memory_text = memory.get('memory', '')
                context_parts.append(f"{i}. {memory_text}")

        # 添加当前问题
        context_parts.append(f"\n=== 当前问题 ===")
        context_parts.append(f"{user_input}")

        # 简单的AI指令
        context_parts.append(f"\n请基于上述历史信息自然地回答用户问题。")

        return "\n".join(context_parts)



    # 同步版本的搜索方法（Streamlit需要）
    def search_relevant_memories_sync(self, user_input: str, limit: int = 5) -> List[Dict]:
        """
        同步版本的记忆搜索
        """
        try:
            return self._search_memories_api_sync(user_input, limit)
        except Exception as e:
            logger.error(f"搜索记忆时出错: {str(e)}")
            return []

    def intelligent_store_memory_sync(self, user_input: str, ai_response: str) -> Dict[str, any]:
        """
        简化的同步记忆存储
        """
        # 简单判断是否应该存储
        should_store = self.should_store_memory(user_input, ai_response)

        result = {
            'stored': False,
            'reason': '',
            'value_level': 'auto',  # 让mem0自己判断
            'confidence': 1.0 if should_store else 0.0
        }

        if should_store:
            # 构建简单的记忆内容
            memory_content = f"用户: {user_input}\nAI: {ai_response}"

            # 存储记忆（让mem0自己判断重要性）
            success = self._store_memory_api_sync(memory_content)

            if success:
                result['stored'] = True
                result['reason'] = "存储成功 - 交由mem0判断重要性"
            else:
                result['reason'] = "存储失败 - API错误"
        else:
            result['reason'] = "未存储 - 内容为垃圾信息"

        return result



    def _search_memories_api_sync(self, query: str, limit: int) -> List[Dict]:
        """
        同步版本的mem0 API搜索
        """
        try:
            search_url = f"{self.mem0_api_url}/search"
            payload = {
                "query": query,
                "user_id": self.user_id,
                "limit": limit
            }

            response = requests.post(search_url, json=payload, timeout=30)

            if response.status_code == 200:
                search_results = response.json()

                memories = []
                # 处理嵌套的results结构
                results_data = search_results.get('results', {})
                if isinstance(results_data, dict) and 'results' in results_data:
                    # 新的API格式: {"results": {"results": [...]}}
                    results_list = results_data['results']
                elif isinstance(results_data, list):
                    # 旧的API格式: {"results": [...]}
                    results_list = results_data
                else:
                    results_list = []

                for result in results_list:
                        memory = {
                            'id': result.get('id', ''),
                            'memory': result.get('memory', ''),
                            'score': result.get('score', 0.0),
                            'created_at': result.get('created_at', ''),
                            'updated_at': result.get('updated_at', ''),
                            'metadata': result.get('metadata', {})
                        }
                        memories.append(memory)

                return memories
            else:
                logger.warning(f"记忆搜索API返回: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"调用搜索API时出错: {str(e)}")
            return []

    def _store_memory_api_sync(self, memory_content: str) -> bool:
        """
        简化的同步记忆存储API调用
        """
        try:
            # 调用mem0 API存储记忆（让mem0自己判断重要性）
            add_url = f"{self.mem0_api_url}/memories"
            payload = {
                "messages": [{"role": "user", "content": memory_content}],
                "user_id": self.user_id
                # 不传入importance，让mem0的LLM自己判断
            }

            response = requests.post(add_url, json=payload, timeout=60)  # 存储操作需要更长时间

            if response.status_code == 200:
                logger.info(f"记忆存储成功，交由mem0判断重要性")
                return True
            else:
                logger.error(f"记忆存储失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"存储记忆时出错: {str(e)}")
            return False
