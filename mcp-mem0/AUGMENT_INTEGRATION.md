# MCP-mem0 与 Augment 集成指南

## 🎯 概述

MCP-mem0 现在完全支持 Augment AI IDE，提供强大的长期记忆功能，让你的编程助手能够记住和检索代码偏好、实现模式和技术知识。

## ✨ 功能特性

### 🔧 可用工具
- **`add_coding_preference`** - 存储代码片段、实现细节和编程模式
- **`get_all_coding_preferences`** - 获取所有存储的编程偏好
- **`search_coding_preferences`** - 语义搜索相关的代码和知识

### 🚀 核心优势
- **持久化记忆** - 跨会话保存编程知识
- **语义搜索** - 自然语言查询相关代码
- **用户隔离** - 每个用户独立的记忆空间
- **Docker化部署** - 简单可靠的容器化运行
- **本地部署** - 数据完全可控，无隐私担忧

## 📋 前置要求

1. **Docker** - 用于运行MCP-mem0服务
2. **Mem0 API** - 本地部署的记忆存储后端
3. **Augment IDE** - 支持MCP协议的AI编程环境

## 🛠️ 安装步骤

### 1. 确保Mem0 API运行
```bash
# 检查Mem0 API是否可用
curl http://localhost:8888/memories?user_id=test
```

### 2. 构建MCP-mem0镜像
```bash
cd mem0-complete-system/mcp-mem0
docker build -t mcp-mem0-augment .
```

### 3. 运行配置脚本
```bash
./start-for-augment.sh [your_user_id]
```

## ⚙️ Augment 配置

将以下配置添加到你的 Augment MCP 设置中：

```json
{
  "mcpServers": {
    "mem0-coding-preferences": {
      "command": "docker",
      "args": [
        "run", 
        "--rm", 
        "-i", 
        "--network", "host",
        "mcp-mem0-augment"
      ],
      "env": {
        "TRANSPORT": "stdio",
        "DEFAULT_USER_ID": "your_user_id",
        "MEM0_API_URL": "http://localhost:8888"
      }
    }
  }
}
```

### 配置参数说明
- **`DEFAULT_USER_ID`** - 你的用户标识符，用于记忆隔离
- **`MEM0_API_URL`** - Mem0 API服务地址
- **`TRANSPORT`** - 传输模式，Augment使用 `stdio`

## 🎮 使用示例

### 添加编程知识
```
请帮我记住这个Python装饰器模式的实现...
```

### 搜索相关代码
```
我之前是怎么实现API错误处理的？
```

### 获取所有记忆
```
显示我所有存储的编程偏好和代码片段
```

## 🔧 高级配置

### 自定义用户ID
```bash
./start-for-augment.sh "alice_dev"
```

### 自定义Mem0 API地址
```bash
export MEM0_API_URL="http://your-mem0-server:8888"
./start-for-augment.sh
```

### 使用不同的Docker镜像
```bash
export DOCKER_IMAGE="your-custom-mcp-mem0"
./start-for-augment.sh
```

## 🐛 故障排除

### 常见问题

1. **连接失败**
   - 检查Mem0 API是否运行: `curl http://localhost:8888/memories?user_id=test`
   - 确认Docker网络配置正确

2. **工具不可用**
   - 重启Augment IDE
   - 检查MCP配置格式是否正确
   - 查看Docker容器日志

3. **记忆不持久**
   - 确认用户ID一致
   - 检查Mem0数据库连接

### 调试命令
```bash
# 测试Docker镜像
docker run --rm -it mcp-mem0-augment python main.py --help

# 查看容器日志
docker logs <container_id>

# 测试API连接
curl -X GET "http://localhost:8888/memories?user_id=test"
```

## 🎉 完成！

配置完成后，重启Augment IDE，你就可以开始使用强大的长期记忆功能了！

MCP-mem0 将帮助你的AI助手记住：
- 代码实现模式
- 最佳实践
- 项目配置
- 技术决策
- 学习笔记

让编程变得更加智能和高效！ 🚀
