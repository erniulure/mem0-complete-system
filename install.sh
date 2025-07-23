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

    # 检查是否为自动安装模式
    if [[ "$1" == "--auto" ]]; then
        echo "🤖 自动安装模式：将执行完整安装"
        install_choice=1
        return
    fi

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
    if [[ "$1" == "--auto" ]]; then
        ./install.sh --auto
    else
        ./install.sh
    fi
    cd ..
    
    log_success "完整安装完成！"
}

# 仅安装Mem0
mem0_only_install() {
    log_step "安装Mem0系统（使用外部AI服务）..."
    
    cd mem0-deployment
    chmod +x install.sh
    if [[ "$1" == "--auto" ]]; then
        ./install.sh --auto
    else
        ./install.sh
    fi
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
        if [[ "$1" == "--auto" ]]; then
            ./install.sh --auto
        else
            ./install.sh
        fi
        cd ..
    fi
    
    log_success "自定义安装完成！"
}

# 验证安装状态
verify_installation() {
    log_step "验证安装状态..."

    local all_services_ok=true
    local service_status=""

    # 等待服务启动
    echo "⏳ 等待服务完全启动..."
    sleep 10

    # 检查Gemini Balance
    if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
        service_status+="✅ Gemini Balance (端口8000): 运行正常\n"
    else
        service_status+="❌ Gemini Balance (端口8000): 服务异常\n"
        all_services_ok=false
    fi

    # 检查Mem0 API
    if curl -s http://localhost:8888/ > /dev/null 2>&1; then
        service_status+="✅ Mem0 API (端口8888): 运行正常\n"
    else
        service_status+="❌ Mem0 API (端口8888): 服务异常\n"
        all_services_ok=false
    fi

    # 检查Web界面
    if curl -s http://localhost:8503/ > /dev/null 2>&1; then
        service_status+="✅ Web界面 (端口8503): 运行正常\n"
    else
        service_status+="❌ Web界面 (端口8503): 服务异常\n"
        all_services_ok=false
    fi

    # 检查Docker容器状态
    local containers_status=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mem0|qdrant|gemini|postgres)")

    echo -e "\n📊 服务状态检查结果："
    echo -e "$service_status"

    echo -e "\n🐳 Docker容器状态："
    echo "$containers_status"

    if $all_services_ok; then
        log_success "所有服务运行正常！"
        return 0
    else
        log_error "部分服务异常，请检查日志"
        return 1
    fi
}

# 显示完成信息
show_completion() {
    clear
    echo -e "${GREEN}"
    echo "============================================================================="
    echo "                    🎉 Mem0完整系统安装完成！"
    echo "============================================================================="
    echo -e "${NC}"

    # 验证安装
    if verify_installation; then
        echo ""
        echo -e "${GREEN}🎯 安装验证: 所有服务运行正常！${NC}"
    else
        echo ""
        echo -e "${RED}⚠️  安装验证: 部分服务异常，请查看上方状态检查${NC}"
    fi

    echo ""
    echo "🌐 系统访问地址："
    echo "  📱 Web界面: http://localhost:8503"
    echo "  🔌 API服务: http://localhost:8888"
    echo "  📚 API文档: http://localhost:8888/docs"
    echo "  🤖 Gemini-Balance: http://localhost:8000"
    echo "  📊 Qdrant管理: http://localhost:6333/dashboard"
    echo ""
    echo "🔧 管理命令："
    echo "  📋 查看状态: cd mem0-deployment && docker-compose ps"
    echo "  📝 查看日志: cd mem0-deployment && docker-compose logs -f"
    echo "  🔄 重启服务: cd mem0-deployment && docker-compose restart"
    echo "  � 停止服务: cd mem0-deployment && docker-compose down"
    echo ""
    echo "🔐 默认账户："
    echo "  👤 用户名: admin"
    echo "  🔑 密码: q1q2q3q4"
    echo ""
    echo "🚀 快速开始："
    echo "  1. 打开浏览器访问: http://localhost:8503"
    echo "  2. 使用默认账户登录"
    echo "  3. 开始创建和管理您的智能记忆"
    echo ""
    echo "💡 功能特色："
    echo "  🧠 动态智能模型选择 - 自动选择最适合的AI模型"
    echo "  🔄 多模态支持 - 文本、图片、语音记忆"
    echo "  🔍 智能搜索 - 语义搜索和向量检索"
    echo "  📊 可视化管理 - 直观的记忆管理界面"
    echo ""
    echo -e "${YELLOW}⚠️  重要提醒：${NC}"
    echo "  🔐 请及时修改默认密码"
    echo "  🛡️  生产环境请配置HTTPS"
    echo "  💾 定期备份重要数据"
    echo ""
    echo -e "${GREEN}🧠 开始使用 Mem0 智能记忆管理系统吧！${NC}"
}

# 主函数
main() {
    show_welcome "$@"

    case $install_choice in
        1|"")
            check_requirements
            full_install "$@"
            ;;
        2)
            check_requirements
            mem0_only_install "$@"
            ;;
        3)
            check_requirements
            custom_install "$@"
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
