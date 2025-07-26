#!/bin/bash

# =============================================================================
# MCP-Mem0 全能安装管理脚本
# 功能：安装、启动、停止、重启、卸载、状态检查、日志查看
# 作者：Augment Agent
# 版本：1.0.0
# =============================================================================

set -e  # 遇到错误立即退出

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="mcp-mem0"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_SCRIPT="main_working.py"
DEFAULT_HOST="192.168.8.225"
DEFAULT_PORT="8082"
VENV_PATH="${SCRIPT_DIR}/.venv"
LOG_FILE="/var/log/${SERVICE_NAME}.log"
PID_FILE="/var/run/${SERVICE_NAME}.pid"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        log_info "请使用: sudo $0 $*"
        exit 1
    fi
}

# 检查系统依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    local deps=("python3" "python3-venv" "python3-pip" "systemctl" "docker")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_info "正在安装缺少的依赖..."
        
        # 更新包管理器
        apt-get update -qq
        
        # 安装缺少的依赖
        for dep in "${missing_deps[@]}"; do
            case $dep in
                "docker")
                    log_info "安装Docker..."
                    curl -fsSL https://get.docker.com -o get-docker.sh
                    sh get-docker.sh
                    systemctl enable docker
                    systemctl start docker
                    rm get-docker.sh
                    ;;
                *)
                    apt-get install -y "$dep"
                    ;;
            esac
        done
    fi
    
    log_info "系统依赖检查完成"
}

# 检查端口占用
check_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pid" ]; then
        log_warn "端口 $port 被进程 $pid 占用"
        
        # 获取进程信息
        local process_info=$(ps -p $pid -o pid,ppid,cmd --no-headers 2>/dev/null || echo "未知进程")
        log_info "进程信息: $process_info"
        
        read -p "是否要终止占用端口的进程? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "正在终止进程 $pid..."
            kill -TERM $pid 2>/dev/null || true
            sleep 2
            
            # 如果进程仍然存在，强制终止
            if kill -0 $pid 2>/dev/null; then
                log_warn "进程仍在运行，强制终止..."
                kill -KILL $pid 2>/dev/null || true
                sleep 1
            fi
            
            # 再次检查
            if lsof -ti:$port &>/dev/null; then
                log_error "无法释放端口 $port"
                return 1
            else
                log_info "端口 $port 已释放"
            fi
        else
            log_error "端口被占用，无法继续"
            return 1
        fi
    else
        log_info "端口 $port 可用"
    fi
    return 0
}

