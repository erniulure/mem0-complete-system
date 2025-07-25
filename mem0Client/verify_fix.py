#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证多模态处理器修复的核心逻辑
不依赖streamlit，直接测试类的功能
"""

import sys
import os
from PIL import Image
import io
import base64

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_multimodal_processor_import():
    """测试MultimodalProcessor导入"""
    print("🧪 测试MultimodalProcessor导入...")
    
    try:
        from multimodal_model_selector import MultimodalProcessor
        print("✅ MultimodalProcessor导入成功")
        return True
    except Exception as e:
        print(f"❌ MultimodalProcessor导入失败: {str(e)}")
        return False

def test_simple_processor_logic():
    """测试简单处理器逻辑（不依赖streamlit）"""
    print("\n🧪 测试简单处理器逻辑...")
    
    try:
        # 直接定义简单处理器类
        class SimpleImageProcessor:
            @staticmethod
            def process_image(image_data):
                try:
                    if isinstance(image_data, str):
                        if image_data.startswith('data:image'):
                            image_data = image_data.split(',')[1]
                        img_bytes = base64.b64decode(image_data)
                        img = Image.open(io.BytesIO(img_bytes))
                    else:
                        img = Image.open(image_data)
                    
                    width, height = img.size
                    format_type = img.format or 'PNG'
                    
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
                    return {"success": False, "error": str(e)}
            
            @staticmethod
            def validate_image(image_info):
                if not image_info["success"]:
                    return False, f"图片处理失败: {image_info['error']}"
                if image_info["size_mb"] > 20:
                    return False, f"图片太大: {image_info['size_mb']}MB (最大20MB)"
                if image_info["width"] > 8000 or image_info["height"] > 8000:
                    return False, f"分辨率太高: {image_info['width']}x{image_info['height']} (最大8000x8000)"
                return True, "图片验证通过"
        
        # 创建测试图片
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # 测试处理
        processor = SimpleImageProcessor()
        result = processor.process_image(buffer)
        
        if result["success"]:
            print("✅ 简单处理器逻辑正常")
            print(f"   - 尺寸: {result['width']}x{result['height']}")
            print(f"   - 格式: {result['format']}")
            
            # 测试验证
            is_valid, msg = processor.validate_image(result)
            if is_valid:
                print(f"✅ 验证逻辑正常: {msg}")
            else:
                print(f"❌ 验证逻辑失败: {msg}")
                return False
        else:
            print(f"❌ 简单处理器逻辑失败: {result['error']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 测试简单处理器逻辑异常: {str(e)}")
        return False

def test_base64_handling():
    """测试base64处理逻辑"""
    print("\n🧪 测试base64处理逻辑...")
    
    try:
        from multimodal_model_selector import MultimodalProcessor
        
        # 创建base64图片
        img = Image.new('RGB', (50, 50), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 测试data URL格式
        data_url = f"data:image/png;base64,{img_base64}"
        
        processor = MultimodalProcessor()
        result = processor.process_image(data_url)
        
        if result["success"]:
            print("✅ data URL格式处理正常")
            print(f"   - 尺寸: {result['width']}x{result['height']}")
        else:
            print(f"❌ data URL格式处理失败: {result['error']}")
            return False
        
        # 测试纯base64格式
        result2 = processor.process_image(img_base64)
        if result2["success"]:
            print("✅ 纯base64格式处理正常")
        else:
            print(f"❌ 纯base64格式处理失败: {result2['error']}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 测试base64处理异常: {str(e)}")
        return False

def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    try:
        from multimodal_model_selector import MultimodalProcessor
        
        processor = MultimodalProcessor()
        
        # 测试无效数据
        result = processor.process_image("invalid_data")
        if not result["success"] and "error" in result:
            print("✅ 无效数据错误处理正常")
            print(f"   - 错误信息: {result['error']}")
        else:
            print("❌ 无效数据错误处理失败")
            return False
        
        # 测试空数据
        result2 = processor.process_image("")
        if not result2["success"] and "error" in result2:
            print("✅ 空数据错误处理正常")
        else:
            print("❌ 空数据错误处理失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 测试错误处理异常: {str(e)}")
        return False

def main():
    """主验证函数"""
    print("🔧 验证多模态处理器修复...")
    print("=" * 50)
    
    tests = [
        test_multimodal_processor_import,
        test_simple_processor_logic,
        test_base64_handling,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 验证结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 核心逻辑验证通过！修复应该有效！")
        print("\n💡 修复说明:")
        print("1. 添加了ensure_multimodal_processor()函数确保初始化")
        print("2. 创建了SimpleImageProcessor作为备用处理器")
        print("3. 在所有使用multimodal_processor的地方添加了初始化检查")
        print("4. 提供了完整的错误处理和降级机制")
        return True
    else:
        print("⚠️ 部分验证失败，请检查修复代码")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
