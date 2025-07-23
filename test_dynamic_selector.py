#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
动态模型选择器测试脚本
"""

import os
import sys
sys.path.append('mem0Client')

from mem0Client.dynamic_model_selector import DynamicModelSelector

def test_dynamic_selector():
    """测试动态模型选择器"""
    
    print("🧪 测试动态模型选择器")
    print("=" * 50)
    
    # 初始化选择器 - 连接到Gemini Balance
    selector = DynamicModelSelector(
        api_base_url='http://localhost:8000',
        api_key='q1q2q3q4'
    )
    
    # 测试获取可用模型
    print("\n📋 可用模型列表:")
    models = selector.get_available_models()
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    
    print(f"\n⚡ 快速决策模型: {selector.fast_model}")
    
    # 测试不同类型的问题
    test_cases = [
        {
            "query": "你好，今天天气怎么样？",
            "has_image": False,
            "description": "简单问候"
        },
        {
            "query": "请帮我分析这个Python代码的时间复杂度，并提供优化建议",
            "has_image": False,
            "description": "复杂技术问题"
        },
        {
            "query": "请分析这张图片中的内容",
            "has_image": True,
            "description": "图片分析任务"
        },
        {
            "query": "帮我写一个创意的营销方案",
            "has_image": False,
            "description": "创意任务"
        }
    ]
    
    print("\n🎯 测试不同类型问题的模型选择:")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   问题: {test_case['query']}")
        print(f"   包含图片: {test_case['has_image']}")
        
        try:
            result = selector.select_optimal_model(
                user_query=test_case['query'],
                has_image=test_case['has_image']
            )
            
            print(f"   推荐模型: {result.get('recommended_model', '未知')}")
            print(f"   推荐理由: {result.get('reasoning', '无')}")
            print(f"   任务类型: {result.get('task_type', '未知')}")
            print(f"   复杂度: {result.get('complexity_level', '未知')}")
            
        except Exception as e:
            print(f"   ❌ 选择失败: {e}")

if __name__ == "__main__":
    test_dynamic_selector()
