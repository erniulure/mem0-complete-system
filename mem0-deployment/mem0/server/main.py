#!/usr/bin/env python3
"""
Mem0 API 服务器
基于 FastAPI 的 Mem0 记忆管理 API
"""

import os
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from mem0 import Memory
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 环境变量配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")
HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/data/history.db")

# 配置加载逻辑
try:
    with open("/app/configs/mem0-config.yaml", "r") as f:
        DEFAULT_CONFIG = yaml.safe_load(f)
    DEFAULT_CONFIG["history_db_path"] = HISTORY_DB_PATH
    os.makedirs(os.path.dirname(HISTORY_DB_PATH), exist_ok=True)
except FileNotFoundError:
    DEFAULT_CONFIG = {
        "version": "v1.1",
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "mem0_collection",
                "host": "mem0-qdrant",
                "port": 6333,
                "embedding_model_dims": 768,
            },
        },
        "llm": {
            "provider": "openai",
            "config": {
                "api_key": OPENAI_API_KEY,
                "temperature": 0.1,
                "model": "gemini-2.0-flash-exp"
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "api_key": OPENAI_API_KEY,
                "model": "text-embedding-004"
            }
        },
        "history_db_path": HISTORY_DB_PATH,
    }

# 初始化 Memory 实例
MEMORY_INSTANCE = Memory.from_config(DEFAULT_CONFIG)

# FastAPI 应用
app = FastAPI(
    title="Mem0 API",
    description="Mem0 记忆管理系统 API",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class Message(BaseModel):
    role: str
    content: str

class AddMemoryRequest(BaseModel):
    messages: List[Message]
    user_id: str
    custom_instructions: Optional[str] = None
    includes: Optional[List[str]] = None
    excludes: Optional[List[str]] = None
    model: Optional[str] = None  # 添加模型字段支持

class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: Optional[int] = 10

# API 路由
@app.get("/")
async def root():
    return {"message": "Mem0 API", "docs": "/docs"}

@app.post("/memories")
async def add_memory(request: AddMemoryRequest):
    try:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # 构建mem0支持的参数字典
        add_params = {
            "messages": messages,
            "user_id": request.user_id
        }

        # 将custom_instructions转换为prompt参数（mem0支持）
        if request.custom_instructions:
            add_params["prompt"] = request.custom_instructions

        # 将includes和excludes信息添加到metadata中（mem0支持）
        metadata = {}
        if request.includes:
            metadata["includes"] = request.includes
        if request.excludes:
            metadata["excludes"] = request.excludes
        if metadata:
            add_params["metadata"] = metadata

        result = MEMORY_INSTANCE.add(**add_params)
        return {"results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories")
async def get_memories(user_id: str):
    try:
        memories = MEMORY_INSTANCE.get_all(user_id=user_id)
        return {"results": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_memories(request: SearchRequest):
    try:
        results = MEMORY_INSTANCE.search(
            query=request.query,
            user_id=request.user_id,
            limit=request.limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    try:
        MEMORY_INSTANCE.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_memories():
    try:
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
