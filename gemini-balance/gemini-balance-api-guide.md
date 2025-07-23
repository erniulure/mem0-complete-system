# Gemini Balance API 调用指导文档

## 📖 概述

Gemini Balance 是一个高性能的 Gemini API 代理服务，提供多种格式的 API 接口，支持负载均衡、流式响应和多模型调用。本文档将详细介绍如何调用 Gemini Balance 的各种 API。

## 🔧 服务配置

### 基本信息
- **服务地址**: `http://localhost:8000`
- **认证Token**: `q1q2q3q4`
- **认证方式**: Bearer Token
- **数据库**: MySQL (root/Woaihujun123.)

### 环境要求
- Docker 和 Docker Compose
- MySQL 5.7+ 容器
- 端口 8000 可用

## 🔑 认证方式

所有 API 调用都需要在请求头中包含认证信息：

```bash
Authorization: Bearer q1q2q3q4
```

## 🚀 API 端点详解

### 1. 获取模型列表

#### 标准格式
```bash
curl -H "Authorization: Bearer q1q2q3q4" \
     http://localhost:8000/v1/models
```

#### OpenAI 兼容格式
```bash
curl -H "Authorization: Bearer q1q2q3q4" \
     http://localhost:8000/openai/v1/models
```

#### HuggingFace 兼容格式
```bash
curl -H "Authorization: Bearer q1q2q3q4" \
     http://localhost:8000/hf/v1/models
```

**响应示例**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "gemini-1.5-flash",
      "object": "model",
      "created": 1752996930,
      "owned_by": "google"
    }
  ]
}
```

### 2. 聊天完成 API

#### 基础聊天请求
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer q1q2q3q4" \
  -d '{
    "model": "gemini-1.5-flash",
    "messages": [
      {
        "role": "user",
        "content": "你好，请介绍一下你自己"
      }
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

#### 流式聊天请求
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer q1q2q3q4" \
  -d '{
    "model": "gemini-1.5-flash",
    "messages": [
      {
        "role": "user", 
        "content": "简单介绍一下人工智能"
      }
    ],
    "stream": true,
    "max_tokens": 150
  }'
```

#### 多轮对话请求
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer q1q2q3q4" \
  -d '{
    "model": "gemini-1.5-flash",
    "messages": [
      {
        "role": "user",
        "content": "什么是机器学习？"
      },
      {
        "role": "assistant",
        "content": "机器学习是人工智能的一个分支..."
      },
      {
        "role": "user",
        "content": "能举个具体例子吗？"
      }
    ],
    "max_tokens": 200
  }'
```

### 3. OpenAI 兼容格式

```bash
curl -X POST http://localhost:8000/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer q1q2q3q4" \
  -d '{
    "model": "gemini-1.5-flash",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ],
    "max_tokens": 50
  }'
```

### 4. 文本嵌入 API

```bash
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer q1q2q3q4" \
  -d '{
    "model": "text-embedding-004",
    "input": "这是一段需要生成嵌入向量的文本"
  }'
```

### 5. 图像生成 API

```bash
curl -X POST http://localhost:8000/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer q1q2q3q4" \
  -d '{
    "model": "imagen-3.0-generate-002",
    "prompt": "一只可爱的小猫在花园里玩耍",
    "n": 1,
    "size": "1024x1024"
  }'
```

## 🎯 支持的模型

### 聊天模型
- `gemini-1.5-pro-latest`
- `gemini-1.5-flash`
- `gemini-1.5-flash-8b`
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.0-flash-exp`
- `gemini-2.0-pro-exp`

### 嵌入模型
- `text-embedding-004`
- `embedding-001`
- `gemini-embedding-001`

### 图像生成模型
- `imagen-3.0-generate-002`
- `imagen-4.0-generate-preview-06-06`

## 📊 请求参数说明

### 聊天完成参数
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 使用的模型名称 |
| `messages` | array | 是 | 对话消息数组 |
| `max_tokens` | integer | 否 | 最大生成token数 |
| `temperature` | float | 否 | 控制随机性 (0.0-2.0) |
| `stream` | boolean | 否 | 是否启用流式响应 |
| `top_p` | float | 否 | 核采样参数 |

### 消息格式
```json
{
  "role": "user|assistant|system",
  "content": "消息内容"
}
```

## 🌐 Web 管理界面

访问 `http://localhost:8000` 可以打开 Web 管理界面，功能包括：

- 模型状态监控
- API 调用统计
- 配置管理
- 日志查看

登录需要使用认证Token: `q1q2q3q4`

## 💡 最佳实践

### 1. 选择合适的端点格式
- **标准格式** (`/v1/*`): 推荐用于新项目，性能最佳
- **OpenAI格式** (`/openai/v1/*`): 适合从OpenAI迁移的项目
- **HuggingFace格式** (`/hf/v1/*`): 适合HuggingFace生态集成

