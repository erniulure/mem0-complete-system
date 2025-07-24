#!/bin/bash

# =============================================================================
# Mem0 Web UI - 容器化安装脚本
# 版本: v1.0
# 描述: 自动化部署Mem0 Web用户界面
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查依赖
check_dependencies() {
    log_info "检查依赖服务..."
    
    # 检查Mem0 API是否运行
    if ! curl -s http://localhost:8888/ > /dev/null 2>&1; then
        log_warning "Mem0 API服务未运行，Web UI可能无法正常工作"
    else
        log_success "Mem0 API服务运行正常"
    fi
    
    # 检查Gemini Balance是否运行
    if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
        log_warning "Gemini Balance服务未运行，AI功能可能无法使用"
    else
        log_success "Gemini Balance服务运行正常"
    fi
}

# 构建和启动Web UI
install_webui() {
    log_info "构建Web UI容器..."
    
    # 停止并删除旧容器
    docker-compose down 2>/dev/null || true
    docker rm -f mem0-webui 2>/dev/null || true
    
    # 构建新容器
    docker-compose build --no-cache
    
    log_info "启动Web UI服务..."
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 连接到网络
    log_info "配置网络连接..."
    docker network connect gemini-balance_gemini-network mem0-webui 2>/dev/null || true
    docker network connect mem0-deployment_mem0-network mem0-webui 2>/dev/null || true
    
    log_success "Web UI安装完成"
}

# 验证安装
verify_installation() {
    log_info "验证Web UI安装..."
    
    # 检查容器状态
    if ! docker ps | grep -q "mem0-webui"; then
        log_error "Web UI容器未运行"
        return 1
    fi
    
    # 检查Web服务
    local retry_count=0
    while [ $retry_count -lt 30 ]; do
        if curl -s http://localhost:8503/ > /dev/null 2>&1; then
            log_success "Web UI服务运行正常"
            break
        fi
        sleep 2
        retry_count=$((retry_count + 1))
    done
    
    if [ $retry_count -eq 30 ]; then
        log_error "Web UI服务启动超时"
        return 1
    fi
    
    # 测试网络连接
    if docker exec mem0-webui curl -s http://gemini-balance:8000/v1/models > /dev/null 2>&1; then
        log_success "Web UI到Gemini Balance网络连接正常"
    else
        log_warning "Web UI到Gemini Balance网络连接异常"
    fi
    
    return 0
}

# 显示完成信息
show_completion() {
    echo ""
    echo -e "${GREEN}🎉 Web UI安装完成！${NC}"
    echo ""
    echo "📱 访问地址: http://localhost:8503"
    echo "👤 默认用户: admin"
    echo "🔑 默认密码: admin123"
    echo ""
    echo "🔧 管理命令:"
    echo "  查看状态: docker-compose ps"
    echo "  查看日志: docker-compose logs -f"
    echo "  重启服务: docker-compose restart"
    echo "  停止服务: docker-compose down"
    echo ""
}

# 主函数
main() {
    echo -e "${BLUE}🌐 开始安装Mem0 Web UI...${NC}"
    
    check_dependencies
    install_webui
    
    if verify_installation; then
        show_completion
    else
        log_error "安装验证失败，请检查日志"
        exit 1
    fi
}

# 运行主函数
main "$@"
