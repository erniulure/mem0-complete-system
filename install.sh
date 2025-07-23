#!/bin/bash

# =============================================================================
# Mem0 完整智能记忆管理系统 - 一键安装脚本
# 版本: v2.0
# 描述: 自动化部署完整的Mem0系统（包含Mem0、Mem0Client、Gemini-Balance）
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 显示欢迎信息
show_welcome() {
    clear
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "              🧠 Mem0 完整智能记忆管理系统 - 一键安装器"
    echo "============================================================================="
    echo -e "${NC}"
    echo "本系统包含三个核心组件："
    echo "  🧠 Mem0: 核心记忆管理引擎和API服务"
    echo "  🌐 Mem0Client: Web用户界面和客户端"
    echo "  🤖 Gemini-Balance: AI服务代理和负载均衡"
    echo ""
    echo "安装选项："
    echo "  1) 🚀 完整安装（推荐）- 安装所有组件"
    echo "  2) 🎯 仅安装Mem0系统 - 使用外部AI服务"
    echo "  3) 🔧 自定义安装 - 选择性安装组件"
    echo ""
    read -p "请选择安装方式 (1-3): " install_choice
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求..."
    
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
    
    # 检查系统资源
    check_system_resources
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

# 检查系统资源
check_system_resources() {
    log_info "检查系统资源..."
    
    # 检查内存
    local total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ "$total_mem" -lt 4096 ]; then
        log_warning "系统内存少于4GB，可能影响性能"
    else
        log_success "系统内存充足: ${total_mem}MB"
    fi
    
    # 检查磁盘空间
    local free_space=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$free_space" -lt 20 ]; then
        log_warning "磁盘空间少于20GB，可能不足"
    else
        log_success "磁盘空间充足: ${free_space}GB"
    fi
}

# 完整安装
full_install() {
    log_step "开始完整安装..."
    
    # 1. 安装Gemini-Balance
    log_info "安装Gemini-Balance AI服务..."
    cd gemini-balance
    if [ -f "deploy.sh" ]; then
        chmod +x deploy.sh
        ./deploy.sh
    else
        log_warning "Gemini-Balance部署脚本不存在，跳过"
    fi
    cd ..
    
    # 2. 安装Mem0系统
    log_info "安装Mem0核心系统..."
    cd mem0-deployment
    chmod +x install.sh
    ./install.sh
    cd ..
    
    log_success "完整安装完成！"
}

# 仅安装Mem0
mem0_only_install() {
    log_step "安装Mem0系统（使用外部AI服务）..."
    
    cd mem0-deployment
    chmod +x install.sh
    ./install.sh
    cd ..
    
    log_success "Mem0系统安装完成！"
}

# 自定义安装
custom_install() {
    log_step "自定义安装..."
    
    echo ""
    echo "请选择要安装的组件："
    echo ""
    
    read -p "是否安装Gemini-Balance AI服务？(y/N): " install_gemini
    read -p "是否安装Mem0核心系统？(Y/n): " install_mem0
    
    if [[ "$install_gemini" =~ ^[Yy]$ ]]; then
        log_info "安装Gemini-Balance..."
        cd gemini-balance
        if [ -f "deploy.sh" ]; then
            chmod +x deploy.sh
            ./deploy.sh
        fi
        cd ..
    fi
    
    if [[ "$install_mem0" =~ ^[Yy]$ ]] || [[ -z "$install_mem0" ]]; then
        log_info "安装Mem0系统..."
        cd mem0-deployment
        chmod +x install.sh
        ./install.sh
        cd ..
    fi
    
    log_success "自定义安装完成！"
}

# 显示完成信息
show_completion() {
    clear
    echo -e "${GREEN}"
    echo "============================================================================="
    echo "                    🎉 Mem0完整系统安装完成！"
    echo "============================================================================="
    echo -e "${NC}"
    echo "系统访问地址："
    echo "  🌐 Mem0 Web界面: http://localhost:8503"
    echo "  🔌 Mem0 API服务: http://localhost:8888"
    echo "  📚 API文档: http://localhost:8888/docs"
    echo "  🤖 Gemini-Balance: http://localhost:8000"
    echo "  📊 Qdrant管理: http://localhost:6333/dashboard"
    echo ""
    echo "管理命令："
    echo "  📋 查看状态: cd mem0-deployment && ./scripts/quick-start.sh"
    echo "  ⚙️  配置管理: cd mem0-deployment && ./scripts/config-manager.sh"
    echo "  📝 查看日志: cd mem0-deployment && docker-compose logs -f"
    echo ""
    echo "默认账户："
    echo "  👤 用户名: admin"
    echo "  🔑 密码: admin123"
    echo ""
    echo -e "${YELLOW}首次使用请访问Web界面进行初始化配置${NC}"
    echo -e "${YELLOW}建议首次登录后立即修改默认密码${NC}"
}

# 主函数
main() {
    show_welcome
    
    case $install_choice in
        1|"")
            check_requirements
            full_install
            ;;
        2)
            check_requirements
            mem0_only_install
            ;;
        3)
            check_requirements
            custom_install
            ;;
        *)
            log_error "无效选择，退出安装"
            exit 1
            ;;
    esac
    
    show_completion
}

# 运行主函数
main "$@"
