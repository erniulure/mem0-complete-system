#!/bin/bash

# =============================================================================
# Mem0 记忆管理系统 - 一键安装脚本
# 版本: v2.0
# 作者: Mem0 Team
# 描述: 自动化部署Mem0记忆管理系统，支持完整配置管理
# =============================================================================

set -e  # 遇到错误立即退出

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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    clear
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "                    🧠 Mem0 记忆管理系统 - 一键安装器"
    echo "============================================================================="
    echo -e "${NC}"
    echo "本脚本将帮助您："
    echo "  ✅ 自动检测系统环境"
    echo "  ✅ 安装必要的依赖"
    echo "  ✅ 配置所有服务参数"
    echo "  ✅ 一键启动完整系统"
    echo "  ✅ 提供配置管理工具"
    echo ""
    echo -e "${YELLOW}注意：请确保您有sudo权限${NC}"
    echo ""
    read -p "按回车键继续安装..." -r
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求..."
    
    # 检查操作系统
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "此脚本仅支持Linux系统"
        exit 1
    fi
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker未安装，正在安装..."
        install_docker
    else
        log_success "Docker已安装: $(docker --version)"
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose未安装，正在安装..."
        install_docker_compose
    else
        log_success "Docker Compose已安装"
    fi
    
    # 检查端口占用
    check_ports
}

# 安装Docker
install_docker() {
    log_info "安装Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    log_success "Docker安装完成"
}

# 安装Docker Compose
install_docker_compose() {
    log_info "安装Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose安装完成"
}

# 检查端口占用
check_ports() {
    log_info "检查端口占用情况..."
    
    local ports=(5432 6333 6334 8000 8503 8888)
    local occupied_ports=()
    
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            occupied_ports+=($port)
        fi
    done
    
    if [ ${#occupied_ports[@]} -gt 0 ]; then
        log_warning "以下端口被占用: ${occupied_ports[*]}"
        log_info "安装过程中会自动调整端口配置"
    else
        log_success "所有必要端口都可用"
    fi
}

# 主安装流程
main() {
    show_welcome
    check_requirements
    
    # 运行配置向导
    log_step "启动配置向导..."
    if [[ "$1" == "--auto" ]]; then
        ./config-wizard.sh --auto
    else
        ./config-wizard.sh
    fi
    
    # 构建和启动服务
    log_step "构建和启动服务..."
    docker-compose build
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    check_services
    
    # 显示完成信息
    show_completion
}

# 检查服务状态
check_services() {
    log_step "检查服务状态..."
    
    local services=("mem0-postgres" "mem0-qdrant" "mem0-api" "mem0-webui-persistent")
    
    for service in "${services[@]}"; do
        if docker ps | grep -q "$service"; then
            log_success "$service 运行正常"
        else
            log_error "$service 启动失败"
        fi
    done
}

# 显示完成信息
show_completion() {
    clear
    echo -e "${GREEN}"
    echo "============================================================================="
    echo "                    🎉 Mem0 系统安装完成！"
    echo "============================================================================="
    echo -e "${NC}"
    echo "服务访问地址："
    echo "  🌐 Web界面: http://localhost:8503"
    echo "  🔌 API服务: http://localhost:8888"
    echo "  📊 Qdrant管理: http://localhost:6333/dashboard"
    echo ""
    echo "管理命令："
    echo "  📋 查看状态: docker-compose ps"
    echo "  🔄 重启服务: docker-compose restart"
    echo "  📝 查看日志: docker-compose logs -f"
    echo "  ⚙️  配置管理: ./config-manager.sh"
    echo ""
    echo -e "${YELLOW}首次使用请访问Web界面进行初始化配置${NC}"
}

# 运行主函数
main "$@"
