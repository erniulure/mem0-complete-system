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
        self.api_base_url = api_base_url or 'http://gemini-balance:8000'
        self.api_key = api_key or 'admin123'
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
        """使用基础模型简单判断用哪个模型更合适"""

        # 简化的决策提示 - 直接问AI选择
        decision_prompt = f"""
用户问题："{user_query}"
是否包含图片：{"是" if has_image else "否"}

请判断这个问题用gemini-2.5-flash还是gemini-2.5-pro回答更好？

选择标准：
- gemini-2.5-flash：适合日常对话、简单问题、快速回复
- gemini-2.5-pro：适合复杂分析、技术问题、深度推理、代码相关

请只回答模型名称，格式如下：
{{
    "recommended_model": "gemini-2.5-flash" 或 "gemini-2.5-pro",
    "reasoning": "选择理由"
}}

只返回JSON，不要其他内容！
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
        """简化的备用推荐逻辑"""
        # 如果有图片，优先使用pro模型
        if has_image:
            return {
                "recommended_model": "gemini-2.5-pro",
                "reasoning": "图片任务使用pro模型确保最佳效果"
            }

        # 默认使用flash模型
        return {
            "recommended_model": "gemini-2.5-flash",
            "reasoning": "默认使用flash模型平衡质量和速度"
        }
    
    def select_optimal_model(self, user_query: str, has_image: bool = False) -> Dict:
        """选择最优模型的主要方法"""

        logging.info(f"开始模型选择 - 问题: '{user_query[:50]}...', 包含图片: {has_image}")

        try:
            # 1. 使用快速模型获取推荐
            recommendation = self._ask_fast_model_for_recommendation(user_query, has_image)
            logging.info(f"AI推荐结果: {recommendation}")

            # 2. 验证推荐的模型是否可用
            recommended_model = recommendation.get('recommended_model')
            if not any(model['id'] == recommended_model for model in self.available_models):
                logging.warning(f"推荐的模型 {recommended_model} 不可用，使用备用逻辑")
                recommendation = self._fallback_recommendation(user_query, has_image)
                recommendation["selection_method"] = "fallback_logic"
            else:
                recommendation["selection_method"] = "ai_recommendation"

            # 3. 添加额外信息
            recommendation.update({
                "available_models": [model['id'] for model in self.available_models],
                "fast_model_used": self.fast_model
            })

            # 确保字段名一致性
            if "recommended_model" in recommendation and "selected_model" not in recommendation:
                recommendation["selected_model"] = recommendation["recommended_model"]
            elif "selected_model" in recommendation and "recommended_model" not in recommendation:
                recommendation["recommended_model"] = recommendation["selected_model"]

            logging.info(f"最终选择模型: {recommendation.get('selected_model')}, 理由: {recommendation.get('reasoning')}")
            return recommendation

        except Exception as e:
            logging.error(f"模型选择失败: {e}, 使用备用逻辑")
            recommendation = self._fallback_recommendation(user_query, has_image)
            recommendation.update({
                "selection_method": "error_fallback",
                "error": str(e),
                "selected_model": recommendation["recommended_model"]
            })
            return recommendation
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [model['id'] for model in self.available_models]
    
    def refresh_models(self):
        """刷新模型列表"""
        self._fetch_available_models()
        self._identify_fast_model()
