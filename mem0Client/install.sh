#!/bin/bash

# =============================================================================
# Mem0 记忆管理系统 - 一键安装脚本
# 支持 Ubuntu/Debian/CentOS/RHEL 系统
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 安装系统依赖
install_dependencies() {
    log_info "安装系统依赖..."

    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        apt update
        apt install -y python3 python3-pip python3-venv git curl wget docker.io docker-compose
        systemctl enable docker
        systemctl start docker
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        yum update -y
        yum install -y python3 python3-pip git curl wget docker docker-compose
        systemctl enable docker
        systemctl start docker
    else
        log_warning "未知的操作系统，尝试通用安装方法"
    fi

    # 添加当前用户到docker组
    usermod -aG docker mem0 2>/dev/null || true

    log_success "系统依赖安装完成"
}

# 创建用户和目录
setup_user_and_dirs() {
    log_info "设置用户和目录..."
    
    # 创建mem0用户（如果不存在）
    if ! id "mem0" &>/dev/null; then
        useradd -r -s /bin/bash -d /opt/mem0 -m mem0
        log_success "创建用户: mem0"
    else
        log_info "用户mem0已存在"
    fi
    
    # 创建必要目录
    mkdir -p /opt/mem0/{logs,backups,data}
    chown -R mem0:mem0 /opt/mem0
    
    log_success "用户和目录设置完成"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    cd /opt/mem0Client
    
    # 创建虚拟环境（如果不存在）
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        log_success "创建Python虚拟环境"
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Python依赖安装完成"
}

# 配置systemd服务
setup_systemd_service() {
    log_info "配置systemd服务..."
    
    # 复制服务文件
    cp scripts/mem0.service /etc/systemd/system/
    
    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable mem0.service
    
    log_success "systemd服务配置完成"
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    # 检查防火墙状态
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian UFW
        ufw allow 8503/tcp
        ufw allow 8888/tcp
        log_success "UFW防火墙规则已添加"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL firewalld
        firewall-cmd --permanent --add-port=8503/tcp
        firewall-cmd --permanent --add-port=8888/tcp
        firewall-cmd --reload
        log_success "firewalld防火墙规则已添加"
    else
        log_warning "未检测到防火墙，请手动开放端口8503和8888"
    fi
}

# 测试API密钥
test_api_key() {
    local api_type="$1"
    local api_key="$2"

    log_info "测试 $api_type API密钥..."

    case "$api_type" in
        "OpenAI")
            response=$(curl -s -w "%{http_code}" -o /dev/null \
                -H "Authorization: Bearer $api_key" \
                -H "Content-Type: application/json" \
                "https://api.openai.com/v1/models")
            ;;
        "Anthropic")
            response=$(curl -s -w "%{http_code}" -o /dev/null \
                -H "x-api-key: $api_key" \
                -H "Content-Type: application/json" \
                "https://api.anthropic.com/v1/messages" \
                -d '{"model":"claude-3-haiku-20240307","max_tokens":1,"messages":[{"role":"user","content":"test"}]}')
            ;;
        "Google")
            response=$(curl -s -w "%{http_code}" -o /dev/null \
                "https://generativelanguage.googleapis.com/v1beta/models?key=$api_key")
            ;;
        *)
            return 1
            ;;
    esac

    if [[ "$response" == "200" ]] || [[ "$response" == "400" ]]; then
        log_success "$api_type API密钥测试通过"
        return 0
    else
        log_warning "$api_type API密钥测试失败 (HTTP: $response)"
        return 1
    fi
}

# 交互式配置API密钥
configure_api_keys() {
    log_info "配置AI API密钥..."
    echo ""
    echo "=============================================="
    echo "🔑 AI API密钥配置"
    echo "=============================================="
    echo "请配置至少一个AI API密钥以使用Mem0服务"
    echo "支持的API提供商："
    echo "1. OpenAI (GPT-3.5, GPT-4)"
    echo "2. Anthropic (Claude)"
    echo "3. Google (Gemini)"
    echo ""

    # 创建环境变量文件
    if [[ ! -f ".env" ]]; then
        cp .env.example .env
    fi

    local has_valid_key=false

    # OpenAI API配置
    echo "--- OpenAI API配置 ---"
    read -p "是否配置OpenAI API密钥? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "请输入OpenAI API密钥: " -s openai_key
        echo
        if [[ -n "$openai_key" ]]; then
            if test_api_key "OpenAI" "$openai_key"; then
                sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" .env
                has_valid_key=true
            else
                read -p "API密钥测试失败，是否仍要保存? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" .env
                fi
            fi
        fi
    fi

    # Anthropic API配置
    echo "--- Anthropic API配置 ---"
    read -p "是否配置Anthropic API密钥? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "请输入Anthropic API密钥: " -s anthropic_key
        echo
        if [[ -n "$anthropic_key" ]]; then
            if test_api_key "Anthropic" "$anthropic_key"; then
                sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$anthropic_key/" .env
                has_valid_key=true
            else
                read -p "API密钥测试失败，是否仍要保存? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$anthropic_key/" .env
                fi
            fi
        fi
    fi

    # Google API配置
    echo "--- Google API配置 ---"
    read -p "是否配置Google API密钥? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "请输入Google API密钥: " -s google_key
        echo
        if [[ -n "$google_key" ]]; then
            if test_api_key "Google" "$google_key"; then
                sed -i "s/GOOGLE_API_KEY=.*/GOOGLE_API_KEY=$google_key/" .env
                has_valid_key=true
            else
                read -p "API密钥测试失败，是否仍要保存? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sed -i "s/GOOGLE_API_KEY=.*/GOOGLE_API_KEY=$google_key/" .env
                fi
            fi
        fi
    fi

    # 检查是否配置了有效密钥
    if [[ "$has_valid_key" == false ]]; then
        echo ""
        log_warning "未检测到有效的API密钥"
        read -p "是否继续安装? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "安装已取消"
            exit 0
        fi
        log_warning "继续安装，但Mem0服务可能无法正常工作"
    else
        log_success "API密钥配置完成"
    fi

    echo "=============================================="
}