### 2. 模型选择建议
- **快速响应**: `gemini-1.5-flash`, `gemini-1.5-flash-8b`
- **高质量输出**: `gemini-1.5-pro`, `gemini-2.5-pro`
- **实验性功能**: `gemini-2.0-flash-exp`

### 3. 性能优化
- 使用流式响应提升用户体验
- 合理设置 `max_tokens` 控制响应长度
- 根据需求调整 `temperature` 参数

### 4. 错误处理
```bash
# 检查服务健康状态
curl http://localhost:8000/health

# 查看API统计信息
curl -H "Authorization: Bearer q1q2q3q4" \
     http://localhost:8000/stats
```

## 🔍 故障排除

### 常见问题

1. **认证失败 (401)**
   - 检查Token是否正确: `q1q2q3q4`
   - 确认请求头格式: `Authorization: Bearer q1q2q3q4`

2. **服务不可用 (503)**
   - 检查服务状态: `docker compose ps`
   - 查看日志: `docker compose logs gemini-balance`

3. **数据库连接失败**
   - 确认MySQL容器运行正常
   - 验证数据库配置: root/Woaihujun123.

### 日志查看
```bash
# 查看实时日志
docker compose logs -f gemini-balance

# 查看MySQL日志
docker logs mysql5.7
```

## 📞 技术支持

如遇到问题，请检查：
1. 服务运行状态
2. 网络连接
3. 认证配置
4. 模型可用性

## 💻 编程语言示例

### Python 示例

```python
import requests
import json

# 基础配置
BASE_URL = "http://localhost:8000"
API_KEY = "q1q2q3q4"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 聊天完成
def chat_completion(message, model="gemini-1.5-flash"):
    url = f"{BASE_URL}/v1/chat/completions"
    data = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 150
    }

    response = requests.post(url, headers=HEADERS, json=data)
    return response.json()

# 流式聊天
def stream_chat(message, model="gemini-1.5-flash"):
    url = f"{BASE_URL}/v1/chat/completions"
    data = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": True,
        "max_tokens": 150
    }

    response = requests.post(url, headers=HEADERS, json=data, stream=True)
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))

# 使用示例
result = chat_completion("你好，介绍一下自己")
print(json.dumps(result, indent=2, ensure_ascii=False))
```

### JavaScript/Node.js 示例

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';
const API_KEY = 'q1q2q3q4';

const headers = {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
};

// 聊天完成
async function chatCompletion(message, model = 'gemini-1.5-flash') {
    try {
        const response = await axios.post(`${BASE_URL}/v1/chat/completions`, {
            model: model,
            messages: [{ role: 'user', content: message }],
            max_tokens: 150
        }, { headers });

        return response.data;
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

// 获取模型列表
async function getModels() {
    try {
        const response = await axios.get(`${BASE_URL}/v1/models`, { headers });
        return response.data;
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

// 使用示例
chatCompletion('Hello, how are you?').then(result => {
    console.log(JSON.stringify(result, null, 2));
});
```

### PHP 示例

```php
<?php
$baseUrl = 'http://localhost:8000';
$apiKey = 'q1q2q3q4';

function chatCompletion($message, $model = 'gemini-1.5-flash') {
    global $baseUrl, $apiKey;

    $url = $baseUrl . '/v1/chat/completions';
    $data = [
        'model' => $model,
        'messages' => [
            ['role' => 'user', 'content' => $message]
        ],
        'max_tokens' => 150
    ];

    $options = [
        'http' => [
            'header' => [
                "Authorization: Bearer $apiKey",
                "Content-Type: application/json"
            ],
            'method' => 'POST',
            'content' => json_encode($data)
        ]
    ];

    $context = stream_context_create($options);
    $result = file_get_contents($url, false, $context);

    return json_decode($result, true);
}

// 使用示例
$result = chatCompletion('你好，请介绍一下你自己');
echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
?>
```

## 🔗 集成示例

### 与 OpenAI SDK 集成

```python
# 使用 OpenAI Python SDK
from openai import OpenAI

client = OpenAI(
    api_key="q1q2q3q4",
    base_url="http://localhost:8000/openai/v1"
)

response = client.chat.completions.create(
    model="gemini-1.5-flash",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ]
)

print(response.choices[0].message.content)
```

### 与 LangChain 集成

```python
from langchain.llms.base import LLM
from langchain.schema import BaseMessage
import requests

class GeminiBalanceLLM(LLM):
    def __init__(self, api_key="q1q2q3q4", base_url="http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url

    def _call(self, prompt: str, stop=None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gemini-1.5-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150
        }

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=data
        )

        return response.json()["choices"][0]["message"]["content"]

    @property
    def _llm_type(self) -> str:
        return "gemini-balance"

# 使用示例
llm = GeminiBalanceLLM()
result = llm("解释一下什么是人工智能")
print(result)
```

---

**文档版本**: v1.0
**最后更新**: 2025-07-20
**服务版本**: gemini-balance 2.2.0
