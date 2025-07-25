#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文档处理器模块
支持各种文档格式的处理和验证
"""

import os
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List

class DocumentProcessor:
    """文档处理器类"""
    
    # 支持的文件格式和对应的MIME类型
    SUPPORTED_FORMATS = {
        # Office文档
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        
        # PDF
        '.pdf': 'application/pdf',
        
        # 文本文档
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.csv': 'text/csv',
        '.json': 'application/json',
        
        # 其他
        '.rtf': 'application/rtf',
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation'
    }
    
    # Gemini API原生支持的格式
    GEMINI_NATIVE_FORMATS = {
        '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', 
        '.txt', '.md', '.csv', '.json'
    }
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        检查文件是否支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持
        """
        if not os.path.exists(file_path):
            return False
        
        file_ext = Path(file_path).suffix.lower()
        return file_ext in cls.SUPPORTED_FORMATS
    
    @classmethod
    def get_mime_type(cls, file_path: str) -> str:
        """
        获取文件的MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: MIME类型
        """
        file_ext = Path(file_path).suffix.lower()
        
        # 首先尝试从我们的映射表获取
        if file_ext in cls.SUPPORTED_FORMATS:
            return cls.SUPPORTED_FORMATS[file_ext]
        
        # 如果没有找到，使用系统的mimetypes模块
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    @classmethod
    def can_upload_to_gemini(cls, file_path: str) -> bool:
        """
        检查文件是否可以直接上传到Gemini API
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否可以上传
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in cls.GEMINI_NATIVE_FORMATS
    
    @classmethod
    def get_file_info(cls, file_path: str) -> Dict[str, Any]:
        """
        获取文件详细信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息
        """
        if not os.path.exists(file_path):
            return {
                'exists': False,
                'error': f'文件不存在: {file_path}'
            }
        
        path_obj = Path(file_path)
        file_size = os.path.getsize(file_path)
        
        return {
            'exists': True,
            'name': path_obj.name,
            'stem': path_obj.stem,
            'suffix': path_obj.suffix.lower(),
            'size_bytes': file_size,
            'size_mb': round(file_size / 1024 / 1024, 2),
            'mime_type': cls.get_mime_type(file_path),
            'supported': cls.is_supported(file_path),
            'can_upload': cls.can_upload_to_gemini(file_path)
        }
    
    @classmethod
    def prepare_for_gemini_api(cls, file_path: str) -> Dict[str, Any]:
        """
        为Gemini API准备文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 准备结果
        """
        file_info = cls.get_file_info(file_path)
        
        if not file_info['exists']:
            return {
                'supported': False,
                'can_upload': False,
                'error': file_info['error'],
                'description': '文件不存在'
            }
        
        if not file_info['supported']:
            return {
                'supported': False,
                'can_upload': False,
                'error': f'不支持的文件格式: {file_info["suffix"]}',
                'description': f'文件格式 {file_info["suffix"]} 不在支持列表中',
                'supported_formats': list(cls.SUPPORTED_FORMATS.keys())
            }
        
        if not file_info['can_upload']:
            return {
                'supported': True,
                'can_upload': False,
                'error': f'文件格式 {file_info["suffix"]} 需要预处理',
                'description': '该格式需要转换后才能上传到Gemini API',
                'requires_preprocessing': True
            }
        
        # 检查文件大小限制 (2GB)
        max_size_bytes = 2 * 1024 * 1024 * 1024  # 2GB
        if file_info['size_bytes'] > max_size_bytes:
            return {
                'supported': True,
                'can_upload': False,
                'error': f'文件太大: {file_info["size_mb"]} MB (最大2048 MB)',
                'description': 'Gemini API限制单个文件最大2GB'
            }
        
        return {
            'supported': True,
            'can_upload': True,
            'file_info': file_info,
            'description': f'文件 {file_info["name"]} 可以直接上传到Gemini API',
            'ready_for_upload': True
        }
    
    @classmethod
    def get_supported_formats_list(cls) -> List[str]:
        """
        获取支持的文件格式列表
        
        Returns:
            List[str]: 支持的格式列表
        """
        return list(cls.SUPPORTED_FORMATS.keys())
    
    @classmethod
    def get_gemini_formats_list(cls) -> List[str]:
        """
        获取Gemini API原生支持的格式列表
        
        Returns:
            List[str]: Gemini支持的格式列表
        """
        return list(cls.GEMINI_NATIVE_FORMATS)
    
    @classmethod
    def validate_file_for_upload(cls, file_path: str) -> Dict[str, Any]:
        """
        验证文件是否可以上传
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 验证结果
        """
        result = cls.prepare_for_gemini_api(file_path)
        
        return {
            'valid': result.get('can_upload', False),
            'message': result.get('description', ''),
            'error': result.get('error'),
            'details': result
        }

def main():
    """测试函数"""
    processor = DocumentProcessor()
    
    # 测试支持的格式
    print("📄 支持的文档格式:")
    for ext, mime in processor.SUPPORTED_FORMATS.items():
        print(f"  {ext}: {mime}")
    
    print("\n🚀 Gemini API原生支持的格式:")
    for ext in processor.GEMINI_NATIVE_FORMATS:
        print(f"  {ext}")
    
    # 测试文件验证
    test_files = ["test.xlsx", "test.docx", "test.pdf", "test.unsupported"]
    
    print("\n🧪 文件支持测试:")
    for file in test_files:
        result = processor.prepare_for_gemini_api(file)
        status = "✅" if result.get('supported') else "❌"
        upload = "🚀" if result.get('can_upload') else "⚠️"
        print(f"  {file}: {status} 支持 {upload} 可上传")
        if result.get('description'):
            print(f"    {result['description']}")

if __name__ == "__main__":
    main()
