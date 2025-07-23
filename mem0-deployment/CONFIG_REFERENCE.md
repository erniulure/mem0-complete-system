# Mem0 记忆管理系统 - 配置参数完整参考

## 📋 配置文件概览

Mem0系统使用以下配置文件：
- `.env` - 环境变量配置（主要配置文件）
- `configs/mem0-config.yaml` - Mem0核心配置
- `docker-compose.yml` - Docker服务编排配置

## 🌐 网络和端口配置

### WEBUI_PORT
- **描述**: Web界面访问端口
- **默认值**: `8503`
- **示例**: `WEBUI_PORT=8503`
- **说明**: 用户通过此端口访问Mem0的Web界面，如 http://localhost:8503

### MEM0_API_PORT
- **描述**: Mem0 API服务端口
- **默认值**: `8888`
- **示例**: `MEM0_API_PORT=8888`
- **说明**: 内部API通信端口，Web界面通过此端口与后端通信

### POSTGRES_PORT
- **描述**: PostgreSQL数据库端口
- **默认值**: `5432`
- **示例**: `POSTGRES_PORT=5432`
- **说明**: PostgreSQL数据库监听端口，存储用户数据和记忆信息

### QDRANT_PORT
- **描述**: Qdrant向量数据库HTTP端口
- **默认值**: `6333`
- **示例**: `QDRANT_PORT=6333`
- **说明**: Qdrant向量数据库HTTP API端口，用于向量搜索和存储

### QDRANT_GRPC_PORT
- **描述**: Qdrant向量数据库gRPC端口
- **默认值**: `6334`
- **示例**: `QDRANT_GRPC_PORT=6334`
- **说明**: Qdrant向量数据库gRPC通信端口，提供高性能数据传输

## 🤖 AI服务配置

### GEMINI_BALANCE_MODE
- **描述**: AI服务部署模式
- **可选值**: `external` | `integrated` | `openai`
- **默认值**: `external`
- **示例**: `GEMINI_BALANCE_MODE=external`
- **说明**: 
  - `external`: 使用外部Gemini Balance服务（推荐）
  - `integrated`: 集成部署Gemini Balance
  - `openai`: 直接使用OpenAI API

### EXTERNAL_GEMINI_BALANCE_URL
- **描述**: 外部Gemini Balance服务URL
- **默认值**: `http://gemini-balance:8000/v1`
- **示例**: `EXTERNAL_GEMINI_BALANCE_URL=http://47.245.60.206:8000/openai/v1`
- **说明**: 外部Gemini Balance服务的完整API地址

### EXTERNAL_GEMINI_BALANCE_TOKEN
- **描述**: Gemini Balance访问令牌
- **默认值**: `q1q2q3q4`
- **示例**: `EXTERNAL_GEMINI_BALANCE_TOKEN=your_access_token`
- **说明**: 访问Gemini Balance服务所需的API令牌

### OPENAI_API_KEY
- **描述**: OpenAI API密钥
- **默认值**: 无
- **示例**: `OPENAI_API_KEY=sk-1234567890abcdef`
- **说明**: 当使用OpenAI模式时必需的API密钥

### OPENAI_BASE_URL
- **描述**: OpenAI API基础URL
- **默认值**: `https://api.openai.com/v1`
- **示例**: `OPENAI_BASE_URL=https://api.openai.com/v1`
- **说明**: OpenAI API的基础URL，可配置为代理服务地址

## 🗄️ 数据库配置

### POSTGRES_DB
- **描述**: PostgreSQL数据库名称
- **默认值**: `mem0`
- **示例**: `POSTGRES_DB=mem0`
- **说明**: 存储Mem0数据的PostgreSQL数据库名称

### POSTGRES_USER
- **描述**: PostgreSQL数据库用户名
- **默认值**: `mem0`
- **示例**: `POSTGRES_USER=mem0`
- **说明**: 连接PostgreSQL数据库的用户名

### POSTGRES_PASSWORD
- **描述**: PostgreSQL数据库密码
- **默认值**: `mem0_secure_password_2024`
- **示例**: `POSTGRES_PASSWORD=your_secure_password`
- **说明**: PostgreSQL数据库密码，生产环境建议使用强密码

### POSTGRES_HOST
- **描述**: PostgreSQL数据库主机地址
- **默认值**: `mem0-postgres`
- **示例**: `POSTGRES_HOST=mem0-postgres`
- **说明**: PostgreSQL数据库的主机地址，Docker环境使用容器名

## 🔐 安全配置

### SESSION_SECRET_KEY
- **描述**: 会话加密密钥
- **默认值**: `mem0-secret-key-change-in-production`
- **示例**: `SESSION_SECRET_KEY=your-random-secret-key-here`
- **说明**: 用于加密用户会话的密钥，生产环境必须更改为随机字符串

### DEFAULT_ADMIN_USERNAME
- **描述**: 默认管理员用户名
- **默认值**: `admin`
- **示例**: `DEFAULT_ADMIN_USERNAME=admin`
- **说明**: 系统初始化时创建的管理员账户用户名

