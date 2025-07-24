#!/bin/bash

# =============================================================================
# Gemini Balance 一键部署脚本
# 支持Docker Compose和本地Python两种部署方式
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        log_info "请使用: sudo $0"
        exit 1
    fi
}

# 检测操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS $VER"
}

# 安装Docker
install_docker() {
    log_info "检查Docker安装状态..."
    
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        log_success "Docker已安装"
        return 0
    fi
    
    log_info "安装Docker和Docker Compose..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt update
        apt install -y docker.io docker-compose curl wget
        systemctl enable docker
        systemctl start docker
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum update -y
        yum install -y docker docker-compose curl wget
        systemctl enable docker
        systemctl start docker
    else
        log_warning "未知的操作系统，请手动安装Docker"
        exit 1
    fi
    
    log_success "Docker安装完成"
}

# 测试Gemini API密钥
test_gemini_key() {
    local api_key="$1"
    
    log_info "测试Gemini API密钥..."
    
    response=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Content-Type: application/json" \
        -d '{
            "contents": [{
                "parts": [{"text": "Hello"}]
            }]
        }' \
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$api_key")
    
    if [[ "$response" == "200" ]]; then
        log_success "Gemini API密钥测试通过"
        return 0
    else
        log_warning "Gemini API密钥测试失败 (HTTP: $response)"
        return 1
    fi
}

# 交互式配置
configure_environment() {
    log_info "配置Gemini Balance环境..."
    echo ""
    echo "=============================================="
    echo "🔑 Gemini Balance 配置向导"
    echo "=============================================="
    echo ""

    # 复制环境变量模板
    if [[ ! -f ".env" ]]; then
        cp .env.example .env
        log_info "已创建.env配置文件"
    fi

    # 检查是否为自动模式
    if [[ "$1" == "--auto" ]]; then
        echo "🤖 自动配置模式：使用默认配置"
        # 使用默认的API密钥（从.env.example中读取）
        gemini_keys="AIzaSyAs5vgmd12k9PF-YU0gvGY-RLjghNE3GrU,AIzaSyATXrWRFU12Qvn_eojERncPSjH0uyEH0oY,AIzaSyC6q7WEX67hRyGUKgwjmFDhU6Pw1oMSuz0,AIzaSyAdMxw-wmI5tI-Op6GcRse4j1nyzReaghA,AIzaSyAfo1AB90HgKSiV4-a_BwTK26-6BhTg5FE,AIzaSyAov2ZscN1AAD3z0uJ-vIgdO6ZsypPudTU,AIzaSyDmsx8yjQHUKgUOw05WGyQkQTmXgBYUWWA,AIzaSyBkE06pIm18ZbNJQVzBuXCx5pf5h2MLC3w,AIzaSyBPSalsP7fkIPme1N_ROCs7LGky4b0bEGw,AIzaSyDCoBo5cWzJvw_WXwBnz0Foq9mr76nXen8"
        access_token="q1q2q3q4"
    else
        # 配置Gemini API密钥
        echo "--- Gemini API密钥配置 ---"
        echo "请输入你的Gemini API密钥（多个密钥用逗号分隔）:"
        read -p "Gemini API Keys: " gemini_keys
    fi
    
    if [[ -n "$gemini_keys" ]]; then
        # 转换为JSON数组格式
        IFS=',' read -ra KEYS <<< "$gemini_keys"
        json_keys="["
        for i in "${!KEYS[@]}"; do
            key=$(echo "${KEYS[$i]}" | xargs) # 去除空格
            if [[ $i -gt 0 ]]; then
                json_keys+=","
            fi
            json_keys+="\"$key\""

            # 测试每个密钥（自动模式跳过测试）
            if [[ "$1" == "--auto" ]]; then
                log_info "自动模式：跳过密钥 ${key:0:10}... 的验证"
            elif test_gemini_key "$key"; then
                log_success "密钥 ${key:0:10}... 验证通过"
            else
                log_warning "密钥 ${key:0:10}... 验证失败"
            fi
        done
        json_keys+="]"
        
        # 更新.env文件
        sed -i "s/API_KEYS=.*/API_KEYS=$json_keys/" .env
        log_success "API密钥配置完成"
    fi
    
    # 配置访问令牌
    if [[ "$1" != "--auto" ]]; then
        echo ""
        echo "--- 访问令牌配置 ---"
        read -p "请输入访问令牌 (默认: q1q2q3q4): " access_token
        access_token=${access_token:-q1q2q3q4}
    fi
    
    sed -i "s/ALLOWED_TOKENS=.*/ALLOWED_TOKENS=[\"$access_token\"]/" .env
    sed -i "s/AUTH_TOKEN=.*/AUTH_TOKEN=$access_token/" .env
    
    # 配置数据库类型
    echo ""
    echo "--- 数据库配置 ---"
    echo "本系统使用MySQL数据库（生产级配置）"
    # 强制使用MySQL，因为docker-compose.yml只支持MySQL
    sed -i "s/DATABASE_TYPE=.*/DATABASE_TYPE=mysql/" .env

    # 确保MySQL配置存在
    if ! grep -q "MYSQL_HOST" .env; then
        echo "MYSQL_HOST=mysql" >> .env
    else
        sed -i "s/MYSQL_HOST=.*/MYSQL_HOST=mysql/" .env
    fi

    if ! grep -q "MYSQL_PORT" .env; then
        echo "MYSQL_PORT=3306" >> .env
    else
        sed -i "s/MYSQL_PORT=.*/MYSQL_PORT=3306/" .env
    fi

    if ! grep -q "MYSQL_USER" .env; then
        echo "MYSQL_USER=gemini" >> .env
    else
        sed -i "s/MYSQL_USER=.*/MYSQL_USER=gemini/" .env
    fi

    if ! grep -q "MYSQL_PASSWORD" .env; then
        echo "MYSQL_PASSWORD=change_me" >> .env
    else
        sed -i "s/MYSQL_PASSWORD=.*/MYSQL_PASSWORD=change_me/" .env
    fi

    if ! grep -q "MYSQL_DATABASE" .env; then
        echo "MYSQL_DATABASE=default_db" >> .env
    else
        sed -i "s/MYSQL_DATABASE=.*/MYSQL_DATABASE=default_db/" .env
    fi

    log_info "已配置MySQL数据库连接参数"
    
    echo "=============================================="
    log_success "环境配置完成"
}