# 部署Mem0 API服务
deploy_mem0_api() {
    log_info "部署Mem0 API服务..."

    # 交互式配置API密钥
    configure_api_keys

    # 创建配置目录
    mkdir -p config/{mem0,nginx,postgres}

    # 启动Docker服务
    log_info "启动Mem0 API Docker容器..."
    docker-compose up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 检查服务状态
    if curl -f http://localhost:8888/health &>/dev/null; then
        log_success "Mem0 API服务启动成功"
    else
        log_warning "Mem0 API服务可能未完全启动，请检查Docker日志"
        log_info "使用命令查看日志: docker-compose logs mem0-api"
    fi
}

# 创建配置文件
create_config() {
    log_info "创建配置文件..."

    # 如果config.yaml不存在，创建默认配置
    if [[ ! -f "config.yaml" ]]; then
        cat > config.yaml << EOF
# Mem0 Client Configuration
mem0:
  api_key: "local_api_key"
  api_url: "http://localhost:8888"

defaults:
  user_id: "default_user"
  extract_mode: "auto"
  batch_size: 10

file_processing:
  supported_formats: [".md", ".txt", ".pdf", ".docx", ".json"]
  max_file_size_mb: 10
  concurrent_upload: true
  max_concurrent_files: 3

search:
  default_limit: 10
  max_limit: 100

auth:
  secret_key: "$(openssl rand -hex 32)"
  session_timeout: 3600
  max_login_attempts: 5

logging:
  level: "INFO"
  file: "/opt/mem0/logs/mem0.log"

backup:
  enabled: true
  interval: "daily"
  retention: 7
EOF
        log_success "创建默认配置文件"
    else
        log_info "配置文件已存在，跳过创建"
    fi
}

# 设置权限
set_permissions() {
    log_info "设置文件权限..."
    
    # 设置目录权限
    chown -R mem0:mem0 /opt/mem0Client
    chmod +x /opt/mem0Client/manage.sh
    
    # 设置日志目录权限
    chown -R mem0:mem0 /opt/mem0/logs
    chmod 755 /opt/mem0/logs
    
    log_success "文件权限设置完成"
}

# 启动服务
start_services() {
    log_info "启动Mem0服务..."
    
    systemctl start mem0.service
    systemctl status mem0.service --no-pager
    
    log_success "Mem0服务已启动"
}

# 显示安装完成信息
show_completion_info() {
    echo ""
    echo "=============================================="
    log_success "Mem0 记忆管理系统安装完成！"
    echo "=============================================="
    echo ""
    echo "🌐 Web界面访问地址:"
    echo "   http://$(hostname -I | awk '{print $1}'):8503"
    echo "   http://localhost:8503"
    echo ""
    echo "🔐 默认管理员账户:"
    echo "   用户名: admin"
    echo "   密码: admin123"
    echo "   ⚠️  请立即登录并修改默认密码！"
    echo ""
    echo "📋 管理命令:"
    echo "   启动服务: sudo systemctl start mem0"
    echo "   停止服务: sudo systemctl stop mem0"
    echo "   查看状态: sudo systemctl status mem0"
    echo "   查看日志: sudo journalctl -u mem0 -f"
    echo ""
    echo "🛠️  高级管理:"
    echo "   cd /opt/mem0Client"
    echo "   sudo ./manage.sh [start|stop|restart|status|backup|restore]"
    echo ""
    echo "📚 文档和支持:"
    echo "   README.md - 详细使用说明"
    echo "   MULTIMODAL_FEATURES.md - 多模态功能说明"
    echo ""
    echo "=============================================="
}

# 主安装流程
main() {
    echo "=============================================="
    echo "🧠 Mem0 记忆管理系统 - 一键安装脚本"
    echo "=============================================="
    echo ""
    
    check_root
    detect_os
    install_dependencies
    setup_user_and_dirs
    deploy_mem0_api
    install_python_deps
    create_config
    setup_systemd_service
    setup_firewall
    set_permissions
    start_services
    show_completion_info
}

# 执行主函数
main "$@"