### DEFAULT_ADMIN_PASSWORD
- **描述**: 默认管理员密码
- **默认值**: `admin123`
- **示例**: `DEFAULT_ADMIN_PASSWORD=secure_admin_password`
- **说明**: 系统初始化时创建的管理员账户密码，建议首次登录后立即修改

## 📊 性能和日志配置

### LOG_LEVEL
- **描述**: 系统日志级别
- **可选值**: `DEBUG` | `INFO` | `WARNING` | `ERROR`
- **默认值**: `INFO`
- **示例**: `LOG_LEVEL=INFO`
- **说明**: 
  - `DEBUG`: 详细调试信息（开发环境）
  - `INFO`: 一般信息（生产环境推荐）
  - `WARNING`: 警告信息
  - `ERROR`: 仅错误信息

### DATA_PATH
- **描述**: 数据文件存储路径
- **默认值**: `./data`
- **示例**: `DATA_PATH=/opt/mem0/data`
- **说明**: 系统数据文件的存储目录，包括上传文件、缓存等

### LOGS_PATH
- **描述**: 日志文件存储路径
- **默认值**: `./logs`
- **示例**: `LOGS_PATH=/opt/mem0/logs`
- **说明**: 系统日志文件的存储目录

### DEPLOYMENT_MODE
- **描述**: 部署模式
- **可选值**: `standalone` | `distributed`
- **默认值**: `standalone`
- **示例**: `DEPLOYMENT_MODE=standalone`
- **说明**: 
  - `standalone`: 单机部署模式
  - `distributed`: 分布式部署模式

## ⚡ 健康检查配置

### HEALTH_CHECK_INTERVAL
- **描述**: 健康检查间隔
- **默认值**: `30s`
- **示例**: `HEALTH_CHECK_INTERVAL=30s`
- **说明**: Docker容器健康检查的时间间隔

### HEALTH_CHECK_TIMEOUT
- **描述**: 健康检查超时时间
- **默认值**: `10s`
- **示例**: `HEALTH_CHECK_TIMEOUT=10s`
- **说明**: 单次健康检查的超时时间

### HEALTH_CHECK_RETRIES
- **描述**: 健康检查重试次数
- **默认值**: `5`
- **示例**: `HEALTH_CHECK_RETRIES=5`
- **说明**: 健康检查失败后的重试次数

## 🔧 高级配置

### GEMINI_BALANCE_PORT
- **描述**: 集成部署时Gemini Balance端口
- **默认值**: `8000`
- **示例**: `GEMINI_BALANCE_PORT=8000`
- **说明**: 仅在integrated模式下使用

### MYSQL_ROOT_PASSWORD
- **描述**: Gemini Balance MySQL密码
- **默认值**: `123456`
- **示例**: `MYSQL_ROOT_PASSWORD=secure_mysql_password`
- **说明**: 集成部署Gemini Balance时使用的MySQL数据库密码

### MYSQL_DATABASE
- **描述**: Gemini Balance MySQL数据库名
- **默认值**: `gemini_balance`
- **示例**: `MYSQL_DATABASE=gemini_balance`
- **说明**: Gemini Balance使用的MySQL数据库名称

## 📝 配置示例

### 生产环境配置示例
```bash
# 基础配置
DEPLOYMENT_MODE=standalone

# 端口配置（避免冲突）
WEBUI_PORT=8503
MEM0_API_PORT=8888
POSTGRES_PORT=5432
QDRANT_PORT=6333

# AI服务配置（外部服务）
GEMINI_BALANCE_MODE=external
EXTERNAL_GEMINI_BALANCE_URL=http://your-ai-service.com/v1
EXTERNAL_GEMINI_BALANCE_TOKEN=your_production_token

# 数据库配置（强密码）
POSTGRES_DB=mem0_prod
POSTGRES_USER=mem0_user
POSTGRES_PASSWORD=very_secure_password_2024

# 安全配置（随机密钥）
SESSION_SECRET_KEY=random-generated-secret-key-for-production
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=secure_admin_password

# 性能配置
LOG_LEVEL=INFO
DATA_PATH=/opt/mem0/data
LOGS_PATH=/opt/mem0/logs
```

### 开发环境配置示例
```bash
# 基础配置
DEPLOYMENT_MODE=standalone

# 端口配置（默认端口）
WEBUI_PORT=8503
MEM0_API_PORT=8888
POSTGRES_PORT=5432
QDRANT_PORT=6333

# AI服务配置（本地测试）
GEMINI_BALANCE_MODE=external
EXTERNAL_GEMINI_BALANCE_URL=http://localhost:8000/v1
EXTERNAL_GEMINI_BALANCE_TOKEN=test_token

# 数据库配置（简单密码）
POSTGRES_DB=mem0_dev
POSTGRES_USER=mem0
POSTGRES_PASSWORD=dev_password

# 安全配置（开发用）
SESSION_SECRET_KEY=dev-secret-key
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

# 调试配置
LOG_LEVEL=DEBUG
DATA_PATH=./data
LOGS_PATH=./logs
```
