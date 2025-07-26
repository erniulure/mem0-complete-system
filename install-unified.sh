#!/bin/bash

# =============================================================================
# Mem0 统一安装脚本
# 所有服务集成在一个docker-compose.yml中，简化安装过程
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
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "系统要求检查通过"
}

# 清理环境
clean_environment() {
    log_step "清理现有环境"
    
    # 停止可能运行的服务
    log_info "停止现有服务..."
    cd mem0-deployment
    docker compose down -v 2>/dev/null || true
    cd ..

    cd mem0Client
    docker compose down -v 2>/dev/null || true
    cd ..

    cd gemini-balance
    docker compose down -v 2>/dev/null || true
    cd ..
    
    # 清理相关容器
    log_info "清理相关容器..."
    docker rm -f $(docker ps -aq --filter "name=mem0") 2>/dev/null || true
    docker rm -f $(docker ps -aq --filter "name=gemini") 2>/dev/null || true
    
    log_success "环境清理完成"
}

# 创建环境配置
create_env_config() {
    log_step "创建环境配置"
    
    cd mem0-deployment
    
    # 创建.env文件
    cat > .env << 'EOF'
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

# Mem0 API配置
MEM0_API_PORT=8888
MEM0_API_KEY=local_api_key
EOF
    
    cd ..
    
    log_success "环境配置创建完成"
}

# 创建统一网络
create_unified_network() {
    log_step "创建统一Docker网络"

    # 删除可能存在的旧网络
    docker network rm mem0-unified-network 2>/dev/null || true

    # 创建新网络
    docker network create mem0-unified-network

    log_success "统一网络创建完成"
}

# 安装Gemini Balance
install_gemini_balance() {
    log_step "安装Gemini Balance AI服务"

    cd gemini-balance

    # 确保配置文件存在
    if [ ! -f ".env" ]; then
        cp .env.example .env 2>/dev/null || true
    fi

    # 确保使用统一网络
    if ! grep -q "mem0-unified-network" docker-compose.yml; then
        cat >> docker-compose.yml << 'EOF'

networks:
  default:
    external: true
    name: mem0-unified-network
EOF
    fi

    # 启动Gemini Balance
    log_info "启动Gemini Balance..."
    docker compose up -d
    
    # 等待服务启动
    log_info "等待Gemini Balance启动..."
    for i in {1..12}; do
        if curl -s http://localhost:8000 >/dev/null 2>&1; then
            log_success "Gemini Balance启动成功"
            cd ..
            return 0
        fi
        log_info "等待Gemini Balance启动... ($i/12)"
        sleep 10
    done
    
    log_warning "Gemini Balance启动超时，但继续安装"
    cd ..
}

# 安装统一Mem0系统
install_unified_mem0() {
    log_step "安装统一Mem0系统（包含WebUI）"
    
    cd mem0-deployment
    
    # 启动所有服务
    log_info "启动所有Mem0服务..."
    docker compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查PostgreSQL
    log_info "等待PostgreSQL就绪..."
    for i in {1..10}; do
        if docker exec mem0-postgres pg_isready -U mem0 -d mem0 >/dev/null 2>&1; then
            log_success "PostgreSQL就绪"
            break
        fi
        log_info "等待PostgreSQL... ($i/10)"
        sleep 5
    done
    
    # 等待Mem0 API
    log_info "等待Mem0 API就绪..."
    for i in {1..15}; do
        if curl -s http://localhost:8888 >/dev/null 2>&1; then
            log_success "Mem0 API就绪"
            break
        fi
        log_info "等待Mem0 API... ($i/15)"
        sleep 10
    done
    
    # 等待WebUI
    log_info "等待WebUI就绪..."
    for i in {1..15}; do
        if curl -s http://localhost:8503 >/dev/null 2>&1; then
            log_success "WebUI就绪"
            break
        fi
        log_info "等待WebUI... ($i/15)"
        sleep 10
    done

    # 初始化WebUI数据库配置
    log_info "初始化WebUI数据库配置..."
    sleep 5  # 确保WebUI完全启动

    # 确保admin用户和AI服务配置存在
    docker exec mem0-postgres psql -U mem0 -d mem0 -c "
        INSERT INTO webui_user_settings (username, setting_key, setting_value)
        VALUES ('admin', 'ai_api_url', 'http://gemini-balance:8000')
        ON CONFLICT (username, setting_key) DO UPDATE SET
        setting_value = EXCLUDED.setting_value,
        updated_at = CURRENT_TIMESTAMP;

        INSERT INTO webui_user_settings (username, setting_key, setting_value)
        VALUES ('admin', 'ai_api_key', 'q1q2q3q4')
        ON CONFLICT (username, setting_key) DO UPDATE SET
        setting_value = EXCLUDED.setting_value,
        updated_at = CURRENT_TIMESTAMP;
    " || log_warning "WebUI配置初始化可能失败，但继续安装"

    log_success "WebUI数据库配置完成"

    cd ..

    log_success "统一Mem0系统安装完成"
}

