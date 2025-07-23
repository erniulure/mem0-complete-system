# 🧠 Mem0 记忆管理系统 - 完整部署方案

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v2.0-orange)](README.md)

## 📋 系统概述

Mem0是一个基于AI的智能记忆管理系统，能够自动提取、存储和检索对话中的重要信息。系统采用完全Docker化部署，支持多种AI模型，提供直观的Web界面和完整的API服务。

### 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web界面       │    │   API服务       │    │   AI服务        │
│   (Streamlit)   │◄──►│   (FastAPI)     │◄──►│ (Gemini/OpenAI) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Qdrant      │
│   (用户数据)     │    │   (向量数据库)   │
└─────────────────┘    └─────────────────┘
```

### ✨ 核心特性

- 🤖 **智能记忆提取**: 自动分析对话内容，提取关键信息
- 🔍 **语义搜索**: 基于向量数据库的智能搜索
- 🌐 **Web界面**: 直观的用户界面，支持实时对话
- 🔌 **API服务**: 完整的RESTful API，支持第三方集成
- 🐳 **Docker化**: 一键部署，环境隔离
- ⚙️ **配置管理**: 图形化配置工具，支持运行时修改
- 📊 **智能记忆** - 自动学习和记忆用户偏好
- 🎯 **高性能** - 基于向量数据库的快速检索

## 🚀 快速开始

### 方式一：一键部署（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd mem0-deployment

# 一键部署（仅核心服务，使用外部AI）
./deploy.sh

# 或者部署完整服务（包含AI服务）
./deploy.sh --mode=with-ai

# 自定义端口部署
./deploy.sh --port=8080 --ai-port=8001
```

### 方式二：手动部署

```bash
# 1. 复制环境配置文件
cp .env.example .env

# 2. 编辑配置文件（可选）
nano .env

# 3. 启动核心服务
docker-compose up -d

# 或启动完整服务（包含AI）
docker-compose -f docker-compose.yml -f docker-compose.ai-services.yml --profile ai-integrated up -d
```

## 🔧 配置选项

### 部署模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `standalone` | 仅部署Mem0核心服务 | 已有外部AI服务 |
| `with-ai` | 部署完整服务栈 | 一键完整部署 |
| `external` | 使用完全外部服务 | 分布式部署 |

### 端口配置

| 服务 | 默认端口 | 环境变量 | 说明 |
|------|----------|----------|------|
| Web界面 | 8503 | `WEBUI_PORT` | 主要访问入口 |
| Mem0 API | 8888 | `MEM0_API_PORT` | 记忆管理API |
| Gemini Balance | 8000 | `GEMINI_BALANCE_PORT` | AI服务 |
| PostgreSQL | 5433 | `POSTGRES_PORT` | 主数据库 |
| Qdrant | 6333 | `QDRANT_PORT` | 向量数据库 |

### AI服务配置

#### 使用外部Gemini Balance

```bash
# 在.env文件中配置
GEMINI_BALANCE_MODE=external
EXTERNAL_GEMINI_BALANCE_URL=http://your-server:8000/v1
EXTERNAL_GEMINI_BALANCE_TOKEN=your-token
```

#### 使用集成AI服务

```bash
# 在.env文件中配置
GEMINI_BALANCE_MODE=integrated
```

#### 使用OpenAI API（备用）

```bash
# 在.env文件中配置
OPENAI_API_KEY=your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 📖 使用指南

### 1. 访问系统

部署完成后，访问 `http://localhost:8503`

默认账户：
- 用户名：`admin`
- 密码：`admin123`

### 2. 配置AI服务

在系统设置中配置AI服务连接：
- API地址：根据部署模式自动配置
- API密钥：根据配置自动设置

### 3. 开始对话

在智能对话页面与AI助手交流，系统会自动学习和记忆重要信息。

## 🛠️ 高级配置

### 自定义配置文件

```bash
# 创建生产环境配置
cp .env.example .env.production

# 编辑配置
nano .env.production

# 使用自定义配置部署
./deploy.sh --config=.env.production
```

### 数据持久化

所有数据默认存储在Docker volumes中：
- `postgres_data`: PostgreSQL数据
- `qdrant_data`: 向量数据库数据
- `mem0_data`: 应用数据

### 日志管理

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f mem0-webui
```

## 🔍 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 修改.env文件中的端口配置
   WEBUI_PORT=8080
   ```

2. **AI服务连接失败**
   ```bash
   # 检查AI服务状态
   curl http://localhost:8000/health
   
   # 检查网络连接
   docker network ls
   ```

3. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose ps mem0-postgres
   
   # 查看数据库日志
   docker-compose logs mem0-postgres
   ```

### 重置系统

```bash
# 停止所有服务
docker-compose down

# 清除所有数据（谨慎操作）
docker-compose down -v

# 重新部署
./deploy.sh
```

## 📝 开发指南

### 本地开发

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up

# 进入开发容器
docker exec -it mem0-webui bash
```

### 自定义扩展

系统支持通过环境变量和配置文件进行扩展，详见 `.env.example` 文件。

## 📄 许可证

[MIT License](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请提交 Issue 或联系维护团队。