# Docker部署
deploy_with_docker() {
    log_info "使用Docker Compose部署..."
    
    # 创建完整的docker-compose.yml
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  gemini-balance:
    image: ghcr.io/snailyp/gemini-balance:latest
    container_name: gemini-balance
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      # 确保MySQL配置正确传递
      - DATABASE_TYPE=mysql
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=gemini
      - MYSQL_PASSWORD=change_me
      - MYSQL_DATABASE=default_db
    volumes:
      - ./data:/app/data
    depends_on:
      mysql:
        condition: service_healthy
    networks:
      - gemini-network
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import requests; exit(0) if requests.get('http://localhost:8000/health').status_code == 200 else exit(1)\""]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s

  mysql:
    image: mysql:8.0
    container_name: gemini-balance-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: default_db
      MYSQL_USER: gemini
      MYSQL_PASSWORD: change_me
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    networks:
      - gemini-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

networks:
  gemini-network:
    driver: bridge

volumes:
  mysql_data:
    driver: local
EOF
    
    # 创建数据目录
    mkdir -p data
    
    # 启动服务
    log_info "启动Docker容器..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    if curl -f http://localhost:8000/health &>/dev/null; then
        log_success "Gemini Balance服务启动成功"
    else
        log_warning "服务可能未完全启动，请检查Docker日志"
        log_info "使用命令查看日志: docker-compose logs -f"
    fi
}

# 本地Python部署
deploy_with_python() {
    log_info "使用Python本地部署..."
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python 3.9+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "检测到Python版本: $python_version"
    
    # 安装依赖
    log_info "安装Python依赖..."
    pip3 install -r requirements.txt
    
    # 启动服务
    log_info "启动Gemini Balance服务..."
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > gemini-balance.log 2>&1 &
    echo $! > gemini-balance.pid
    
    sleep 5
    
    if curl -f http://localhost:8000/health &>/dev/null; then
        log_success "Gemini Balance服务启动成功"
        log_info "PID: $(cat gemini-balance.pid)"
        log_info "日志文件: gemini-balance.log"
    else
        log_error "服务启动失败，请检查日志"
        exit 1
    fi
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 8000/tcp
        log_success "UFW防火墙规则已添加"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8000/tcp
        firewall-cmd --reload
        log_success "firewalld防火墙规则已添加"
    else
        log_warning "未检测到防火墙，请手动开放端口8000"
    fi
}

# 显示完成信息
show_completion_info() {
    echo ""
    echo "=============================================="
    log_success "Gemini Balance 部署完成！"
    echo "=============================================="
    echo ""
    echo "🌐 访问地址:"
    echo "   http://$(hostname -I | awk '{print $1}'):8000"
    echo "   http://localhost:8000"
    echo ""
    echo "🔑 API端点:"
    echo "   OpenAI格式: http://localhost:8000/v1"
    echo "   Gemini格式: http://localhost:8000/v1beta"
    echo ""
    echo "📊 管理界面:"
    echo "   状态监控: http://localhost:8000/keys_status"
    echo "   API文档: http://localhost:8000/docs"
    echo ""
    echo "🛠️  管理命令:"
    if [[ "$DEPLOY_METHOD" == "docker" ]]; then
        echo "   查看状态: docker-compose ps"
        echo "   查看日志: docker-compose logs -f"
        echo "   停止服务: docker-compose down"
        echo "   重启服务: docker-compose restart"
    else
        echo "   查看状态: ps aux | grep uvicorn"
        echo "   查看日志: tail -f gemini-balance.log"
        echo "   停止服务: kill \$(cat gemini-balance.pid)"
    fi
    echo ""
    echo "⚠️  重要提醒:"
    echo "   请妥善保管你的API密钥和访问令牌"
    echo "   生产环境建议使用HTTPS和更强的认证"
    echo ""
    echo "=============================================="
}

# 主菜单
show_menu() {
    echo ""
    echo "=============================================="
    echo "🧠 Gemini Balance 部署脚本"
    echo "=============================================="

    # 检查是否为自动模式
    if [[ "$1" == "--auto" ]]; then
        echo "🤖 自动部署模式：使用Docker Compose部署"
        choice=1
    else
        echo "请选择部署方式:"
        echo "1) Docker Compose部署 (推荐)"
        echo "2) Python本地部署"
        echo "3) 退出"
        echo ""
        read -p "请选择 (1-3): " choice
    fi
    
    case $choice in
        1)
            DEPLOY_METHOD="docker"
            check_root
            detect_os
            install_docker
            if [[ "$1" == "--auto" ]]; then
                configure_environment --auto
            else
                configure_environment
            fi
            deploy_with_docker
            setup_firewall
            show_completion_info
            ;;
        2)
            DEPLOY_METHOD="python"
            if [[ "$1" == "--auto" ]]; then
                configure_environment --auto
            else
                configure_environment
            fi
            deploy_with_python
            show_completion_info
            ;;
        3)
            log_info "退出部署"
            exit 0
            ;;
        *)
            log_error "无效选择"
            show_menu
            ;;
    esac
}

# 主函数
main() {
    show_menu "$@"
}

# 执行主函数
main "$@"
