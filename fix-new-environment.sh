#!/bin/bash

# =============================================================================
# 新环境问题修复脚本
# 专门解决在全新电脑上安装时遇到的问题
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

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        log_info "请使用: sudo $0"
        exit 1
    fi
}

# 完全清理环境
clean_environment() {
    log_step "完全清理现有环境"
    
    # 停止所有相关容器
    log_info "停止所有相关容器..."
    docker stop $(docker ps -q --filter "name=mem0") 2>/dev/null || true
    docker stop $(docker ps -q --filter "name=gemini") 2>/dev/null || true
    
    # 删除所有相关容器
    log_info "删除所有相关容器..."
    docker rm $(docker ps -aq --filter "name=mem0") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=gemini") 2>/dev/null || true
    
    # 删除所有相关卷
    log_info "删除所有相关数据卷..."
    docker volume rm $(docker volume ls -q | grep -E "(mem0|postgres|neo4j|qdrant|gemini)") 2>/dev/null || true
    
    # 删除所有相关网络
    log_info "删除所有相关网络..."
    docker network rm $(docker network ls -q --filter "name=mem0") 2>/dev/null || true
    docker network rm $(docker network ls -q --filter "name=gemini") 2>/dev/null || true
    
    log_success "环境清理完成"
}

# 强制重新初始化数据库
force_reinit_database() {
    log_step "强制重新初始化数据库"
    
    cd mem0-deployment
    
    # 确保PostgreSQL容器完全重新创建
    log_info "重新创建PostgreSQL容器..."
    docker-compose down -v
    docker volume rm mem0-deployment_postgres_data 2>/dev/null || true
    
    # 只启动PostgreSQL
    log_info "启动PostgreSQL服务..."
    docker-compose up -d mem0-postgres
    
    # 等待PostgreSQL完全启动
    log_info "等待PostgreSQL完全启动..."
    sleep 30
    
    # 检查PostgreSQL是否正常
    for i in {1..10}; do
        if docker exec mem0-postgres pg_isready -U mem0 -d mem0 >/dev/null 2>&1; then
            log_success "PostgreSQL启动成功"
            break
        fi
        log_info "等待PostgreSQL启动... ($i/10)"
        sleep 5
    done
    
    # 手动执行初始化脚本
    log_info "手动执行WebUI数据库初始化..."
    docker exec mem0-postgres psql -U mem0 -d mem0 -f /docker-entrypoint-initdb.d/init_webui_db.sql
    
    # 验证WebUI数据库
    log_info "验证WebUI数据库..."
    if docker exec mem0-postgres psql -U mem0 -d webui -c "\dt" >/dev/null 2>&1; then
        log_success "WebUI数据库初始化成功"
    else
        log_error "WebUI数据库初始化失败"
        return 1
    fi
    
    cd ..
}

# 修复网络配置
fix_network_configuration() {
    log_step "修复网络配置"
    
    # 创建统一网络
    log_info "创建统一网络..."
    docker network create mem0-unified-network 2>/dev/null || log_info "网络已存在"
    
    # 确保所有容器连接到统一网络
    log_info "连接现有容器到统一网络..."
    for container in mem0-postgres mem0-qdrant mem0-neo4j mem0-api mem0-webui gemini-balance gemini-balance-mysql; do
        if docker ps -q --filter "name=$container" | grep -q .; then
            docker network connect mem0-unified-network $container 2>/dev/null || true
        fi
    done
    
    log_success "网络配置修复完成"
}

# 修复环境变量
fix_environment_variables() {
    log_step "修复环境变量配置"
    
    # 更新mem0-deployment/.env
    log_info "更新mem0-deployment环境变量..."
    cd mem0-deployment
    cat > .env << EOF
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
    cd ..
    
    # 更新mem0Client/.env
    log_info "更新mem0Client环境变量..."
    cd mem0Client
    cat > .env << EOF
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
    cd ..
    
    log_success "环境变量配置完成"
}

# 重新启动所有服务
restart_all_services() {
    log_step "重新启动所有服务"
    
    # 按正确顺序启动服务
    log_info "启动Gemini Balance..."
    cd gemini-balance
    docker-compose up -d
    cd ..
    
    log_info "启动Mem0核心服务..."
    cd mem0-deployment
    docker-compose up -d
    cd ..
    
    log_info "启动WebUI..."
    cd mem0Client
    docker-compose up -d
    cd ..
    
    # 等待所有服务启动
    log_info "等待所有服务启动..."
    sleep 60
    
    log_success "所有服务重新启动完成"
}

# 验证修复结果
verify_fix() {
    log_step "验证修复结果"
    
    local all_ok=true
    
    # 检查容器状态
    log_info "检查容器状态..."
    for container in mem0-postgres mem0-qdrant mem0-neo4j mem0-api mem0-webui gemini-balance; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q $container; then
            log_success "$container 运行正常"
        else
            log_error "$container 未运行"
            all_ok=false
        fi
    done
    
    # 检查WebUI数据库连接
    log_info "检查WebUI数据库连接..."
    if docker exec mem0-postgres psql -U mem0 -d webui -c "SELECT COUNT(*) FROM webui_config;" >/dev/null 2>&1; then
        log_success "WebUI数据库连接正常"
    else
        log_error "WebUI数据库连接失败"
        all_ok=false
    fi
    
    # 检查服务响应
    log_info "检查服务响应..."
    sleep 10
    
    if curl -s http://localhost:8000 >/dev/null 2>&1; then
        log_success "Gemini Balance响应正常"
    else
        log_warning "Gemini Balance响应异常"
    fi
    
    if curl -s http://localhost:8888 >/dev/null 2>&1; then
        log_success "Mem0 API响应正常"
    else
        log_warning "Mem0 API响应异常"
    fi
    
    if curl -s http://localhost:8503 >/dev/null 2>&1; then
        log_success "WebUI响应正常"
    else
        log_warning "WebUI响应异常"
    fi
    
    if $all_ok; then
        log_success "🎉 修复完成！所有服务正常运行"
    else
        log_warning "⚠️ 部分服务仍有问题，请检查日志"
    fi
}

# 主函数
main() {
    echo "============================================================================="
    echo "              🔧 Mem0 新环境问题修复脚本"
    echo "============================================================================="
    echo ""
    echo "此脚本将："
    echo "  1. 完全清理现有环境"
    echo "  2. 强制重新初始化数据库"
    echo "  3. 修复网络配置"
    echo "  4. 修复环境变量"
    echo "  5. 重新启动所有服务"
    echo "  6. 验证修复结果"
    echo ""
    
    read -p "是否继续？(y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "操作已取消"
        exit 0
    fi
    
    check_root
    clean_environment
    force_reinit_database
    fix_network_configuration
    fix_environment_variables
    restart_all_services
    verify_fix
    
    echo ""
    echo "============================================================================="
    echo "🎉 修复完成！"
    echo "============================================================================="
    echo ""
    echo "访问地址："
    echo "  🌐 WebUI: http://localhost:8503"
    echo "  🔌 API: http://localhost:8888"
    echo "  🤖 Gemini Balance: http://localhost:8000"
    echo ""
}

# 运行主函数
main "$@"
