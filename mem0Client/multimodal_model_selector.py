"""
智能多模态模型选择器
根据内容类型、复杂度和用户偏好自动选择最适合的Gemini模型
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import base64
import io
from PIL import Image

class IntelligentModelSelector:
    """智能模型选择器"""
    
    def __init__(self):
        self.model_costs = {
            "gemini-2.0-flash": 1,
            "gemini-2.5-flash": 2, 
            "gemini-2.5-pro": 5
        }
        
        self.model_capabilities = {
            "gemini-2.0-flash": {
                "speed": 10, "cost": 10, "quality": 6, 
                "multimodal": 8, "reasoning": 6
            },
            "gemini-2.5-flash": {
                "speed": 7, "cost": 7, "quality": 8,
                "multimodal": 9, "reasoning": 8
            },
            "gemini-2.5-pro": {
                "speed": 4, "cost": 3, "quality": 10,
                "multimodal": 10, "reasoning": 10
            }
        }
        
        # 任务类型映射
        self.task_patterns = {
            "simple_chat": [
                r"你好|hello|hi|谢谢|thank",
                r"简单|basic|quick|fast"
            ],
            "image_analysis": [
                r"图片|图像|照片|image|photo|picture",
                r"看|识别|分析|describe|analyze|what.*see"
            ],
            "complex_reasoning": [
                r"分析|解释|为什么|原因|深入|analyze|explain|why|reason",
                r"比较|对比|区别|优缺点|compare|contrast|difference",
                r"解决|修复|调试|优化|solve|fix|debug|optimize"
            ],
            "creative_tasks": [
                r"创建|生成|写|设计|开发|create|generate|write|design",
                r"创意|创新|想法|creative|innovative|idea"
            ],
            "technical_tasks": [
                r"代码|编程|算法|架构|api|code|programming|algorithm|architecture",
                r"数据库|框架|系统|database|framework|system"
            ]
        }
    
    def analyze_content_complexity(self, content: str, has_image: bool = False) -> Dict:
        """分析内容复杂度"""
        
        # 基础复杂度指标
        length = len(content)
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?。！？]', content))
        
        # 技术关键词检测
        technical_keywords = [
            'api', 'algorithm', 'architecture', 'database', 'framework',
            'python', 'javascript', 'react', 'vue', 'angular', 'node',
            '算法', '架构', '数据库', '框架', '编程', '代码'
        ]
        tech_score = sum(1 for keyword in technical_keywords 
                        if keyword.lower() in content.lower())
        
        # 复杂句式检测
        complex_patterns = [
            r'因为.*所以', r'不仅.*而且', r'虽然.*但是', r'如果.*那么',
            r'because.*therefore', r'not only.*but also', r'although.*however'
        ]
        complexity_score = sum(1 for pattern in complex_patterns 
                             if re.search(pattern, content, re.IGNORECASE))
        
        # 问题类型检测
        question_patterns = [
            r'为什么|why', r'怎么样|how', r'什么时候|when', 
            r'在哪里|where', r'是什么|what'
        ]
        question_score = sum(1 for pattern in question_patterns 
                           if re.search(pattern, content, re.IGNORECASE))
        
        # 计算总复杂度
        total_complexity = (
            (length > 500) * 2 +           # 长文本
            (word_count > 100) * 2 +       # 词汇量
            (sentence_count > 5) * 1 +     # 句子数量
            tech_score * 3 +               # 技术内容
            complexity_score * 2 +         # 句式复杂度
            question_score * 1 +           # 问题复杂度
            (has_image) * 3                # 包含图片
        )
        
        return {
            "total_score": total_complexity,
            "length": length,
            "word_count": word_count,
            "tech_score": tech_score,
            "complexity_score": complexity_score,
            "question_score": question_score,
            "has_image": has_image
        }
    
    def detect_task_type(self, content: str, has_image: bool = False) -> str:
        """检测任务类型"""
        
        if has_image:
            return "image_analysis"
        
        content_lower = content.lower()
        
        # 检测各种任务类型
        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return task_type
        
        return "simple_chat"  # 默认
    
    def select_model_by_task(self, task_type: str, complexity: Dict) -> str:
        """根据任务类型和复杂度选择模型"""
        
        total_complexity = complexity["total_score"]
        has_image = complexity["has_image"]
        
        # 图片任务优先使用高级模型
        if has_image or task_type == "image_analysis":
            if total_complexity >= 8:
                return "gemini-2.5-pro"
            else:
                return "gemini-2.5-flash"
        
        # 复杂推理任务
        if task_type == "complex_reasoning":
            if total_complexity >= 10:
                return "gemini-2.5-pro"
            else:
                return "gemini-2.5-flash"
        
        # 技术任务
        if task_type == "technical_tasks":
            if total_complexity >= 8:
                return "gemini-2.5-pro"
            elif total_complexity >= 5:
                return "gemini-2.5-flash"
            else:
                return "gemini-2.0-flash"
        
        # 创意任务
        if task_type == "creative_tasks":
            if total_complexity >= 6:
                return "gemini-2.5-flash"
            else:
                return "gemini-2.0-flash"
        
        # 简单对话
        return "gemini-2.0-flash"
    
    def apply_user_preferences(self, base_model: str, preferences: Dict) -> str:
        """应用用户偏好调整模型选择"""
        
        if preferences.get("always_use_pro"):
            return "gemini-2.5-pro"
        
        if preferences.get("always_use_flash"):
            return "gemini-2.0-flash"
        
        if preferences.get("prefer_speed"):
            # 偏好速度，降级模型
            if base_model == "gemini-2.5-pro":
                return "gemini-2.5-flash"
            elif base_model == "gemini-2.5-flash":
                return "gemini-2.0-flash"
        
        if preferences.get("prefer_quality"):
            # 偏好质量，升级模型
            if base_model == "gemini-2.0-flash":
                return "gemini-2.5-flash"
            elif base_model == "gemini-2.5-flash":
                return "gemini-2.5-pro"
        
        if preferences.get("cost_sensitive"):
            # 成本敏感，降级模型
            if base_model == "gemini-2.5-pro":
                return "gemini-2.5-flash"
            elif base_model == "gemini-2.5-flash":
                return "gemini-2.0-flash"
        
        return base_model
    
    def select_optimal_model(self, 
                           content: str,
                           has_image: bool = False,
                           user_preferences: Dict = None,
                           system_constraints: Dict = None) -> Dict:
        """综合选择最优模型"""
        
        # 1. 分析内容复杂度
        complexity = self.analyze_content_complexity(content, has_image)
        
        # 2. 检测任务类型
        task_type = self.detect_task_type(content, has_image)
        
        # 3. 基础模型选择
        base_model = self.select_model_by_task(task_type, complexity)
        
        # 4. 应用用户偏好
        if user_preferences:
            selected_model = self.apply_user_preferences(base_model, user_preferences)
        else:
            selected_model = base_model
        
        # 5. 应用系统约束
        if system_constraints:
            if system_constraints.get("high_load"):
                selected_model = "gemini-2.0-flash"
            elif system_constraints.get("low_latency_required"):
                if selected_model == "gemini-2.5-pro":
                    selected_model = "gemini-2.5-flash"
        
        # 6. 生成选择理由
        reasoning = self._generate_reasoning(
            task_type, complexity, base_model, selected_model, has_image
        )
        
        return {
            "selected_model": selected_model,
            "base_model": base_model,
            "task_type": task_type,
            "complexity": complexity,
            "reasoning": reasoning,
            "estimated_cost": self.model_costs[selected_model],
            "capabilities": self.model_capabilities[selected_model],
            "confidence": self._calculate_confidence(complexity, task_type)
        }
    
    def _generate_reasoning(self, task_type: str, complexity: Dict, 
                          base_model: str, selected_model: str, has_image: bool) -> str:
        """生成选择理由"""
        reasons = []
        
        # 任务类型理由
        if has_image:
            reasons.append("检测到图片内容，需要多模态处理能力")
        elif task_type == "complex_reasoning":
            reasons.append("检测到复杂推理任务")
        elif task_type == "technical_tasks":
            reasons.append("检测到技术相关内容")
        elif task_type == "creative_tasks":
            reasons.append("检测到创意任务")
        
        # 复杂度理由
        total_complexity = complexity["total_score"]
        if total_complexity >= 10:
            reasons.append("内容复杂度很高")
        elif total_complexity >= 5:
            reasons.append("内容复杂度中等")
        else:
            reasons.append("内容相对简单")
        
        # 模型选择理由
        if "2.5-pro" in selected_model:
            reasons.append("选择Pro模型确保最佳质量")
        elif "2.5-flash" in selected_model:
            reasons.append("选择Flash 2.5平衡质量和速度")
        else:
            reasons.append("选择Flash 2.0优化响应速度")
        
        # 调整理由
        if base_model != selected_model:
            reasons.append(f"根据用户偏好从{base_model}调整为{selected_model}")
        
        return "; ".join(reasons)
    
    def _calculate_confidence(self, complexity: Dict, task_type: str) -> float:
        """计算选择置信度"""
        base_confidence = 0.7
        
        # 根据复杂度调整置信度
        if complexity["total_score"] >= 8:
            base_confidence += 0.2
        elif complexity["total_score"] <= 3:
            base_confidence += 0.1
        
        # 根据任务类型调整
        if task_type in ["image_analysis", "complex_reasoning"]:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)

class MultimodalProcessor:
    """多模态内容处理器"""
    
    @staticmethod
    def process_image(image_data) -> Dict:
        """处理图片数据"""
        try:
            if isinstance(image_data, str):
                # base64字符串
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                img_bytes = base64.b64decode(image_data)
                img = Image.open(io.BytesIO(img_bytes))
            else:
                # 文件对象
                img = Image.open(image_data)
            
            # 获取图片信息
            width, height = img.size
            format_type = img.format
            mode = img.mode
            
            # 计算文件大小
            buffer = io.BytesIO()
            img.save(buffer, format=format_type or 'PNG')
            size_bytes = len(buffer.getvalue())
            
            # 转换为base64
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "success": True,
                "base64": img_base64,
                "width": width,
                "height": height,
                "format": format_type,
                "mode": mode,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def validate_image(image_info: Dict) -> Tuple[bool, str]:
        """验证图片是否符合要求"""
        if not image_info["success"]:
            return False, f"图片处理失败: {image_info['error']}"
        
        # 检查文件大小 (限制20MB)
        if image_info["size_mb"] > 20:
            return False, f"图片太大: {image_info['size_mb']}MB (最大20MB)"
        
        # 检查分辨率 (限制8000x8000)
        if image_info["width"] > 8000 or image_info["height"] > 8000:
            return False, f"分辨率太高: {image_info['width']}x{image_info['height']} (最大8000x8000)"
        
        return True, "图片验证通过"
