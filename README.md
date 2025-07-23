# 🧠 Mem0 完整智能记忆管理系统

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v2.0-orange)](README.md)

## 📋 项目概述

这是一个完整的智能记忆管理系统，集成了三个核心组件：

- **🧠 Mem0**: 核心记忆管理引擎和API服务
- **🌐 Mem0Client**: Web用户界面和客户端
- **🤖 Gemini-Balance**: AI服务代理和负载均衡

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mem0Client    │    │   Mem0-API      │    │ Gemini-Balance  │
│   (Web界面)     │◄──►│   (核心引擎)     │◄──►│   (AI代理)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Qdrant      │    │     MySQL       │
│   (用户数据)     │    │   (向量数据库)   │    │   (AI服务数据)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 项目结构

```
mem0-complete-system/
├── README.md                    # 主项目说明
├── LICENSE                      # 许可证
├── docker-compose.yml           # 完整系统编排
├── .env.example                # 环境变量示例
├── install.sh                  # 一键安装脚本
├── 
├── mem0-deployment/             # Mem0核心部署
│   ├── README.md               # Mem0部署说明
│   ├── docker-compose.yml     # Mem0服务编排
│   ├── install.sh              # Mem0安装脚本
│   ├── scripts/                # 管理脚本
│   │   ├── config-wizard.sh   # 配置向导
│   │   ├── config-manager.sh  # 配置管理器
│   │   └── quick-start.sh     # 快速启动器
│   ├── mem0/                   # Mem0核心代码
│   ├── mem0Client/             # 客户端代码
│   └── configs/                # 配置文件
│
├── mem0Client/                  # Web界面客户端
│   ├── README.md               # 客户端说明
│   ├── web_app_full_cn.py      # 主应用
│   ├── core/                   # 核心组件
│   ├── config.yaml             # 客户端配置
│   └── requirements.txt        # 依赖包
│
└── gemini-balance/              # AI服务代理
    ├── README.md               # AI代理说明
    ├── docker-compose.yml     # AI服务编排
    ├── app/                    # 代理应用
    ├── deploy.sh               # 部署脚本
    └── requirements.txt        # 依赖包
```

## 🚀 快速开始

### 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- Linux/macOS/Windows (WSL2)
- 最少 8GB RAM
- 最少 20GB 磁盘空间

### 🎯 一键安装完整系统

```bash
# 1. 克隆项目
git clone https://github.com/your-username/mem0-complete-system.git
cd mem0-complete-system

# 2. 运行一键安装（推荐）
./install.sh
```

### 🔧 分步安装

#### 方案一：使用Mem0集成部署（推荐）

```bash
# 进入Mem0部署目录
cd mem0-deployment

# 运行配置向导
./config-wizard.sh

# 启动完整系统
docker-compose up -d

# 检查状态
./quick-start.sh
```

#### 方案二：独立部署各组件

```bash
# 1. 部署Gemini-Balance AI服务
cd gemini-balance
./deploy.sh

# 2. 部署Mem0核心系统
cd ../mem0-deployment
./install.sh

# 3. 配置AI服务连接
./config-manager.sh
```

## 🌐 系统访问

### 完整系统访问地址

| 服务 | 地址 | 描述 |
|------|------|------|
| 🌐 **Mem0 Web界面** | http://localhost:8503 | 主要用户界面 |
| 🔌 **Mem0 API** | http://localhost:8888 | 记忆管理API |
| 📚 **API文档** | http://localhost:8888/docs | Swagger文档 |
| 🤖 **Gemini-Balance** | http://localhost:8000 | AI服务代理 |
| 📊 **Qdrant管理** | http://localhost:6333/dashboard | 向量数据库 |

### 默认账户

- **管理员用户**: admin
- **默认密码**: admin123
- **首次登录后请立即修改密码**

## ⚙️ 配置管理

### 🎛️ 统一配置管理

```bash
# 进入主部署目录
cd mem0-deployment

# 使用配置管理器
./scripts/config-manager.sh
```

### 🔧 主要配置项

#### AI服务配置
- **外部Gemini-Balance**: 使用独立部署的AI服务（推荐）
- **OpenAI模式**: 直接使用OpenAI API

> **注意**: 集成模式需要手动部署Gemini Balance服务，建议使用外部模式

#### 网络配置
- **端口设置**: 所有服务端口可自定义
- **域名配置**: 支持自定义域名
- **SSL配置**: 支持HTTPS部署

#### 数据库配置
- **PostgreSQL**: 用户数据和记忆存储
- **Qdrant**: 向量数据库
- **MySQL**: AI服务数据（可选）

## 🛠️ 服务管理

### 🚀 快速操作

```bash
# 启动完整系统
cd mem0-deployment
docker-compose up -d

# 查看所有服务状态
docker-compose ps

# 查看系统日志
docker-compose logs -f

# 停止系统
docker-compose down
```

### 📊 系统监控

```bash
# 使用快速启动器
cd mem0-deployment
./quick-start.sh

# 选择相应的监控选项
# 4) 查看服务状态
# 5) 查看服务日志
```

## 🔧 开发和定制

### 🎨 自定义Web界面

```bash
# 编辑Web界面
cd mem0Client
# 修改 web_app_full_cn.py

# 重新构建
cd ../mem0-deployment
docker-compose build mem0-webui
docker-compose up -d mem0-webui
```

### 🤖 自定义AI服务

```bash
# 配置Gemini-Balance
cd gemini-balance
# 编辑配置文件

# 重新部署
./deploy.sh
```

### 📝 API扩展

```bash
# 扩展Mem0 API
cd mem0-deployment/mem0
# 修改API代码

# 重新构建
cd ..
docker-compose build mem0-api
docker-compose up -d mem0-api
```

## 📚 详细文档

- [Mem0部署指南](mem0-deployment/README.md)
- [配置参考手册](mem0-deployment/docs/CONFIG_REFERENCE.md)
- [Mem0Client使用说明](mem0Client/README.md)
- [Gemini-Balance配置](gemini-balance/README.md)

## 🔍 故障排除

### 常见问题

1. **端口冲突**: 使用配置管理器修改端口
2. **AI服务连接失败**: 检查Gemini-Balance状态
3. **数据库连接问题**: 检查PostgreSQL和Qdrant状态

### 获取帮助

```bash
# 查看系统状态
cd mem0-deployment
./scripts/quick-start.sh

# 查看详细日志
docker-compose logs [service-name]

# 重置系统
docker-compose down -v
./install.sh
```

## 🤝 贡献

欢迎为这个项目贡献代码！

### 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢所有贡献者和用户的支持！

---

**🎉 这是一个完整的、生产就绪的智能记忆管理系统！**

如有任何问题，请查看相关文档或提交Issue。