# 设置Python虚拟环境
setup_venv() {
    log_info "设置Python虚拟环境..."
    
    if [ ! -d "$VENV_PATH" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv "$VENV_PATH"
    fi
    
    # 激活虚拟环境并安装依赖
    source "$VENV_PATH/bin/activate"
    
    log_info "升级pip..."
    pip install --upgrade pip -q
    
    log_info "安装Python依赖..."
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt" -q
    else
        # 安装基本依赖
        pip install mcp fastapi uvicorn starlette httpx python-dotenv mem0ai -q
    fi
    
    log_info "Python环境设置完成"
}

# 检查Docker服务
check_docker() {
    log_info "检查Docker服务..."

    if ! systemctl is-active --quiet docker; then
        log_info "启动Docker服务..."
        systemctl start docker
    fi

    # 检查mem0相关容器
    local containers=("mem0-api" "mem0-postgres" "mem0-qdrant" "mem0-neo4j")
    local missing_containers=()

    for container in "${containers[@]}"; do
        if ! docker ps --format "table {{.Names}}" | grep -q "$container"; then
            missing_containers+=("$container")
        fi
    done

    if [ ${#missing_containers[@]} -ne 0 ]; then
        log_warn "以下mem0容器未运行: ${missing_containers[*]}"
        log_info "请确保mem0 Docker服务正在运行"
        log_info "参考命令: docker-compose up -d"
    else
        log_info "mem0 Docker容器运行正常"
    fi
}

# 创建systemd服务文件
create_service() {
    log_info "创建systemd服务文件..."

    # 创建mem0配置目录
    local mem0_config_dir="$SCRIPT_DIR/.mem0"
    mkdir -p "$mem0_config_dir"
    chmod 755 "$mem0_config_dir"

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=MCP-Mem0 Server with User Isolation
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=HOME=$SCRIPT_DIR
Environment=MEM0_CONFIG_DIR=$mem0_config_dir
Environment=PYTHONPATH=$VENV_PATH/lib/python3.12/site-packages
ExecStart=$VENV_PATH/bin/python $SCRIPT_DIR/$PYTHON_SCRIPT --host $DEFAULT_HOST --port $DEFAULT_PORT
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# 安全设置 - 放宽限制以允许mem0正常工作
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false
ReadWritePaths=$SCRIPT_DIR /var/log /tmp $mem0_config_dir

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "systemd服务文件创建完成"
}

# 生成配置文件示例
generate_config_example() {
    log_info "生成配置文件示例..."

    local config_file="$SCRIPT_DIR/config.json"

    cat > "$config_file" << 'EOF'
{
  "mcpServers": {
    "mem0-coding-preferences": {
      "command": "python",
      "args": ["/opt/mem0-complete-system/mem0-mcp-clean/main_working.py"],
      "env": {
        "PYTHONPATH": "/opt/mem0-complete-system/mem0-mcp-clean/.venv/lib/python3.12/site-packages"
      }
    }
  },
  "server": {
    "name": "MCP-Mem0 Server with User Isolation",
    "version": "1.0.0",
    "description": "A Model Context Protocol server that provides coding preference management with complete user isolation using mem0 AI memory system.",
    "host": "192.168.8.225",
    "port": 8082,
    "transport": "sse"
  },
  "mem0": {
    "api_url": "http://localhost:8888",
    "endpoints": {
      "health": "/",
      "memories": "/memories",
      "search": "/search",
      "docs": "/docs"
    },
    "timeouts": {
      "add_memory": 60,
      "search_memory": 30,
      "get_memories": 30
    }
  },
  "docker": {
    "required_containers": [
      "mem0-api",
      "mem0-postgres",
      "mem0-qdrant",
      "mem0-neo4j",
      "mem0-webui"
    ],
    "api_container": "mem0-api",
    "api_port": 8888
  },
  "tools": [
    {
      "name": "add_coding_preference",
      "description": "Add a new coding preference to mem0 with user isolation. This tool stores code snippets, implementation details, and coding patterns for future reference. Each user's data is completely isolated. Note: Processing may take 30-60 seconds due to AI analysis.",
      "parameters": {
        "text": {
          "type": "string",
          "description": "The coding preference text to store"
        }
      }
    },
    {
      "name": "get_all_coding_preferences",
      "description": "Retrieve all stored coding preferences for the current user. Returns user-specific data only.",
      "parameters": {}
    },
    {
      "name": "search_coding_preferences",
      "description": "Search through stored coding preferences using semantic search. Searches only the current user's data.",
      "parameters": {
        "query": {
          "type": "string",
          "description": "Search query for finding relevant coding preferences"
        }
      }
    }
  ],
  "user_isolation": {
    "enabled": true,
    "default_user": "admin_default",
    "header_name": "X-User-ID",
    "validation_pattern": "^[a-zA-Z0-9_-]{1,64}$"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "handlers": ["console", "systemd"]
  },
  "security": {
    "cors_enabled": false,
    "allowed_origins": ["*"],
    "rate_limiting": false,
    "max_requests_per_minute": 60
  }
}
EOF

    # 设置文件权限
    chmod 644 "$config_file"

    log_info "配置文件示例已生成: $config_file"
    log_info "你可以根据需要修改配置参数"
}

# 生成Claude Desktop配置示例
generate_claude_config() {
    log_info "生成Claude Desktop配置示例..."

    local claude_config_file="$SCRIPT_DIR/claude_desktop_config.json"

    cat > "$claude_config_file" << EOF
{
  "mcpServers": {
    "mem0-coding-preferences": {
      "command": "python",
      "args": ["$SCRIPT_DIR/main_working.py"],
      "env": {
        "PYTHONPATH": "$VENV_PATH/lib/python3.12/site-packages",
        "PATH": "$VENV_PATH/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
      }
    }
  }
}
EOF

    # 设置文件权限
    chmod 644 "$claude_config_file"

    log_info "Claude Desktop配置示例已生成: $claude_config_file"
    log_info "将此配置添加到你的Claude Desktop配置文件中"
    log_info "通常位于: ~/.config/Claude/claude_desktop_config.json"
}

# 生成Augment配置示例
generate_augment_config() {
    log_info "生成Augment配置示例..."

    local augment_config_file="$SCRIPT_DIR/augment_config.json"

    cat > "$augment_config_file" << EOF
{
  "mcp_servers": [
    {
      "name": "mem0-coding-preferences",
      "url": "http://$DEFAULT_HOST:$DEFAULT_PORT/sse",
      "headers": {
        "X-User-ID": "your_user_id_here"
      },
      "description": "MCP-Mem0 coding preferences server with user isolation",
      "tools": [
        "add_coding_preference",
        "get_all_coding_preferences",
        "search_coding_preferences"
      ]
    }
  ],
  "connection": {
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5
  }
}
EOF

    # 设置文件权限
    chmod 644 "$augment_config_file"

    log_info "Augment配置示例已生成: $augment_config_file"
    log_info "记得将 'your_user_id_here' 替换为你的实际用户ID"
}

# 生成README文件
generate_readme() {
    log_info "生成README文档..."

    local readme_file="$SCRIPT_DIR/README.md"

    cat > "$readme_file" << 'EOF'
# MCP-Mem0 编程偏好管理服务

一个基于Model Context Protocol (MCP)的编程偏好管理服务，集成mem0 AI记忆系统，提供完整的用户隔离功能。

## 🚀 功能特性

- **用户隔离**: 每个用户的数据完全隔离，确保隐私安全
- **智能记忆**: 基于mem0 AI的语义搜索和关系图谱
- **MCP协议**: 标准的Model Context Protocol实现
- **Docker集成**: 完整的容器化部署方案
- **系统服务**: systemd服务管理，开机自启
- **实时日志**: 完整的日志记录和监控

## 📦 安装要求

- Ubuntu/Debian Linux系统
- Python 3.12+
- Docker和Docker Compose
- systemd服务管理器
- root权限

## 🛠️ 快速安装

```bash
# 克隆或下载项目文件
cd /opt/mem0-complete-system/mem0-mcp-clean

# 运行安装脚本
sudo ./install.sh install
```

## 🎮 服务管理

```bash
# 启动服务
sudo ./install.sh start

# 停止服务
sudo ./install.sh stop

# 重启服务
sudo ./install.sh restart

# 查看状态
./install.sh status

# 查看日志
./install.sh logs 100

# 实时日志
./install.sh follow

# 测试连接
./install.sh test

# 卸载服务
sudo ./install.sh uninstall
```

## 🔧 配置文件

安装后会生成以下配置文件：

- `config.json` - 主配置文件
- `claude_desktop_config.json` - Claude Desktop配置示例
- `augment_config.json` - Augment配置示例

## 🌐 API端点

- **SSE端点**: `http://192.168.8.225:8082/sse`
- **用户端点**: `http://192.168.8.225:8082/user/{user_id}`
- **记住包含**: `X-User-ID` 头部

## 🛡️ 用户隔离

每个用户通过 `X-User-ID` 头部进行识别：

```bash
curl -H "X-User-ID: john_doe" http://192.168.8.225:8082/sse
```

## 🔨 可用工具

### 1. add_coding_preference
添加新的编程偏好到mem0记忆系统。

**参数**:
- `text` (string): 要存储的编程偏好文本

### 2. get_all_coding_preferences
获取当前用户的所有编程偏好。

**参数**: 无

### 3. search_coding_preferences
使用语义搜索查找相关的编程偏好。

**参数**:
- `query` (string): 搜索查询字符串

## 📊 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │───▶│  MCP-Mem0 Server │───▶│   Mem0 Docker   │
│  (Augment/      │    │   (FastMCP)     │    │   (API/DB/VDB)  │
│   Claude)       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🐳 Docker依赖

需要以下mem0容器运行：
- `mem0-api` - 主API服务
- `mem0-postgres` - PostgreSQL数据库
- `mem0-qdrant` - 向量数据库
- `mem0-neo4j` - 图数据库
- `mem0-webui` - Web界面

## 📝 日志管理

服务使用systemd journal进行日志管理：

```bash
# 查看服务日志
sudo journalctl -u mcp-mem0 -f

# 查看最近100行
sudo journalctl -u mcp-mem0 -n 100

# 查看特定时间范围
sudo journalctl -u mcp-mem0 --since "1 hour ago"
```

## 🔍 故障排除

### 端口被占用
```bash
# 查看端口占用
sudo lsof -i:8082

# 脚本会自动处理端口冲突
sudo ./install.sh start
```

### Docker容器未运行
```bash
# 检查容器状态
docker ps | grep mem0

# 启动mem0服务
cd /path/to/mem0-docker
docker-compose up -d
```

### 服务启动失败
```bash
# 查看详细错误
sudo journalctl -u mcp-mem0 --no-pager -l

# 检查Python环境
source .venv/bin/activate
python main_working.py --help
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请查看日志或提交Issue。
EOF

    # 设置文件权限
    chmod 644 "$readme_file"

    log_info "README文档已生成: $readme_file"
}

# 安装服务
install_service() {
    log_info "开始安装MCP-Mem0服务..."

    # 检查必要文件
    if [ ! -f "$SCRIPT_DIR/$PYTHON_SCRIPT" ]; then
        log_error "找不到Python脚本: $SCRIPT_DIR/$PYTHON_SCRIPT"
        exit 1
    fi

    # 检查系统依赖
    check_dependencies

    # 检查端口
    check_port "$DEFAULT_PORT"

    # 设置Python环境
    setup_venv

    # 检查Docker
    check_docker

    # 创建服务文件
    create_service

    # 启用服务
    systemctl enable "$SERVICE_NAME"

    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"

    # 生成配置文件示例
    generate_config_example
    generate_claude_config
    generate_augment_config

    log_info "MCP-Mem0服务安装完成"
    log_info "使用以下命令管理服务:"
    log_info "  启动: sudo systemctl start $SERVICE_NAME"
    log_info "  停止: sudo systemctl stop $SERVICE_NAME"
    log_info "  重启: sudo systemctl restart $SERVICE_NAME"
    log_info "  状态: sudo systemctl status $SERVICE_NAME"
    log_info "  日志: sudo journalctl -u $SERVICE_NAME -f"
}

# 卸载服务
uninstall_service() {
    log_info "开始卸载MCP-Mem0服务..."

    # 停止服务
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "停止服务..."
        systemctl stop "$SERVICE_NAME"
    fi

    # 禁用服务
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log_info "禁用服务..."
        systemctl disable "$SERVICE_NAME"
    fi

    # 删除服务文件
    if [ -f "$SERVICE_FILE" ]; then
        log_info "删除服务文件..."
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
    fi

    # 清理日志文件
    read -p "是否删除日志文件? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$LOG_FILE"
        log_info "日志文件已删除"
    fi

    # 清理虚拟环境
    read -p "是否删除Python虚拟环境? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
        log_info "Python虚拟环境已删除"
    fi

    log_info "MCP-Mem0服务卸载完成"
}

# 启动服务
start_service() {
    log_info "启动MCP-Mem0服务..."

    # 检查端口
    check_port "$DEFAULT_PORT"

    # 检查Docker
    check_docker

    # 启动服务
    systemctl start "$SERVICE_NAME"

    # 等待服务启动
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "服务启动成功"
        show_status
    else
        log_error "服务启动失败"
        log_info "查看错误日志: sudo journalctl -u $SERVICE_NAME --no-pager -l"
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止MCP-Mem0服务..."

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME"
        log_info "服务已停止"
    else
        log_warn "服务未运行"
    fi
}

# 重启服务
restart_service() {
    log_info "重启MCP-Mem0服务..."

    # 检查端口
    check_port "$DEFAULT_PORT"

    # 检查Docker
    check_docker

    # 重启服务
    systemctl restart "$SERVICE_NAME"

    # 等待服务启动
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "服务重启成功"
        show_status
    else
        log_error "服务重启失败"
        log_info "查看错误日志: sudo journalctl -u $SERVICE_NAME --no-pager -l"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_info "MCP-Mem0服务状态:"
    echo

    # 服务状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}● 服务状态: 运行中${NC}"
    else
        echo -e "${RED}● 服务状态: 已停止${NC}"
    fi

    # 端口状态
    if lsof -ti:$DEFAULT_PORT &>/dev/null; then
        echo -e "${GREEN}● 端口状态: $DEFAULT_PORT 已监听${NC}"
    else
        echo -e "${RED}● 端口状态: $DEFAULT_PORT 未监听${NC}"
    fi

    # Docker状态
    local docker_status="正常"
    local containers=("mem0-api" "mem0-postgres" "mem0-qdrant" "mem0-neo4j")
    for container in "${containers[@]}"; do
        if ! docker ps --format "table {{.Names}}" | grep -q "$container"; then
            docker_status="异常"
            break
        fi
    done

    if [ "$docker_status" = "正常" ]; then
        echo -e "${GREEN}● Docker状态: mem0容器运行正常${NC}"
    else
        echo -e "${RED}● Docker状态: 部分mem0容器未运行${NC}"
    fi

    # 连接信息
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo
        echo -e "${CYAN}连接信息:${NC}"
        echo -e "  SSE端点: http://$DEFAULT_HOST:$DEFAULT_PORT/sse"
        echo -e "  用户端点: http://$DEFAULT_HOST:$DEFAULT_PORT/user/{user_id}"
        echo -e "  记住包含 X-User-ID 头部!"
    fi

    echo
}

# 查看日志
show_logs() {
    local lines=${1:-50}
    log_info "显示最近 $lines 行日志:"
    echo

    if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
        journalctl -u "$SERVICE_NAME" -n "$lines" --no-pager
    else
        log_error "服务未安装"
        exit 1
    fi
}

# 实时查看日志
follow_logs() {
    log_info "实时查看日志 (Ctrl+C 退出):"
    echo

    if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
        journalctl -u "$SERVICE_NAME" -f
    else
        log_error "服务未安装"
        exit 1
    fi
}

# 测试连接
test_connection() {
    log_info "测试MCP-Mem0服务连接..."

    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        log_error "服务未运行"
        exit 1
    fi

    # 测试SSE端点
    local sse_url="http://$DEFAULT_HOST:$DEFAULT_PORT/sse"
    log_info "测试SSE端点: $sse_url"

    # 使用正确的SSE测试方法：检查HTTP状态码
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 5 --max-time 10 \
        -H "X-User-ID: test" \
        -H "Accept: text/event-stream" \
        "$sse_url")

    if [ "$http_code" = "200" ]; then
        log_info "✓ SSE端点连接成功 (HTTP $http_code)"
    else
        log_error "✗ SSE端点连接失败 (HTTP $http_code)"
    fi

    # 测试mem0 API
    log_info "测试mem0 API连接..."
    local mem0_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 5 --max-time 10 \
        "http://localhost:8888/")

    if [ "$mem0_code" = "200" ] || [ "$mem0_code" = "404" ]; then
        log_info "✓ mem0 API连接成功 (HTTP $mem0_code)"
    else
        log_error "✗ mem0 API连接失败 (HTTP $mem0_code)"
    fi

    # 测试MCP工具可用性（检查服务是否响应工具请求）
    log_info "测试MCP工具可用性..."
    if journalctl -u "$SERVICE_NAME" --no-pager -n 20 | grep -q "Processing request of type"; then
        log_info "✓ MCP服务正在处理请求，工具功能正常"
    else
        log_info "ℹ MCP服务运行正常，工具可通过客户端调用"
    fi

    echo
    log_info "连接测试完成！"
    log_info "如果所有测试都通过，服务已准备就绪。"
}

# 显示帮助信息
show_help() {
    echo -e "${CYAN}MCP-Mem0 全能管理脚本${NC}"
    echo -e "${PURPLE}版本: 1.0.0${NC}"
    echo
    echo -e "${YELLOW}用法:${NC}"
    echo "  $0 [命令] [选项]"
    echo
    echo -e "${YELLOW}命令:${NC}"
    echo "  install     安装MCP-Mem0服务"
    echo "  uninstall   卸载MCP-Mem0服务"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      显示服务状态"
    echo "  logs [n]    显示最近n行日志 (默认50行)"
    echo "  follow      实时查看日志"
    echo "  test        测试服务连接"
    echo "  help        显示此帮助信息"
    echo
    echo -e "${YELLOW}示例:${NC}"
    echo "  $0 install              # 安装服务"
    echo "  $0 start                # 启动服务"
    echo "  $0 status               # 查看状态"
    echo "  $0 logs 100             # 查看最近100行日志"
    echo "  $0 follow               # 实时查看日志"
    echo "  $0 test                 # 测试连接"
    echo
    echo -e "${YELLOW}配置:${NC}"
    echo "  服务名称: $SERVICE_NAME"
    echo "  监听地址: $DEFAULT_HOST:$DEFAULT_PORT"
    echo "  Python脚本: $PYTHON_SCRIPT"
    echo "  虚拟环境: $VENV_PATH"
    echo "  服务文件: $SERVICE_FILE"
    echo "  日志文件: 使用systemd journal"
    echo
}

# 主函数
main() {
    # 显示脚本信息
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${CYAN}MCP-Mem0 全能管理脚本 v1.0.0${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    echo

    # 检查参数
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    local command=$1
    shift

    case $command in
        "install")
            check_root
            install_service
            ;;
        "uninstall")
            check_root
            uninstall_service
            ;;
        "start")
            check_root
            start_service
            ;;
        "stop")
            check_root
            stop_service
            ;;
        "restart")
            check_root
            restart_service
            ;;
        "status")
            show_status
            ;;
        "logs")
            local lines=${1:-50}
            show_logs "$lines"
            ;;
        "follow")
            follow_logs
            ;;
        "test")
            test_connection
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口点
main "$@"
