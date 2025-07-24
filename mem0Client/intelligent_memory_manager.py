"""
智能记忆管理器
负责AI记忆的智能检索、存储和管理
"""

import re
import json
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class IntelligentMemoryManager:
    """智能记忆管理器 - 实现AI驱动的记忆管理"""
    
    def __init__(self, mem0_api_url: str, user_id: str):
        self.mem0_api_url = mem0_api_url.rstrip('/')
        self.user_id = user_id
        
        # 记忆需求判断的关键词模式
        self.memory_trigger_patterns = {
            # 明确的记忆请求
            'explicit_memory_request': [
                r'记得|记住|回忆|想起|提到过|说过|之前|上次|以前',
                r'我的|我们的|我曾经|我之前|我上次',
                r'那个|那次|那时候|当时',
                r'历史|过去|以往|之前的'
            ],
            
            # 个人信息相关
            'personal_info': [
                r'我是|我叫|我的名字|我的工作|我的职业|我的爱好',
                r'我喜欢|我不喜欢|我的偏好|我的习惯',
                r'我住在|我来自|我的家|我的地址'
            ],
            
            # 项目和工作相关
            'project_work': [
                r'项目|工作|任务|计划|目标',
                r'进展|状态|完成|开始|结束',
                r'团队|同事|客户|合作'
            ],
            
            # 学习和技能相关
            'learning_skills': [
                r'学习|学会|掌握|了解|研究',
                r'技能|能力|知识|经验|专业',
                r'课程|培训|教程|文档'
            ],
            
            # 时间相关的查询
            'temporal_queries': [
                r'什么时候|何时|时间|日期|期限',
                r'今天|昨天|明天|这周|上周|下周',
                r'最近|近期|不久前|一段时间'
            ]
        }
        
        # 记忆存储价值判断标准
        self.storage_value_indicators = {
            'high_value': [
                r'重要|关键|核心|主要|必须',
                r'决定|确定|选择|计划|目标',
                r'问题|解决|方案|策略|方法',
                r'偏好|喜欢|不喜欢|习惯|风格',
                # 个人信息相关
                r'我是|我叫|名字|姓名|叫做',
                r'年龄|岁|多大|出生',
                r'职业|工作|从事|开发者|工程师|程序员',
                r'专业|学习|毕业|学校|大学',
                r'项目|开发|正在做|在做|负责',
                r'技术栈|使用|技术|语言|框架'
            ],

            'medium_value': [
                r'想法|观点|意见|建议|推荐',
                r'经验|教训|发现|学到|了解',
                r'信息|数据|资料|文档|链接',
                r'兴趣|爱好|喜好|感兴趣',
                r'背景|经历|经验|历史'
            ],

            'low_value': [
                r'你好|再见|谢谢|不客气|没关系',
                r'测试|试试|看看|随便|无所谓',
                r'天气|新闻|娱乐|闲聊|聊天'
            ]
        }

    def analyze_memory_need(self, user_input: str) -> Dict[str, any]:
        """
        分析用户输入是否需要检索历史记忆
        
        Args:
            user_input: 用户输入的文本
            
        Returns:
            Dict包含:
            - needs_memory: bool, 是否需要检索记忆
            - confidence: float, 判断的置信度 (0-1)
            - trigger_type: str, 触发类型
            - keywords: List[str], 关键词
        """
        
        user_input_lower = user_input.lower()
        
        # 检查各种触发模式
        trigger_scores = {}
        matched_keywords = []
        
        for category, patterns in self.memory_trigger_patterns.items():
            score = 0
            category_keywords = []
            
            for pattern in patterns:
                matches = re.findall(pattern, user_input_lower)
                if matches:
                    score += len(matches) * 0.2
                    category_keywords.extend(matches)
            
            if score > 0:
                trigger_scores[category] = min(score, 1.0)  # 限制最大值为1.0
                matched_keywords.extend(category_keywords)
        
        # 计算总体需要记忆的概率
        if not trigger_scores:
            needs_memory = False
            confidence = 0.0
            trigger_type = 'none'
        else:
            # 取最高分数作为主要触发类型
            trigger_type = max(trigger_scores.keys(), key=lambda k: trigger_scores[k])
            confidence = trigger_scores[trigger_type]
            
            # 如果置信度超过阈值，则认为需要记忆
            needs_memory = confidence >= 0.3
        
        return {
            'needs_memory': needs_memory,
            'confidence': confidence,
            'trigger_type': trigger_type,
            'keywords': list(set(matched_keywords)),
            'all_scores': trigger_scores
        }

    def analyze_storage_value(self, user_input: str, ai_response: str) -> Dict[str, any]:
        """
        分析对话内容是否值得存储为记忆
        
        Args:
            user_input: 用户输入
            ai_response: AI回复
            
        Returns:
            Dict包含:
            - should_store: bool, 是否应该存储
            - value_level: str, 价值等级 (high/medium/low)
            - confidence: float, 判断置信度
            - reasons: List[str], 存储理由
        """
        
        combined_text = f"{user_input} {ai_response}".lower()
        
        # 计算各价值等级的分数
        value_scores = {}
        matched_reasons = []
        
        for level, patterns in self.storage_value_indicators.items():
            score = 0
            level_reasons = []
            
            for pattern in patterns:
                matches = re.findall(pattern, combined_text)
                if matches:
                    score += len(matches) * 0.15
                    level_reasons.extend(matches)
            
            if score > 0:
                value_scores[level] = min(score, 1.0)
                matched_reasons.extend(level_reasons)
        
        # 判断是否应该存储
        if not value_scores:
            should_store = False
            value_level = 'none'
            confidence = 0.0
        else:
            # 确定价值等级
            if 'high_value' in value_scores and value_scores['high_value'] >= 0.3:
                value_level = 'high'
                confidence = value_scores['high_value']
                should_store = True
            elif 'medium_value' in value_scores and value_scores['medium_value'] >= 0.4:
                value_level = 'medium'
                confidence = value_scores['medium_value']
                should_store = True
            elif 'low_value' in value_scores:
                value_level = 'low'
                confidence = value_scores['low_value']
                should_store = False
            else:
                # 默认中等价值
                value_level = 'medium'
                confidence = max(value_scores.values()) if value_scores else 0.0
                should_store = confidence >= 0.3
        
        # 添加调试信息
        logger.info(f"存储价值分析 - 输入: {user_input[:100]}...")
        logger.info(f"存储价值分析 - 匹配分数: {value_scores}")
        logger.info(f"存储价值分析 - 是否存储: {should_store}, 价值等级: {value_level}, 置信度: {confidence}")

        return {
            'should_store': should_store,
            'value_level': value_level,
            'confidence': confidence,
            'reasons': list(set(matched_reasons)),
            'all_scores': value_scores
        }

    def extract_search_keywords(self, user_input: str) -> List[str]:
        """
        从用户输入中提取搜索关键词

        Args:
            user_input: 用户输入

        Returns:
            List[str]: 关键词列表
        """
        # 移除常见的停用词
        stop_words = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '们',
                     '这', '那', '有', '和', '与', '或', '但', '如果', '因为', '所以',
                     '什么', '怎么', '为什么', '哪里', '什么时候', '谁', '如何'}

        # 简单的关键词提取（可以后续用更高级的NLP技术替换）
        words = re.findall(r'\w+', user_input.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 1]

        return keywords[:10]  # 限制关键词数量

    async def search_relevant_memories(self, user_input: str, limit: int = 5) -> List[Dict]:
        """
        基于用户输入搜索相关记忆 - 增强版本

        Args:
            user_input: 用户输入
            limit: 返回记忆数量限制

        Returns:
            List[Dict]: 相关记忆列表，按相关度排序
        """
        try:
            # 提取关键词用于多重搜索
            keywords = self.extract_search_keywords(user_input)

            all_memories = []

            # 1. 主要搜索：使用完整用户输入
            main_memories = await self._search_memories_api(user_input, limit)
            all_memories.extend(main_memories)

            # 2. 关键词搜索：使用提取的关键词
            if keywords:
                keyword_query = ' '.join(keywords[:3])  # 使用前3个关键词
                keyword_memories = await self._search_memories_api(keyword_query, limit//2)
                all_memories.extend(keyword_memories)

            # 3. 去重并按相关度排序
            unique_memories = self._deduplicate_memories(all_memories)
            sorted_memories = sorted(unique_memories, key=lambda x: x.get('score', 0.0), reverse=True)

            return sorted_memories[:limit]

        except Exception as e:
            logger.error(f"搜索记忆时出错: {str(e)}")
            return []

    async def _search_memories_api(self, query: str, limit: int) -> List[Dict]:
        """
        调用mem0 API搜索记忆的内部方法

        Args:
            query: 搜索查询
            limit: 结果限制

        Returns:
            List[Dict]: 搜索结果
        """
        try:
            search_url = f"{self.mem0_api_url}/search"
            payload = {
                "query": query,
                "user_id": self.user_id,
                "limit": limit
            }

            response = requests.post(search_url, json=payload, timeout=10)

            if response.status_code == 200:
                search_results = response.json()

                memories = []
                if 'results' in search_results:
                    for result in search_results['results']:
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

    def _deduplicate_memories(self, memories: List[Dict]) -> List[Dict]:
        """
        去除重复的记忆

        Args:
            memories: 记忆列表

        Returns:
            List[Dict]: 去重后的记忆列表
        """
        seen_ids = set()
        unique_memories = []

        for memory in memories:
            memory_id = memory.get('id', '')
            if memory_id and memory_id not in seen_ids:
                seen_ids.add(memory_id)
                unique_memories.append(memory)

        return unique_memories

    def categorize_memories(self, memories: List[Dict]) -> Dict[str, List[Dict]]:
        """
        将记忆按类型分类

        Args:
            memories: 记忆列表

        Returns:
            Dict[str, List[Dict]]: 分类后的记忆
        """
        categories = {
            'personal_info': [],
            'preferences': [],
            'projects': [],
            'conversations': [],
            'other': []
        }

        for memory in memories:
            memory_text = memory.get('memory', '').lower()

            # 个人信息
            if any(keyword in memory_text for keyword in ['我是', '我叫', '我的名字', '我住在', '我来自']):
                categories['personal_info'].append(memory)
            # 偏好和习惯
            elif any(keyword in memory_text for keyword in ['喜欢', '不喜欢', '偏好', '习惯', '风格']):
                categories['preferences'].append(memory)
            # 项目和工作
            elif any(keyword in memory_text for keyword in ['项目', '工作', '任务', '计划', '目标']):
                categories['projects'].append(memory)
            # 对话记录
            elif '用户:' in memory_text and 'ai:' in memory_text:
                categories['conversations'].append(memory)
            else:
                categories['other'].append(memory)

        return categories

    def build_context_with_memories(self, user_input: str, memories: List[Dict],
                                   analysis_result: Dict = None) -> str:
        """
        将检索到的记忆智能整合到对话上下文中 - 增强版本

        Args:
            user_input: 用户输入
            memories: 相关记忆列表
            analysis_result: 记忆需求分析结果

        Returns:
            str: 整合了记忆的上下文
        """
        if not memories:
            return user_input

        # 按类型分类记忆
        categorized_memories = self.categorize_memories(memories)

        # 根据分析结果选择最相关的记忆
        relevant_memories = self._select_most_relevant_memories(
            categorized_memories, user_input, analysis_result
        )

        if not relevant_memories:
            return user_input

        # 构建智能上下文
        context_parts = []

        # 添加记忆上下文
        if relevant_memories:
            context_parts.append("=== 相关历史信息 ===")

            for i, memory in enumerate(relevant_memories[:3], 1):
                memory_text = memory.get('memory', '')
                score = memory.get('score', 0.0)
                created_at = memory.get('created_at', '')

                # 清理记忆文本（移除"用户:"和"AI:"前缀）
                clean_memory = self._clean_memory_text(memory_text)

                context_parts.append(f"{i}. {clean_memory}")
                if created_at:
                    context_parts.append(f"   (时间: {created_at[:10]}, 相关度: {score:.2f})")

        # 添加当前问题
        context_parts.append("\n=== 当前对话 ===")
        context_parts.append(f"用户问题: {user_input}")

        # 添加AI指令
        context_parts.append("\n=== AI指令 ===")
        context_parts.append(
            "请基于上述历史信息回答用户问题。要求：\n"
            "1. 如果历史信息与当前问题相关，请自然地引用这些信息\n"
            "2. 如果历史信息不够准确或过时，请询问用户确认\n"
            "3. 保持回复的自然性，不要生硬地列举历史信息\n"
            "4. 如果没有相关历史信息，请正常回答问题"
        )

        return "\n".join(context_parts)

    def _select_most_relevant_memories(self, categorized_memories: Dict[str, List[Dict]],
                                     user_input: str, analysis_result: Dict = None) -> List[Dict]:
        """
        选择最相关的记忆

        Args:
            categorized_memories: 分类后的记忆
            user_input: 用户输入
            analysis_result: 分析结果

        Returns:
            List[Dict]: 最相关的记忆列表
        """
        relevant_memories = []

        # 根据触发类型优先选择记忆
        if analysis_result:
            trigger_type = analysis_result.get('trigger_type', '')

            if trigger_type == 'personal_info':
                relevant_memories.extend(categorized_memories['personal_info'][:2])
                relevant_memories.extend(categorized_memories['preferences'][:1])
            elif trigger_type == 'project_work':
                relevant_memories.extend(categorized_memories['projects'][:2])
                relevant_memories.extend(categorized_memories['conversations'][:1])
            elif trigger_type == 'explicit_memory_request':
                # 明确的记忆请求，优先返回最相关的记忆
                all_memories = []
                for category_memories in categorized_memories.values():
                    all_memories.extend(category_memories)
                relevant_memories = sorted(all_memories, key=lambda x: x.get('score', 0.0), reverse=True)[:3]
            else:
                # 默认策略：混合选择
                relevant_memories.extend(categorized_memories['personal_info'][:1])
                relevant_memories.extend(categorized_memories['preferences'][:1])
                relevant_memories.extend(categorized_memories['projects'][:1])
        else:
            # 没有分析结果时的默认策略
            for category_memories in categorized_memories.values():
                if category_memories:
                    relevant_memories.extend(category_memories[:1])

        # 按相关度排序并限制数量
        relevant_memories = sorted(relevant_memories, key=lambda x: x.get('score', 0.0), reverse=True)
        return relevant_memories[:3]

    def _clean_memory_text(self, memory_text: str) -> str:
        """
        清理记忆文本，移除格式化标记

        Args:
            memory_text: 原始记忆文本

        Returns:
            str: 清理后的文本
        """
        # 移除"用户:"和"AI:"前缀
        cleaned = re.sub(r'^用户:\s*', '', memory_text, flags=re.MULTILINE)
        cleaned = re.sub(r'^AI:\s*', '', cleaned, flags=re.MULTILINE)

        # 移除多余的空行
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)

        # 限制长度
        if len(cleaned) > 200:
            cleaned = cleaned[:200] + "..."

        return cleaned.strip()

    def extract_key_information(self, user_input: str, ai_response: str) -> Dict[str, any]:
        """
        从对话中提取关键信息

        Args:
            user_input: 用户输入
            ai_response: AI回复

        Returns:
            Dict: 提取的关键信息
        """
        combined_text = f"{user_input} {ai_response}"

        # 提取个人信息
        personal_info = {}
        name_match = re.search(r'我(?:是|叫|的名字是)\s*([^\s，。！？]+)', combined_text)
        if name_match:
            personal_info['name'] = name_match.group(1)

        age_match = re.search(r'(?:我|今年)\s*(\d+)\s*(?:岁|年)', combined_text)
        if age_match:
            personal_info['age'] = age_match.group(1)

        job_match = re.search(r'我(?:是|的工作是|从事)\s*([^\s，。！？]+)', combined_text)
        if job_match:
            personal_info['job'] = job_match.group(1)

        # 提取偏好信息
        preferences = {}
        like_matches = re.findall(r'(?:我|用户)(?:喜欢|爱好|偏好)\s*([^\s，。！？]+)', combined_text)
        if like_matches:
            preferences['likes'] = like_matches

        dislike_matches = re.findall(r'(?:我|用户)(?:不喜欢|讨厌|不爱)\s*([^\s，。！？]+)', combined_text)
        if dislike_matches:
            preferences['dislikes'] = dislike_matches

        # 提取项目信息
        projects = {}
        project_matches = re.findall(r'(?:项目|工作|任务)\s*([^\s，。！？]+)', combined_text)
        if project_matches:
            projects['mentioned_projects'] = project_matches

        return {
            'personal_info': personal_info,
            'preferences': preferences,
            'projects': projects,
            'has_key_info': bool(personal_info or preferences or projects)
        }

    async def intelligent_store_memory(self, user_input: str, ai_response: str) -> Dict[str, any]:
        """
        智能判断并存储记忆

        Args:
            user_input: 用户输入
            ai_response: AI回复

        Returns:
            Dict: 存储结果和详情
        """
        # 分析存储价值
        storage_analysis = self.analyze_storage_value(user_input, ai_response)

        # 提取关键信息
        key_info = self.extract_key_information(user_input, ai_response)

        # 综合判断是否存储
        should_store = storage_analysis['should_store']

        # 如果包含关键信息，提高存储优先级
        if key_info['has_key_info']:
            should_store = True
            if storage_analysis['value_level'] == 'low':
                storage_analysis['value_level'] = 'medium'

        result = {
            'stored': False,
            'reason': '',
            'value_level': storage_analysis['value_level'],
            'confidence': storage_analysis['confidence'],
            'key_info': key_info
        }

        if should_store:
            # 构建优化的记忆内容
            memory_content = self._build_optimized_memory_content(
                user_input, ai_response, key_info
            )

            # 存储记忆
            success = await self.store_memory_async(
                memory_content,
                storage_analysis['value_level'],
                key_info
            )

            if success:
                result['stored'] = True
                result['reason'] = f"存储成功 - {storage_analysis['value_level']}级别记忆"
            else:
                result['reason'] = "存储失败 - API错误"
        else:
            result['reason'] = f"未存储 - 价值等级过低 (置信度: {storage_analysis['confidence']:.2f})"

        return result

    def _build_optimized_memory_content(self, user_input: str, ai_response: str,
                                      key_info: Dict) -> str:
        """
        构建优化的记忆内容

        Args:
            user_input: 用户输入
            ai_response: AI回复
            key_info: 关键信息

        Returns:
            str: 优化的记忆内容
        """
        # 基础对话内容
        base_content = f"用户: {user_input}\nAI: {ai_response}"

        # 如果有关键信息，添加结构化摘要
        if key_info['has_key_info']:
            summary_parts = []

            if key_info['personal_info']:
                personal = key_info['personal_info']
                summary_parts.append("个人信息:")
                for key, value in personal.items():
                    summary_parts.append(f"  {key}: {value}")

            if key_info['preferences']:
                prefs = key_info['preferences']
                summary_parts.append("偏好信息:")
                if 'likes' in prefs:
                    summary_parts.append(f"  喜欢: {', '.join(prefs['likes'])}")
                if 'dislikes' in prefs:
                    summary_parts.append(f"  不喜欢: {', '.join(prefs['dislikes'])}")

            if key_info['projects']:
                projects = key_info['projects']
                summary_parts.append("项目信息:")
                if 'mentioned_projects' in projects:
                    summary_parts.append(f"  提到的项目: {', '.join(projects['mentioned_projects'])}")

            if summary_parts:
                summary = "\n".join(summary_parts)
                return f"{base_content}\n\n关键信息摘要:\n{summary}"

        return base_content

    async def store_memory_async(self, memory_content: str, value_level: str = 'medium',
                                key_info: Dict = None) -> bool:
        """
        异步存储记忆到mem0 - 增强版本

        Args:
            memory_content: 记忆内容
            value_level: 记忆价值等级
            key_info: 关键信息

        Returns:
            bool: 存储是否成功
        """
        try:
            # 构建元数据
            metadata = {
                "value_level": value_level,
                "timestamp": datetime.now().isoformat(),
                "source": "intelligent_chat"
            }

            # 添加关键信息到元数据
            if key_info and key_info['has_key_info']:
                metadata.update({
                    "has_personal_info": bool(key_info['personal_info']),
                    "has_preferences": bool(key_info['preferences']),
                    "has_projects": bool(key_info['projects'])
                })

            # 调用mem0 API存储记忆
            add_url = f"{self.mem0_api_url}/memories"
            payload = {
                "messages": [{"role": "user", "content": memory_content}],
                "user_id": self.user_id,
                "metadata": metadata
            }

            response = requests.post(add_url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"记忆存储成功: {value_level} 级别")
                return True
            else:
                logger.error(f"记忆存储失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"存储记忆时出错: {str(e)}")
            return False

    # 同步版本的方法，用于Streamlit
    def search_relevant_memories_sync(self, user_input: str, limit: int = 5) -> List[Dict]:
        """
        同步版本的记忆搜索
        """
        try:
            # 提取关键词用于多重搜索
            keywords = self.extract_search_keywords(user_input)

            all_memories = []

            # 1. 主要搜索：使用完整用户输入
            main_memories = self._search_memories_api_sync(user_input, limit)
            all_memories.extend(main_memories)

            # 2. 关键词搜索：使用提取的关键词
            if keywords:
                keyword_query = ' '.join(keywords[:3])  # 使用前3个关键词
                keyword_memories = self._search_memories_api_sync(keyword_query, limit//2)
                all_memories.extend(keyword_memories)

            # 3. 去重并按相关度排序
            unique_memories = self._deduplicate_memories(all_memories)
            sorted_memories = sorted(unique_memories, key=lambda x: x.get('score', 0.0), reverse=True)

            return sorted_memories[:limit]

        except Exception as e:
            logger.error(f"搜索记忆时出错: {str(e)}")
            return []

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

            response = requests.post(search_url, json=payload, timeout=10)

            if response.status_code == 200:
                search_results = response.json()

                memories = []
                if 'results' in search_results:
                    for result in search_results['results']:
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

    def intelligent_store_memory_sync(self, user_input: str, ai_response: str) -> Dict[str, any]:
        """
        同步版本的智能记忆存储
        """
        # 分析存储价值
        storage_analysis = self.analyze_storage_value(user_input, ai_response)

        # 提取关键信息
        key_info = self.extract_key_information(user_input, ai_response)

        # 综合判断是否存储
        should_store = storage_analysis['should_store']

        # 如果包含关键信息，提高存储优先级
        if key_info['has_key_info']:
            should_store = True
            if storage_analysis['value_level'] == 'low':
                storage_analysis['value_level'] = 'medium'

        result = {
            'stored': False,
            'reason': '',
            'value_level': storage_analysis['value_level'],
            'confidence': storage_analysis['confidence'],
            'key_info': key_info
        }

        if should_store:
            # 构建优化的记忆内容
            memory_content = self._build_optimized_memory_content(
                user_input, ai_response, key_info
            )

            # 存储记忆（同步版本）
            success = self.store_memory_sync(
                memory_content,
                storage_analysis['value_level'],
                key_info
            )

            if success:
                result['stored'] = True
                result['reason'] = f"存储成功 - {storage_analysis['value_level']}级别记忆"
            else:
                result['reason'] = "存储失败 - API错误"
        else:
            result['reason'] = f"未存储 - 价值等级过低 (置信度: {storage_analysis['confidence']:.2f})"

        return result

    def store_memory_sync(self, memory_content: str, value_level: str = 'medium',
                         key_info: Dict = None) -> bool:
        """
        同步版本的记忆存储
        """
        try:
            # 构建元数据
            metadata = {
                "value_level": value_level,
                "timestamp": datetime.now().isoformat(),
                "source": "intelligent_chat"
            }

            # 添加关键信息到元数据
            if key_info and key_info['has_key_info']:
                metadata.update({
                    "has_personal_info": bool(key_info['personal_info']),
                    "has_preferences": bool(key_info['preferences']),
                    "has_projects": bool(key_info['projects'])
                })

            # 调用mem0 API存储记忆
            add_url = f"{self.mem0_api_url}/memories"
            payload = {
                "messages": [{"role": "user", "content": memory_content}],
                "user_id": self.user_id,
                "metadata": metadata
            }

            response = requests.post(add_url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"记忆存储成功: {value_level} 级别")
                return True
            else:
                logger.error(f"记忆存储失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"存储记忆时出错: {str(e)}")
            return False