# 验证安装
verify_installation() {
    log_step "验证安装结果"
    
    local all_ok=true
    
    # 检查容器状态
    log_info "检查容器状态..."
    local containers=("mem0-postgres" "mem0-qdrant" "mem0-neo4j" "mem0-api" "mem0-webui" "gemini-balance")
    
    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q $container; then
            log_success "✅ $container 运行正常"
        else
            log_error "❌ $container 未运行"
            all_ok=false
        fi
    done
    
    # 检查服务响应
    log_info "检查服务响应..."
    
    if curl -s http://localhost:8000 >/dev/null 2>&1; then
        log_success "✅ Gemini Balance (8000) 响应正常"
    else
        log_warning "⚠️ Gemini Balance (8000) 响应异常"
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
    
    # 检查数据库连接
    if docker exec mem0-postgres psql -U mem0 -d mem0 -c "SELECT 1" >/dev/null 2>&1; then
        log_success "✅ 数据库连接正常"
    else
        log_error "❌ 数据库连接异常"
        all_ok=false
    fi
    
    if $all_ok; then
        log_success "🎉 安装验证通过！"
        return 0
    else
        log_warning "⚠️ 部分服务有问题"
        return 1
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo "============================================================================="
    echo "🎉 Mem0 统一系统安装完成！"
    echo "============================================================================="
    echo ""
    echo "访问地址："
    echo "  🌐 WebUI: http://localhost:8503"
    echo "  🔌 Mem0 API: http://localhost:8888"
    echo "  🤖 Gemini Balance: http://localhost:8000"
    echo "  📊 Neo4j Browser: http://localhost:7474 (neo4j/password)"
    echo "  🔍 Qdrant: http://localhost:6333"
    echo ""
    echo "管理命令："
    echo "  查看状态: docker ps"
    echo "  查看日志: docker logs <容器名>"
    echo "  停止服务: cd mem0-deployment && docker compose down"
    echo "  重启服务: cd mem0-deployment && docker compose restart"
    echo ""
    echo "特点："
    echo "  ✅ 所有服务统一管理"
    echo "  ✅ 共享同一个网络"
    echo "  ✅ 共享同一个数据库"
    echo "  ✅ 简化的配置管理"
    echo ""
}

# 主函数
main() {
    echo "============================================================================="
    echo "              🧠 Mem0 统一安装脚本"
    echo "============================================================================="
    echo ""
    echo "此脚本将安装完整的Mem0系统，包括："
    echo "  🧠 Mem0 核心API服务"
    echo "  🌐 Mem0 WebUI界面"
    echo "  🤖 Gemini Balance AI服务"
    echo "  🗄️ PostgreSQL数据库"
    echo "  📊 Neo4j图数据库"
    echo "  🔍 Qdrant向量数据库"
    echo ""
    echo "特点："
    echo "  ✅ 统一的docker-compose管理"
    echo "  ✅ 共享网络和数据库"
    echo "  ✅ 简化的安装过程"
    echo "  ✅ 减少配置冲突"
    echo ""
    
    if [[ "$1" != "--auto" ]]; then
        read -p "是否继续安装？(y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "安装已取消"
            exit 0
        fi
    fi
    
    check_requirements
    clean_environment
    create_env_config
    create_unified_network
    install_gemini_balance
    install_unified_mem0
    
    if verify_installation; then
        show_completion
    else
        echo ""
        echo "⚠️ 安装完成但部分服务可能需要调整"
        echo "请检查日志: docker logs <容器名>"
        show_completion
    fi
}

# 运行主函数
main "$@"
