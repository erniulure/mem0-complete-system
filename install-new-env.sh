#!/bin/bash

# =============================================================================
# Mem0 新环境专用安装脚本
# 专门为全新、干净的电脑环境设计
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

log_step() {
    echo ""
    echo -e "${BLUE}[STEP]${NC} $1"
    echo "----------------------------------------"
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求"
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查端口
    local ports=(8000 8888 8503 7474 7687 6333 5432 3306)
    for port in "${ports[@]}"; do
        if netstat -tuln | grep -q ":$port "; then
            log_warning "端口 $port 已被占用"
        fi
    done
    
    log_success "系统要求检查完成"
}

# 创建环境配置文件
create_env_files() {
    log_step "创建环境配置文件"
    
    # 创建mem0-deployment/.env
    log_info "创建mem0-deployment环境配置..."
    cat > mem0-deployment/.env << 'EOF'
# PostgreSQL配置
POSTGRES_HOST=mem0-postgres
POSTGRES_PORT=5432
POSTGRES_DB=mem0
POSTGRES_USER=mem0
POSTGRES_PASSWORD=mem0_password

# OpenAI API配置（使用Gemini Balance）
OPENAI_API_KEY=q1q2q3q4
OPENAI_BASE_URL=http://gemini-balance:8000/v1

# Neo4j配置
NEO4J_URI=bolt://mem0-neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Qdrant配置
QDRANT_HOST=mem0-qdrant
QDRANT_PORT=6333
EOF
    
    # 创建mem0Client/.env
    log_info "创建mem0Client环境配置..."
    cat > mem0Client/.env << 'EOF'
# WebUI数据库配置
POSTGRES_HOST=mem0-postgres
POSTGRES_PORT=5432
POSTGRES_USER=mem0
POSTGRES_PASSWORD=mem0_password

# Mem0 API配置
MEM0_API_URL=http://mem0-api:8000

# AI服务配置
AI_API_URL=http://gemini-balance:8000
AI_API_KEY=q1q2q3q4
EOF
    
    # 创建gemini-balance/.env
    log_info "创建gemini-balance环境配置..."
    if [ ! -f "gemini-balance/.env" ]; then
        cp gemini-balance/.env.example gemini-balance/.env 2>/dev/null || true
    fi
    
    log_success "环境配置文件创建完成"
}

# 创建统一网络
create_network() {
    log_step "创建统一Docker网络"
    
    # 删除可能存在的旧网络
    docker network rm mem0-unified-network 2>/dev/null || true
    
    # 创建新网络
    docker network create mem0-unified-network
    
    log_success "统一网络创建完成"
}

# 按顺序安装服务
install_services() {
    log_step "按顺序安装服务"
    
    # 1. 安装Gemini Balance
    log_info "安装Gemini Balance AI服务..."
    cd gemini-balance
    chmod +x deploy.sh
    echo "q1q2q3q4" | ./deploy.sh --auto || {
        log_warning "Gemini Balance自动安装失败，尝试手动启动..."
        docker-compose up -d
    }
    cd ..
    
    # 等待Gemini Balance启动
    log_info "等待Gemini Balance启动..."
    for i in {1..12}; do
        if curl -s http://localhost:8000 >/dev/null 2>&1; then
            log_success "Gemini Balance启动成功"
            break
        fi
        log_info "等待Gemini Balance启动... ($i/12)"
        sleep 10
    done
    
    # 2. 安装Mem0核心服务
    log_info "安装Mem0核心服务..."
    cd mem0-deployment
    
    # 确保所有服务使用统一网络
    if ! grep -q "mem0-unified-network" docker-compose.yml; then
        cat >> docker-compose.yml << 'EOF'

networks:
  default:
    external: true
    name: mem0-unified-network
EOF
    fi
    
    docker-compose up -d
    cd ..
    
    # 等待Mem0服务启动
    log_info "等待Mem0服务启动..."
    for i in {1..18}; do
        if curl -s http://localhost:8888 >/dev/null 2>&1; then
            log_success "Mem0 API启动成功"
            break
        fi
        log_info "等待Mem0 API启动... ($i/18)"
        sleep 10
    done
    
    # 3. 手动初始化WebUI数据库
    log_info "初始化WebUI数据库..."
    sleep 10
    docker exec mem0-postgres psql -U mem0 -d mem0 -f /docker-entrypoint-initdb.d/init_webui_db.sql || {
        log_warning "WebUI数据库初始化可能失败，但继续安装..."
    }
    
    # 4. 安装WebUI
    log_info "安装WebUI..."
    cd mem0Client
    
    # 确保WebUI使用统一网络
    if ! grep -q "mem0-unified-network" docker-compose.yml; then
        cat >> docker-compose.yml << 'EOF'

networks:
  default:
    external: true
    name: mem0-unified-network
EOF
    fi
    
    docker-compose up -d
    cd ..
    
    # 等待WebUI启动
    log_info "等待WebUI启动..."
    for i in {1..12}; do
        if curl -s http://localhost:8503 >/dev/null 2>&1; then
            log_success "WebUI启动成功"
            break
        fi
        log_info "等待WebUI启动... ($i/12)"
        sleep 10
    done
    
    log_success "所有服务安装完成"
}

