#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
动态智能模型选择器
通过API获取可用模型，使用快速模型进行决策，然后用最优模型执行
"""

import requests
import json
import os
from typing import Dict, List, Optional, Tuple
import logging

class DynamicModelSelector:
    """动态智能模型选择器"""
    
    def __init__(self, api_base_url: str = None, api_key: str = None):
        # 使用Gemini Balance服务
        self.api_base_url = api_base_url or 'http://localhost:8000'
        self.api_key = api_key or 'q1q2q3q4'
        self.available_models = []
        self.fast_model = None
        self.model_capabilities = {}

        logging.info(f"连接到Gemini Balance: {self.api_base_url}")

        # 初始化
        self._fetch_available_models()
        self._identify_fast_model()
    
    def _fetch_available_models(self) -> List[Dict]:
        """从API获取可用模型列表"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_base_url}/v1/models"
            logging.info(f"请求URL: {url}")
            logging.info(f"请求头: {headers}")

            response = requests.get(url, headers=headers, timeout=10)

            logging.info(f"响应状态码: {response.status_code}")
            logging.info(f"响应内容: {response.text[:200]}...")

            if response.status_code == 200:
                data = response.json()
                self.available_models = data.get('data', [])
                logging.info(f"获取到 {len(self.available_models)} 个可用模型")
                return self.available_models
            else:
                logging.warning(f"获取模型列表失败: {response.status_code} - {response.text}")
                # 使用默认模型列表
                self._use_default_models()
                
        except Exception as e:
            logging.error(f"获取模型列表异常: {e}")
            self._use_default_models()
        
        return self.available_models
    
    def _use_default_models(self):
        """使用默认模型列表作为备用"""
        # 使用Gemini Balance的主流模型（按推荐优先级排序）
        self.available_models = [
            {"id": "gemini-2.5-flash", "object": "model"},    # 主流平衡模型
            {"id": "gemini-2.5-pro", "object": "model"},      # 主流高质量模型
            {"id": "gemini-2.0-flash", "object": "model"},    # 快速模型
            {"id": "gemini-1.5-flash", "object": "model"},    # 备用快速模型
            {"id": "gemini-1.5-pro", "object": "model"}       # 备用高质量模型
        ]
        logging.info("使用默认Gemini主流模型列表")
    
    def _identify_fast_model(self):
        """识别最快的模型用于决策"""
        if not self.available_models:
            return
        
        # 定义快速模型的优先级（优先使用主流模型）
        fast_model_priorities = [
            "gemini-2.5-flash",           # 最新主流快速模型
            "gemini-2.0-flash",           # 次选快速模型
            "gemini-1.5-flash",           # 备用快速模型
            "gemini-1.5-flash-8b",        # 轻量级模型
            "gpt-4o-mini",
            "gpt-3.5-turbo"
        ]
        
        # 查找可用的最快模型
        for fast_model in fast_model_priorities:
            if any(model['id'] == fast_model for model in self.available_models):
                self.fast_model = fast_model
                break
        
        # 如果没找到，使用第一个可用模型
        if not self.fast_model and self.available_models:
            self.fast_model = self.available_models[0]['id']
        
        logging.info(f"选择快速决策模型: {self.fast_model}")
    
    def _ask_fast_model_for_recommendation(self, user_query: str, has_image: bool = False) -> Dict:
        """使用快速模型分析问题并推荐最适合的模型"""
        
        # 构建模型列表字符串
        model_list = "\n".join([f"- {model['id']}" for model in self.available_models])
        
        # 构建决策提示
        decision_prompt = f"""
你是一个AI模型选择专家。请分析用户的问题，从以下可用模型中推荐最适合的模型：

可用模型：
{model_list}

用户问题："{user_query}"
是否包含图片：{"是" if has_image else "否"}

模型选择优先级指南：
1. **主流首选**: gemini-2.5-flash (平衡), gemini-2.5-pro (高质量)
2. **快速选择**: gemini-2.0-flash (速度优先)
3. **备用选择**: gemini-1.5系列

推荐规则：
- 简单对话 → gemini-2.5-flash
- 复杂推理/技术问题 → gemini-2.5-pro
- 图片分析 → gemini-2.5-pro 或 gemini-2.5-flash
- 创意任务 → gemini-2.5-flash 或 gemini-2.5-pro
- 速度要求高 → gemini-2.0-flash

请严格按照以下JSON格式回答，不要添加任何其他文字：
{{
    "recommended_model": "推荐的模型ID",
    "reasoning": "推荐理由",
    "task_type": "任务类型",
    "complexity_level": "复杂度等级(1-10)",
    "alternative_model": "备选模型ID"
}}

重要：只返回JSON，不要有任何解释或其他内容！
"""
        
        try:
            # 调用快速模型
            response = self._call_model(self.fast_model, decision_prompt)
            
            # 解析JSON响应
            try:
                recommendation = json.loads(response)
                return recommendation
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试提取模型名称
                return self._extract_model_from_text(response)
                
        except Exception as e:
            logging.error(f"快速模型决策失败: {e}")
            return self._fallback_recommendation(user_query, has_image)
    
    def _call_model(self, model_id: str, prompt: str) -> str:
        """调用指定模型"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        response = requests.post(
            f"{self.api_base_url}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"API调用失败: {response.status_code}")
    
    def _extract_model_from_text(self, text: str) -> Dict:
        """从文本中提取模型推荐"""
        # 简单的文本解析逻辑
        available_model_ids = [model['id'] for model in self.available_models]
        
        for model_id in available_model_ids:
            if model_id in text:
                return {
                    "recommended_model": model_id,
                    "reasoning": "从文本中提取的推荐",
                    "task_type": "未知",
                    "complexity_level": "5"
                }
        
        # 如果没找到，返回默认推荐
        return self._fallback_recommendation("", False)
    
    def _fallback_recommendation(self, user_query: str, has_image: bool) -> Dict:
        """备用推荐逻辑"""
        if not self.available_models:
            return {
                "recommended_model": "gpt-4o-mini",
                "reasoning": "默认推荐",
                "task_type": "未知",
                "complexity_level": "5"
            }
        
        # 简单的规则推荐
        if has_image:
            # 优先选择支持多模态的主流模型
            multimodal_models = [
                "gemini-2.5-pro",           # 最佳多模态质量
                "gemini-2.5-flash",         # 主流多模态平衡
                "gemini-2.0-flash-exp",     # 实验性多模态
                "gemini-1.5-pro"            # 备用多模态
            ]
            for model in multimodal_models:
                if any(m['id'] == model for m in self.available_models):
                    return {
                        "recommended_model": model,
                        "reasoning": "图片任务需要多模态能力，选择主流模型确保最佳效果",
                        "task_type": "图片分析",
                        "complexity_level": "7"
                    }
        
        # 检查是否是复杂任务
        complex_keywords = ["分析", "解释", "代码", "算法", "架构", "设计", "优化", "调试"]
        if any(keyword in user_query for keyword in complex_keywords):
            # 选择高质量主流模型
            quality_models = [
                "gemini-2.5-pro",           # 主流最佳质量
                "gemini-2.0-pro-exp",       # 实验性高质量
                "gemini-1.5-pro"            # 备用高质量
            ]
            for model in quality_models:
                if any(m['id'] == model for m in self.available_models):
                    return {
                        "recommended_model": model,
                        "reasoning": "复杂任务需要高质量模型，选择主流2.5-pro确保最佳推理能力",
                        "task_type": "复杂推理",
                        "complexity_level": "8"
                    }
        
        # 默认选择主流平衡模型
        balanced_models = [
            "gemini-2.5-flash",         # 主流首选：最佳平衡
            "gemini-2.0-flash",         # 次选：速度优先
            "gemini-1.5-flash"          # 备用：兼容性好
        ]
        for model in balanced_models:
            if any(m['id'] == model for m in self.available_models):
                return {
                    "recommended_model": model,
                    "reasoning": "选择主流2.5-flash模型，平衡质量和速度，适合日常对话",
                    "task_type": "一般对话",
                    "complexity_level": "5"
                }
        
        # 最后选择第一个可用模型
        return {
            "recommended_model": self.available_models[0]['id'],
            "reasoning": "使用第一个可用模型",
            "task_type": "未知",
            "complexity_level": "5"
        }
    
    def select_optimal_model(self, user_query: str, has_image: bool = False) -> Dict:
        """选择最优模型的主要方法"""
        
        # 1. 使用快速模型获取推荐
        recommendation = self._ask_fast_model_for_recommendation(user_query, has_image)
        
        # 2. 验证推荐的模型是否可用
        recommended_model = recommendation.get('recommended_model')
        if not any(model['id'] == recommended_model for model in self.available_models):
            # 如果推荐的模型不可用，使用备用推荐
            recommendation = self._fallback_recommendation(user_query, has_image)
        
        # 3. 添加额外信息
        recommendation.update({
            "available_models": [model['id'] for model in self.available_models],
            "fast_model_used": self.fast_model,
            "selection_method": "dynamic_ai_recommendation"
        })
        
        return recommendation
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [model['id'] for model in self.available_models]
    
    def refresh_models(self):
        """刷新模型列表"""
        self._fetch_available_models()
        self._identify_fast_model()
