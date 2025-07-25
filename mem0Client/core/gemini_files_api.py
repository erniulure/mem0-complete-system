#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gemini Files API集成模块
支持上传和管理各种文档格式
"""

import os
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class GeminiFilesAPI:
    """Gemini Files API客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://generativelanguage.googleapis.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.upload_url = f"{base_url}/upload/v1beta/files"
        self.files_url = f"{base_url}/v1beta/files"
        
    def upload_document(self, file_path: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        上传文档到Gemini Files API
        
        Args:
            file_path: 文件路径
            display_name: 显示名称
            
        Returns:
            上传结果字典
        """
        if not os.path.exists(file_path):
            return {'success': False, 'error': f'文件不存在: {file_path}'}
        
        # 检查文件是否支持
        if not DocumentProcessor.is_supported(file_path):
            return {'success': False, 'error': f'不支持的文件格式: {Path(file_path).suffix}'}
        
        # 准备文件信息
        file_size = os.path.getsize(file_path)
        mime_type = DocumentProcessor.get_mime_type(file_path)
        display_name = display_name or Path(file_path).name
        
        try:
            # 第一步：初始化上传会话
            upload_session = self._initialize_upload(file_size, mime_type, display_name)
            if not upload_session['success']:
                return upload_session
            
            # 第二步：上传文件数据
            upload_result = self._upload_file_data(upload_session['upload_url'], file_path, file_size)
            if not upload_result['success']:
                return upload_result
            
            # 第三步：等待处理完成
            file_info = self._wait_for_processing(upload_result['file_uri'])
            
            return {
                'success': True,
                'file_uri': upload_result['file_uri'],
                'file_name': upload_result.get('file_name'),
                'display_name': display_name,
                'mime_type': mime_type,
                'size_bytes': file_size,
                'size_mb': round(file_size / 1024 / 1024, 2),
                'state': file_info.get('state', 'UNKNOWN'),
                'expiration_time': file_info.get('expirationTime'),
                'message': f'文档上传成功: {display_name}'
            }
            
        except Exception as e:
            logger.error(f"上传文档失败: {str(e)}")
            return {'success': False, 'error': f'上传失败: {str(e)}'}
    
    def _initialize_upload(self, file_size: int, mime_type: str, display_name: str) -> Dict[str, Any]:
        """初始化上传会话"""
        headers = {
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-Upload-Protocol': 'resumable',
            'X-Goog-Upload-Command': 'start',
            'X-Goog-Upload-Header-Content-Length': str(file_size),
            'X-Goog-Upload-Header-Content-Type': mime_type,
            'Content-Type': 'application/json'
        }
        
        data = {
            'file': {
                'display_name': display_name
            }
        }
        
        try:
            response = requests.post(self.upload_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                upload_url = response.headers.get('X-Goog-Upload-URL')
                if upload_url:
                    return {'success': True, 'upload_url': upload_url}
                else:
                    return {'success': False, 'error': '未获取到上传URL'}
            else:
                return {'success': False, 'error': f'初始化上传失败: {response.status_code} - {response.text}'}
                
        except Exception as e:
            return {'success': False, 'error': f'初始化上传异常: {str(e)}'}
    
    def _upload_file_data(self, upload_url: str, file_path: str, file_size: int) -> Dict[str, Any]:
        """上传文件数据"""
        headers = {
            'Content-Length': str(file_size),
            'X-Goog-Upload-Offset': '0',
            'X-Goog-Upload-Command': 'upload, finalize'
        }
        
        try:
            with open(file_path, 'rb') as file:
                response = requests.post(upload_url, headers=headers, data=file, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                file_info = result.get('file', {})
                return {
                    'success': True,
                    'file_uri': file_info.get('uri'),
                    'file_name': file_info.get('name'),
                    'state': file_info.get('state', 'PROCESSING')
                }
            else:
                return {'success': False, 'error': f'上传文件数据失败: {response.status_code} - {response.text}'}
                
        except Exception as e:
            return {'success': False, 'error': f'上传文件数据异常: {str(e)}'}
    
    def _wait_for_processing(self, file_uri: str, max_wait_time: int = 60) -> Dict[str, Any]:
        """等待文件处理完成"""
        if not file_uri:
            return {'state': 'UNKNOWN'}
        
        # 从URI中提取文件名
        file_name = file_uri.split('/')[-1]
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                file_info = self.get_file_info(file_name)
                if file_info['success']:
                    state = file_info.get('state', 'UNKNOWN')
                    if state in ['ACTIVE', 'FAILED']:
                        return file_info
                
                time.sleep(2)  # 等待2秒后重试
                
            except Exception as e:
                logger.warning(f"检查文件状态失败: {str(e)}")
                break
        
        return {'state': 'TIMEOUT', 'message': '等待处理超时'}
    
    def get_file_info(self, file_name: str) -> Dict[str, Any]:
        """获取文件信息"""
        headers = {'X-Goog-Api-Key': self.api_key}
        
        try:
            response = requests.get(f"{self.files_url}/{file_name}", headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    **result
                }
            else:
                return {'success': False, 'error': f'获取文件信息失败: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'获取文件信息异常: {str(e)}'}
    
    def list_files(self, page_size: int = 10) -> Dict[str, Any]:
        """列出已上传的文件"""
        headers = {'X-Goog-Api-Key': self.api_key}
        params = {'pageSize': page_size}
        
        try:
            response = requests.get(self.files_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return {'success': True, **response.json()}
            else:
                return {'success': False, 'error': f'列出文件失败: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'列出文件异常: {str(e)}'}
    
    def delete_file(self, file_name: str) -> Dict[str, Any]:
        """删除文件"""
        headers = {'X-Goog-Api-Key': self.api_key}
        
        try:
            response = requests.delete(f"{self.files_url}/{file_name}", headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {'success': True, 'message': f'文件已删除: {file_name}'}
            else:
                return {'success': False, 'error': f'删除文件失败: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'error': f'删除文件异常: {str(e)}'}
    
    def create_multimodal_message(self, text: str, file_uri: str, mime_type: str) -> Dict[str, Any]:
        """
        创建包含文档的多模态消息
        
        Args:
            text: 文本内容
            file_uri: 文件URI
            mime_type: MIME类型
            
        Returns:
            多模态消息格式
        """
        return {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": text
                },
                {
                    "type": "file_data",
                    "file_data": {
                        "mime_type": mime_type,
                        "file_uri": file_uri
                    }
                }
            ]
        }

class DocumentUploadManager:
    """文档上传管理器"""
    
    def __init__(self, api_key: str):
        self.files_api = GeminiFilesAPI(api_key)
        self.processor = DocumentProcessor()
    
    def upload_and_analyze(self, file_path: str, question: str = "请分析这个文档的内容") -> Dict[str, Any]:
        """
        上传文档并准备分析
        
        Args:
            file_path: 文件路径
            question: 分析问题
            
        Returns:
            包含上传结果和消息格式的字典
        """
        # 检查文件支持情况
        support_info = self.processor.prepare_for_gemini_api(file_path)
        if not support_info.get('supported') or not support_info.get('can_upload'):
            return {
                'success': False,
                'error': support_info.get('error', '文件不支持'),
                'support_info': support_info
            }
        
        # 上传文档
        upload_result = self.files_api.upload_document(file_path)
        if not upload_result['success']:
            return upload_result
        
        # 创建多模态消息
        message = self.files_api.create_multimodal_message(
            text=question,
            file_uri=upload_result['file_uri'],
            mime_type=upload_result['mime_type']
        )
        
        return {
            'success': True,
            'upload_info': upload_result,
            'message': message,
            'support_info': support_info,
            'ready_for_api': True
        }

def main():
    """测试函数"""
    # 这里需要真实的API密钥
    api_key = os.getenv('GEMINI_API_KEY', 'your-api-key-here')
    
    if api_key == 'your-api-key-here':
        print("⚠️ 请设置GEMINI_API_KEY环境变量")
        return
    
    manager = DocumentUploadManager(api_key)
    
    # 测试文件支持检查
    test_files = ["test.xlsx", "test.docx", "test.pdf"]
    
    print("📄 文档上传支持测试:")
    for file in test_files:
        support_info = manager.processor.prepare_for_gemini_api(file)
        print(f"  {file}: {'✅' if support_info.get('supported') else '❌'}")
        if support_info.get('description'):
            print(f"    {support_info['description']}")

if __name__ == "__main__":
    main()
