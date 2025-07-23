# 🧠 Mem0 记忆管理系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)

一个基于AI的智能记忆管理系统，支持多用户、多模态内容处理和智能对话功能。包含完整的Mem0 API部署和Web界面。

## ✨ 主要特性

### 🔐 用户认证与多用户支持
- **安全登录系统** - 密码哈希加密存储
- **多用户数据隔离** - 每个用户独立的记忆空间
- **管理员功能** - 用户管理、密码重置、系统监控
- **会话管理** - 自动过期和安全登出

### 🧠 智能记忆管理
- **AI对话学习** - 通过对话自动学习和记忆用户偏好
- **多模态支持** - 文本、图片、文档等多种格式
- **智能搜索** - 基于语义的智能记忆检索
- **标签分类** - 自动标签生成和分类管理

### 🎨 现代化界面
- **响应式设计** - 适配各种屏幕尺寸
- **实时更新** - 记忆统计和状态实时显示
- **多标签页** - 智能对话、数据分析、记忆管理等
- **可视化图表** - 记忆趋势和统计分析

### 🐳 完整Docker部署
- **Mem0 API服务** - 完整的记忆管理API
- **PostgreSQL数据库** - 持久化数据存储
- **Qdrant向量数据库** - 高性能向量搜索
- **Redis缓存** - 提升系统性能
- **Nginx反向代理** - 生产级负载均衡

### 🛠️ 系统管理
- **一键安装** - 支持Ubuntu/Debian/CentOS等主流Linux发行版
- **服务管理** - systemd服务集成，开机自启
- **备份恢复** - 完整的数据备份和恢复功能
- **日志监控** - 详细的系统日志和状态监控

## 🚀 快速开始

### 系统要求

- **操作系统**: Ubuntu 18.04+, Debian 10+, CentOS 7+, RHEL 7+
- **Python**: 3.8+
- **Docker**: 20.10+
- **内存**: 最少4GB RAM
- **磁盘**: 最少10GB可用空间

### 一键安装

```bash
# 下载项目
git clone https://github.com/your-username/mem0-memory-system.git
cd mem0-memory-system

# 配置API密钥
cp .env.example .env
# 编辑 .env 文件，至少配置一个AI API密钥 (OpenAI/Anthropic/Google)

# 运行一键安装脚本
sudo chmod +x install.sh
sudo ./install.sh
```

安装脚本会自动：
- 安装Docker和系统依赖
- 部署Mem0 API服务 (PostgreSQL + Qdrant + Redis)
- 配置Web界面和用户认证
- 设置systemd服务和防火墙
- 启动所有服务

安装完成后，访问 `http://your-server-ip:8503` 即可使用Web界面。

### 默认账户

- **用户名**: `admin`
- **密码**: `admin123`

⚠️ **重要**: 首次登录后请立即修改默认密码！

## 📖 使用指南

### Web界面功能

1. **🧠 智能对话** - 与AI助手对话，系统自动学习记忆
2. **📊 数据分析** - 查看记忆统计和趋势分析
3. **📝 记忆管理** - 浏览、编辑、删除记忆内容
4. **🔍 记忆搜索** - 智能搜索和过滤记忆
5. **⚙️ 系统设置** - 配置API、用户设置等

### 管理命令

```bash
# 进入项目目录
cd /opt/mem0Client

# 服务管理
sudo ./manage.sh start      # 启动服务
sudo ./manage.sh stop       # 停止服务
sudo ./manage.sh restart    # 重启服务
sudo ./manage.sh status     # 查看状态

# 日志查看
sudo ./manage.sh logs       # 查看Web界面日志
sudo ./manage.sh api-logs   # 查看API日志

# Docker管理
sudo ./manage.sh docker up      # 启动Docker容器
sudo ./manage.sh docker down    # 停止Docker容器
sudo ./manage.sh docker logs    # 查看Docker日志
sudo ./manage.sh docker ps      # 查看容器状态

# 备份恢复
sudo ./manage.sh backup     # 备份系统
sudo ./manage.sh restore    # 恢复系统

# 系统更新
sudo ./manage.sh update     # 更新依赖
```

## 🏗️ 架构说明

### 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx (80)    │    │  Web UI (8503)  │    │  Mem0 API       │
│   反向代理       │────│  Streamlit界面   │────│  (8888)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │ PostgreSQL      │    │   Qdrant        │
                       │ (5432)          │────│   (6333)        │
                       │ 关系数据库       │    │   向量数据库     │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                              ┌─────────────────┐
                                              │   Redis         │
                                              │   (6379)        │
                                              │   缓存          │
                                              └─────────────────┘
```

### 核心组件

```
mem0Client/
├── web_app_full_cn.py          # 主Web应用
├── auth_system.py              # 用户认证系统
├── api_patches.py              # 安全补丁
├── modern_chat_interface.py    # 聊天界面
├── multimodal_model_selector.py # 模型选择器
├── core/                       # 核心功能模块
├── docker-compose.yml          # Docker编排文件
├── .env.example               # 环境变量模板
├── config/                    # 配置文件目录
├── scripts/                   # 系统服务文件
├── install.sh                 # 一键安装脚本
├── manage.sh                  # 管理脚本
└── requirements.txt           # Python依赖
```

### 安全特性

- **密码加密**: PBKDF2哈希算法
- **会话管理**: 自动过期和安全令牌
- **数据隔离**: 用户间完全隔离
- **输入验证**: 防止恶意输入
- **审计日志**: 完整的操作记录
- **网络隔离**: Docker网络安全

## 🔧 配置说明

### 环境变量配置 (.env)

```bash
# AI API密钥 (至少配置一个)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# 数据库配置
POSTGRES_URL=postgresql://mem0:mem0password@localhost:5432/mem0db
QDRANT_URL=http://localhost:6333

# 认证配置
MEM0_SECRET_KEY=your_secret_key_change_in_production
MEM0_ADMIN_USER=admin
MEM0_ADMIN_PASS=admin123
```

### Docker服务配置

```yaml
# docker-compose.yml 主要服务
services:
  mem0-api:      # Mem0 API服务
  postgres:      # PostgreSQL数据库
  qdrant:        # Qdrant向量数据库
  redis:         # Redis缓存
  nginx:         # Nginx反向代理
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持与反馈

- **问题报告**: [GitHub Issues](https://github.com/your-username/mem0-memory-system/issues)
- **功能请求**: [GitHub Discussions](https://github.com/your-username/mem0-memory-system/discussions)
- **文档**: [Wiki](https://github.com/your-username/mem0-memory-system/wiki)

## 📊 项目状态

- ✅ 用户认证系统
- ✅ 多用户数据隔离  
- ✅ 智能对话功能
- ✅ 记忆管理界面
- ✅ Docker完整部署
- ✅ 系统管理工具
- 🔄 API文档完善
- 🔄 Kubernetes支持
- 📋 移动端适配

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**
