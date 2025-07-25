# Mem0 新环境安装指南

## 🎯 **专为全新电脑环境设计**

如果您在**全新、干净的电脑**上安装Mem0系统，请使用本指南中的专用脚本，而不是通用的 `install.sh`。

## 🚨 **新环境 vs 已有环境的区别**

### **新环境特点**：
- 全新的Docker环境
- 没有任何残留的容器、网络、数据卷
- PostgreSQL需要完整初始化
- 网络配置需要从零开始

### **已有环境特点**：
- 可能有残留的Docker资源
- PostgreSQL可能跳过初始化
- 网络配置可能有冲突

## 🚀 **新环境安装方法**

### **方法1: 使用新环境专用安装脚本（推荐）**

```bash
# 克隆仓库
git clone https://github.com/erniulure/mem0-complete-system.git
cd mem0-complete-system

# 使用新环境专用安装脚本
./install-new-env.sh

# 或自动安装
./install-new-env.sh --auto
```

### **方法2: 如果安装失败，使用修复脚本**

```bash
# 如果安装过程中遇到问题，运行修复脚本
sudo ./fix-new-environment.sh
```

## 🔧 **新环境脚本的特点**

### **install-new-env.sh 特点**：
- ✅ 专为新环境设计
- ✅ 按正确顺序安装服务
- ✅ 自动创建环境配置文件
- ✅ 强制初始化数据库
- ✅ 等待服务完全启动
- ✅ 验证安装结果

### **fix-new-environment.sh 特点**：
- ✅ 完全清理环境
- ✅ 强制重新初始化数据库
- ✅ 修复网络配置
- ✅ 修复环境变量
- ✅ 重新启动所有服务

## 🐛 **常见新环境问题及解决方案**

### **问题1: WebUI数据库连接失败**
```
ConnectionError: WebUI独立数据库不可用
```

**解决方案**：
```bash
sudo ./fix-new-environment.sh
```

### **问题2: 服务间网络连接异常**
```
[WARNING] WebUI ↔ Gemini Balance 连接异常
[WARNING] WebUI ↔ Mem0 API 连接异常
```

**解决方案**：
```bash
# 检查网络配置
docker network ls
docker network inspect mem0-unified-network

# 如果有问题，运行修复脚本
sudo ./fix-new-environment.sh
```

### **问题3: PostgreSQL初始化跳过**
```
PostgreSQL Database directory appears to contain a database; Skipping initialization
```

**解决方案**：
```bash
# 强制重新初始化
sudo ./fix-new-environment.sh
```

## 📊 **安装验证**

安装完成后，检查以下服务：

```bash
# 检查容器状态
docker ps

# 检查服务响应
curl http://localhost:8503  # WebUI
curl http://localhost:8888  # Mem0 API
curl http://localhost:8000  # Gemini Balance

# 检查数据库
docker exec mem0-postgres psql -U mem0 -d webui -c "\dt"
```

## 🌐 **访问地址**

安装成功后，您可以访问：

- **🌐 WebUI**: http://localhost:8503
- **🔌 Mem0 API**: http://localhost:8888
- **🤖 Gemini Balance**: http://localhost:8000
- **📊 Neo4j Browser**: http://localhost:7474 (neo4j/password)
- **🔍 Qdrant**: http://localhost:6333

## 🆘 **故障排除**

### **如果所有方法都失败**：

1. **完全清理环境**：
   ```bash
   sudo ./fix-new-environment.sh
   ```

2. **手动清理**：
   ```bash
   # 停止所有容器
   docker stop $(docker ps -aq)
   
   # 删除所有容器
   docker rm $(docker ps -aq)
   
   # 删除所有数据卷
   docker volume prune -f
   
   # 删除所有网络
   docker network prune -f
   
   # 重新安装
   ./install-new-env.sh --auto
   ```

3. **查看详细日志**：
   ```bash
   # 查看特定容器日志
   docker logs mem0-webui
   docker logs mem0-postgres
   docker logs gemini-balance
   ```

## 📝 **与通用安装脚本的区别**

| 特性 | install.sh (通用) | install-new-env.sh (新环境) |
|------|------------------|---------------------------|
| 环境检测 | 复杂的环境检测 | 简化的新环境检测 |
| 数据库初始化 | 可能跳过初始化 | 强制完整初始化 |
| 网络配置 | 复杂的网络管理 | 简单的统一网络 |
| 服务启动 | 并行启动 | 顺序启动，等待完成 |
| 错误处理 | 复杂的错误恢复 | 简单的错误提示 |
| 适用场景 | 各种环境 | 仅新环境 |

## 🎯 **推荐使用场景**

### **使用 install-new-env.sh 当**：
- ✅ 全新安装的电脑
- ✅ 从未安装过Docker容器
- ✅ 没有任何Mem0相关的残留文件
- ✅ 希望简单、直接的安装过程

### **使用 install.sh 当**：
- ✅ 已有Docker环境
- ✅ 需要升级现有安装
- ✅ 有特殊的网络配置需求
- ✅ 需要自定义安装选项

---

**🎉 希望这个新环境专用安装脚本能帮您在全新电脑上顺利部署Mem0系统！**
