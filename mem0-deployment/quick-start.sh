#!/bin/bash

# =============================================================================
# Mem0 快速启动脚本 - 适用于已配置环境
# 版本: v2.0
# 描述: 快速启动已配置的Mem0系统
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
    echo "                    🚀 Mem0 快速启动器"
    echo "============================================================================="
    echo -e "${NC}"
    echo "选择启动模式："
    echo ""
    echo "  1) 🔄 重启所有服务"
    echo "  2) ▶️  启动服务（如果未运行）"
    echo "  3) ⏹️  停止所有服务"
    echo "  4) 📊 查看服务状态"
    echo "  5) 📝 查看服务日志"
    echo "  6) ⚙️  配置管理"
    echo "  0) 🚪 退出"
    echo ""
}

# 检查配置文件
check_config() {
    if [[ ! -f ".env" ]]; then
        log_error "配置文件 .env 不存在"
        log_info "请先运行 ./install.sh 进行初始化配置"
        exit 1
    fi
    
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "Docker Compose 配置文件不存在"
        exit 1
    fi
    
    log_success "配置文件检查通过"
}

# 启动服务
start_services() {
    log_step "启动Mem0服务..."
    
    # 检查是否已有服务运行
    if docker-compose ps | grep -q "Up"; then
        log_warning "检测到服务已在运行"
        echo ""
        docker-compose ps
        echo ""
        read -p "是否重启服务？(y/N): " restart_choice
        
        if [[ "$restart_choice" =~ ^[Yy]$ ]]; then
            restart_services
        else
            log_info "保持当前服务状态"
        fi
    else
        log_info "启动所有服务..."
        docker-compose up -d
        
        log_info "等待服务启动..."
        sleep 15
        
        check_service_health
    fi
}

# 重启服务
restart_services() {
    log_step "重启Mem0服务..."
    
    log_info "停止现有服务..."
    docker-compose down
    
    log_info "启动服务..."
    docker-compose up -d
    
    log_info "等待服务启动..."
    sleep 15
    
    check_service_health
}

# 停止服务
stop_services() {
    log_step "停止Mem0服务..."
    
    if docker-compose ps | grep -q "Up"; then
        docker-compose down
        log_success "所有服务已停止"
    else
        log_info "服务未运行"
    fi
}

# 检查服务健康状态
check_service_health() {
    log_step "检查服务健康状态..."
    
    local services=("mem0-postgres" "mem0-qdrant" "mem0-api" "mem0-webui-persistent")
    local healthy_count=0
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service.*Up"; then
            # 检查健康状态
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "unknown")
            
            case $health_status in
                "healthy")
                    echo -e "  ✅ $service: ${GREEN}健康${NC}"
                    ((healthy_count++))
                    ;;
                "starting")
                    echo -e "  🔄 $service: ${YELLOW}启动中${NC}"
                    ;;
                "unhealthy")
                    echo -e "  ❌ $service: ${RED}不健康${NC}"
                    ;;
                "unknown"|"")
                    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service.*Up"; then
                        echo -e "  ✅ $service: ${GREEN}运行中${NC}"
                        ((healthy_count++))
                    else
                        echo -e "  ❌ $service: ${RED}未运行${NC}"
                    fi
                    ;;
            esac
        else
            echo -e "  ❌ $service: ${RED}未运行${NC}"
        fi
    done
    
    echo ""
    if [[ $healthy_count -eq ${#services[@]} ]]; then
        log_success "所有服务运行正常！"
        show_access_info
    else
        log_warning "部分服务可能存在问题，请检查日志"
    fi
}

# 显示访问信息
show_access_info() {
    # 读取端口配置
    local webui_port=$(grep "^WEBUI_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "8503")
    local api_port=$(grep "^MEM0_API_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "8888")
    local qdrant_port=$(grep "^QDRANT_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "6333")
    
    echo ""
    echo -e "${CYAN}🌐 服务访问地址：${NC}"
    echo "  📱 Web界面: http://localhost:$webui_port"
    echo "  🔌 API服务: http://localhost:$api_port"
    echo "  📊 Qdrant管理: http://localhost:$qdrant_port/dashboard"
    echo ""
}

# 查看服务状态
view_status() {
    clear
    echo -e "${CYAN}Mem0 服务状态${NC}"
    echo "============================================================================="
    
    # 显示Docker Compose状态
    if command -v docker-compose &> /dev/null; then
        echo -e "${YELLOW}Docker Compose 服务状态:${NC}"
        docker-compose ps
        echo ""
    fi
    
    # 显示详细的容器状态
    echo -e "${YELLOW}详细容器状态:${NC}"
    docker ps --filter "name=mem0" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # 显示资源使用情况
    echo -e "${YELLOW}资源使用情况:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker ps --filter "name=mem0" --format "{{.Names}}" | tr '\n' ' ')
    echo ""
    
    show_access_info
    
    read -p "按回车键返回主菜单..." -r
}

# 查看服务日志
view_logs() {
    clear
    echo -e "${CYAN}选择要查看的日志${NC}"
    echo "============================================================================="
    echo "1) mem0-api - API服务日志"
    echo "2) mem0-webui - Web界面日志"
    echo "3) mem0-postgres - 数据库日志"
    echo "4) mem0-qdrant - 向量数据库日志"
    echo "5) 所有服务日志"
    echo "6) 实时日志（所有服务）"
    echo "0) 返回主菜单"
    echo ""
    
    read -p "选择 (0-6): " log_choice
    
    case $log_choice in
        1) docker-compose logs --tail=100 mem0-api ;;
        2) docker-compose logs --tail=100 mem0-webui-persistent ;;
        3) docker-compose logs --tail=100 mem0-postgres ;;
        4) docker-compose logs --tail=100 mem0-qdrant ;;
        5) docker-compose logs --tail=50 ;;
        6) docker-compose logs -f ;;
        0) return ;;
        *) log_error "无效选择" && sleep 2 ;;
    esac
    
    if [[ $log_choice != "0" && $log_choice != "6" ]]; then
        echo ""
        read -p "按回车键返回..." -r
    fi
}

# 主循环
main() {
    # 检查配置
    check_config
    
    while true; do
        show_welcome
        read -p "请选择操作 (0-6): " choice
        
        case $choice in
            1) restart_services ;;
            2) start_services ;;
            3) stop_services ;;
            4) view_status ;;
            5) view_logs ;;
            6) 
                if [[ -f "config-manager.sh" ]]; then
                    ./config-manager.sh
                else
                    log_error "配置管理器不存在"
                    sleep 2
                fi
                ;;
            0) 
                log_info "退出快速启动器"
                exit 0
                ;;
            *) 
                log_error "无效选择，请重试"
                sleep 2
                ;;
        esac
    done
}

# 运行主函数
main "$@"
