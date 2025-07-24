"""
智能记忆功能测试用例
用于验证AI记忆检索、存储和整合功能的准确性
"""

class MemoryTestCases:
    """智能记忆功能测试用例集合"""
    
    @staticmethod
    def get_all_test_cases():
        """获取所有测试用例"""
        return {
            "personal_info_tests": MemoryTestCases.get_personal_info_tests(),
            "preference_tests": MemoryTestCases.get_preference_tests(),
            "project_tests": MemoryTestCases.get_project_tests(),
            "memory_retrieval_tests": MemoryTestCases.get_memory_retrieval_tests(),
            "context_integration_tests": MemoryTestCases.get_context_integration_tests(),
            "storage_decision_tests": MemoryTestCases.get_storage_decision_tests()
        }
    
    @staticmethod
    def get_personal_info_tests():
        """个人信息相关测试用例"""
        return [
            {
                "name": "基础个人信息存储",
                "conversation": [
                    {"user": "你好，我是刘昶，今年38岁", "expected_memory": True, "memory_type": "personal_info"},
                    {"user": "我是一名软件工程师", "expected_memory": True, "memory_type": "personal_info"}
                ],
                "validation": {
                    "should_extract_name": "刘昶",
                    "should_extract_age": "38",
                    "should_extract_job": "软件工程师"
                }
            },
            {
                "name": "个人信息检索",
                "setup_memories": ["我是刘昶，今年38岁，是一名软件工程师"],
                "conversation": [
                    {"user": "我的名字是什么？", "expected_memory_retrieval": True},
                    {"user": "我多大了？", "expected_memory_retrieval": True},
                    {"user": "我的工作是什么？", "expected_memory_retrieval": True}
                ],
                "validation": {
                    "should_mention_name": True,
                    "should_mention_age": True,
                    "should_mention_job": True
                }
            }
        ]
    
    @staticmethod
    def get_preference_tests():
        """偏好信息相关测试用例"""
        return [
            {
                "name": "偏好信息存储",
                "conversation": [
                    {"user": "我喜欢Python编程", "expected_memory": True, "memory_type": "preferences"},
                    {"user": "我不喜欢Java", "expected_memory": True, "memory_type": "preferences"},
                    {"user": "我偏好使用VS Code编辑器", "expected_memory": True, "memory_type": "preferences"}
                ],
                "validation": {
                    "should_extract_likes": ["Python编程"],
                    "should_extract_dislikes": ["Java"],
                    "should_extract_preferences": ["VS Code编辑器"]
                }
            },
            {
                "name": "偏好信息检索和应用",
                "setup_memories": ["用户喜欢Python编程，不喜欢Java，偏好使用VS Code编辑器"],
                "conversation": [
                    {"user": "推荐一个编程语言给我", "expected_memory_retrieval": True},
                    {"user": "什么编辑器比较好？", "expected_memory_retrieval": True}
                ],
                "validation": {
                    "should_recommend_python": True,
                    "should_avoid_java": True,
                    "should_recommend_vscode": True
                }
            }
        ]
    
    @staticmethod
    def get_project_tests():
        """项目相关测试用例"""
        return [
            {
                "name": "项目信息存储",
                "conversation": [
                    {"user": "我正在开发一个AI聊天机器人项目", "expected_memory": True, "memory_type": "projects"},
                    {"user": "这个项目使用Python和Streamlit", "expected_memory": True, "memory_type": "projects"},
                    {"user": "项目的目标是实现智能记忆功能", "expected_memory": True, "memory_type": "projects"}
                ],
                "validation": {
                    "should_extract_project": "AI聊天机器人",
                    "should_extract_tech": ["Python", "Streamlit"],
                    "should_extract_goal": "智能记忆功能"
                }
            },
            {
                "name": "项目进展跟踪",
                "setup_memories": ["用户正在开发AI聊天机器人项目，使用Python和Streamlit，目标是实现智能记忆功能"],
                "conversation": [
                    {"user": "我的项目进展如何？", "expected_memory_retrieval": True},
                    {"user": "项目还需要什么功能？", "expected_memory_retrieval": True}
                ],
                "validation": {
                    "should_mention_project": True,
                    "should_mention_tech": True,
                    "should_mention_goal": True
                }
            }
        ]
    
    @staticmethod
    def get_memory_retrieval_tests():
        """记忆检索功能测试"""
        return [
            {
                "name": "明确记忆请求",
                "setup_memories": ["用户昨天讨论了机器学习算法", "用户提到喜欢深度学习"],
                "conversation": [
                    {"user": "我们昨天讨论了什么？", "expected_memory_retrieval": True, "confidence_threshold": 0.8},
                    {"user": "我之前提到过什么偏好？", "expected_memory_retrieval": True, "confidence_threshold": 0.7},
                    {"user": "回忆一下我们的对话", "expected_memory_retrieval": True, "confidence_threshold": 0.9}
                ]
            },
            {
                "name": "隐式记忆需求",
                "setup_memories": ["用户是Python开发者", "用户正在学习机器学习"],
                "conversation": [
                    {"user": "推荐一些学习资源", "expected_memory_retrieval": True, "confidence_threshold": 0.5},
                    {"user": "有什么好的项目想法？", "expected_memory_retrieval": True, "confidence_threshold": 0.4}
                ]
            },
            {
                "name": "无关记忆过滤",
                "setup_memories": ["用户喜欢咖啡", "用户住在北京"],
                "conversation": [
                    {"user": "今天天气怎么样？", "expected_memory_retrieval": False},
                    {"user": "1+1等于几？", "expected_memory_retrieval": False}
                ]
            }
        ]
    
    @staticmethod
    def get_context_integration_tests():
        """上下文整合功能测试"""
        return [
            {
                "name": "记忆上下文整合",
                "setup_memories": [
                    "用户是刘昶，38岁软件工程师",
                    "用户喜欢Python，正在开发AI项目"
                ],
                "conversation": [
                    {"user": "给我一些职业建议", "expected_memory_retrieval": True}
                ],
                "validation": {
                    "should_use_name": True,
                    "should_use_age": True,
                    "should_use_profession": True,
                    "should_use_preferences": True,
                    "context_quality": "high"
                }
            },
            {
                "name": "记忆冲突处理",
                "setup_memories": [
                    "用户说他25岁（2023年）",
                    "用户说他26岁（2024年）"
                ],
                "conversation": [
                    {"user": "我多大了？", "expected_memory_retrieval": True}
                ],
                "validation": {
                    "should_handle_conflict": True,
                    "should_ask_confirmation": True
                }
            }
        ]
    
    @staticmethod
    def get_storage_decision_tests():
        """存储决策功能测试"""
        return [
            {
                "name": "高价值信息存储",
                "conversation": [
                    {"user": "我的目标是成为AI专家", "expected_storage": True, "expected_value": "high"},
                    {"user": "我决定学习深度学习", "expected_storage": True, "expected_value": "high"},
                    {"user": "这个项目对我很重要", "expected_storage": True, "expected_value": "medium"}
                ]
            },
            {
                "name": "中等价值信息存储",
                "conversation": [
                    {"user": "我觉得这个想法不错", "expected_storage": True, "expected_value": "medium"},
                    {"user": "我了解了一些新知识", "expected_storage": True, "expected_value": "medium"},
                    {"user": "这个经验很有用", "expected_storage": True, "expected_value": "medium"}
                ]
            },
            {
                "name": "低价值信息过滤",
                "conversation": [
                    {"user": "你好", "expected_storage": False, "expected_value": "low"},
                    {"user": "谢谢", "expected_storage": False, "expected_value": "low"},
                    {"user": "今天天气不错", "expected_storage": False, "expected_value": "low"},
                    {"user": "随便聊聊", "expected_storage": False, "expected_value": "low"}
                ]
            },
            {
                "name": "关键信息强制存储",
                "conversation": [
                    {"user": "我叫张三", "expected_storage": True, "expected_value": "high", "reason": "personal_info"},
                    {"user": "我的邮箱是zhang@example.com", "expected_storage": True, "expected_value": "high", "reason": "contact_info"},
                    {"user": "我的生日是1990年1月1日", "expected_storage": True, "expected_value": "high", "reason": "personal_info"}
                ]
            }
        ]
    
    @staticmethod
    def get_integration_test_scenarios():
        """集成测试场景"""
        return [
            {
                "name": "完整对话流程测试",
                "description": "模拟真实用户对话，测试完整的记忆功能",
                "conversation_flow": [
                    {"user": "你好，我是新用户", "step": "初始接触"},
                    {"user": "我叫李明，是一名数据科学家", "step": "个人信息建立"},
                    {"user": "我正在学习深度学习", "step": "兴趣和目标"},
                    {"user": "我喜欢用Python和TensorFlow", "step": "技术偏好"},
                    {"user": "我的项目是预测股价", "step": "项目信息"},
                    {"user": "我们上次聊了什么？", "step": "记忆检索测试"},
                    {"user": "给我一些学习建议", "step": "个性化建议"},
                    {"user": "我的项目进展如何？", "step": "项目跟踪"}
                ],
                "expected_outcomes": {
                    "memories_created": 5,
                    "successful_retrievals": 3,
                    "personalized_responses": 2
                }
            }
        ]