# 验证安装
verify_installation() {
    log_step "验证安装结果"
    
    local all_ok=true
    
    # 检查服务响应
    log_info "检查服务响应..."
    
    if curl -s http://localhost:8000 >/dev/null 2>&1; then
        log_success "✅ Gemini Balance (8000) 响应正常"
    else
        log_error "❌ Gemini Balance (8000) 响应异常"
        all_ok=false
    fi
    
    if curl -s http://localhost:8888 >/dev/null 2>&1; then
        log_success "✅ Mem0 API (8888) 响应正常"
    else
        log_error "❌ Mem0 API (8888) 响应异常"
        all_ok=false
    fi
    
    if curl -s http://localhost:8503 >/dev/null 2>&1; then
        log_success "✅ WebUI (8503) 响应正常"
    else
        log_error "❌ WebUI (8503) 响应异常"
        all_ok=false
    fi
    
    # 检查数据库
    log_info "检查数据库连接..."
    if docker exec mem0-postgres pg_isready -U mem0 -d mem0 >/dev/null 2>&1; then
        log_success "✅ PostgreSQL 连接正常"
    else
        log_error "❌ PostgreSQL 连接异常"
        all_ok=false
    fi
    
    if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
        log_success "✅ Neo4j 连接正常"
    else
        log_error "❌ Neo4j 连接异常"
        all_ok=false
    fi
    
    # 检查WebUI数据库
    if docker exec mem0-postgres psql -U mem0 -d webui -c "SELECT 1" >/dev/null 2>&1; then
        log_success "✅ WebUI数据库连接正常"
    else
        log_warning "⚠️ WebUI数据库连接异常"
    fi
    
    if $all_ok; then
        log_success "🎉 安装验证通过！"
        return 0
    else
        log_warning "⚠️ 部分服务有问题，但基本功能可用"
        return 1
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo "============================================================================="
    echo "🎉 Mem0 新环境安装完成！"
    echo "============================================================================="
    echo ""
    echo "访问地址："
    echo "  🌐 WebUI: http://localhost:8503"
    echo "  🔌 Mem0 API: http://localhost:8888"
    echo "  🤖 Gemini Balance: http://localhost:8000"
    echo "  📊 Neo4j Browser: http://localhost:7474 (neo4j/password)"
    echo "  🔍 Qdrant: http://localhost:6333"
    echo ""
    echo "如果遇到问题，请运行修复脚本："
    echo "  sudo ./fix-new-environment.sh"
    echo ""
    echo "查看服务状态："
    echo "  docker ps"
    echo ""
    echo "查看服务日志："
    echo "  docker logs <容器名>"
    echo ""
}

# 主函数
main() {
    echo "============================================================================="
    echo "              🧠 Mem0 新环境专用安装脚本"
    echo "============================================================================="
    echo ""
    echo "此脚本专为全新、干净的电脑环境设计，将："
    echo "  1. 检查系统要求"
    echo "  2. 创建环境配置文件"
    echo "  3. 创建统一Docker网络"
    echo "  4. 按正确顺序安装所有服务"
    echo "  5. 验证安装结果"
    echo ""
    
    if [[ "$1" != "--auto" ]]; then
        read -p "是否继续安装？(y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "安装已取消"
            exit 0
        fi
    fi
    
    check_requirements
    create_env_files
    create_network
    install_services
    
    if verify_installation; then
        show_completion
    else
        echo ""
        echo "⚠️ 安装完成但部分服务可能需要调整"
        echo "请运行修复脚本: sudo ./fix-new-environment.sh"
        show_completion
    fi
}

# 运行主函数
main "$@"
