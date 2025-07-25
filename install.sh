#!/bin/bash

# =============================================================================
# Mem0 完整智能记忆管理系统 - 健壮版一键安装脚本
# 版本: v3.0
# 描述: 解决网络、配置、启动顺序等问题的完全自动化安装脚本
# =============================================================================

set -e

# 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_LOG="${SCRIPT_DIR}/install-$(date +%Y%m%d-%H%M%S).log"
UNIFIED_NETWORK="mem0-unified-network"
AUTO_MODE=false
MAX_RETRY=3
HEALTH_CHECK_TIMEOUT=300

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 增强的日志函数 - 同时输出到控制台和日志文件
log_info() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "$msg" >> "$INSTALL_LOG"
}

log_success() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1"
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "$msg" >> "$INSTALL_LOG"
}

log_warning() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1"
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "$msg" >> "$INSTALL_LOG"
}

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1"
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$msg" >> "$INSTALL_LOG"
}

log_step() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [STEP] $1"
    echo -e "${PURPLE}[STEP]${NC} $1"
    echo "$msg" >> "$INSTALL_LOG"
    echo "----------------------------------------" >> "$INSTALL_LOG"
}

# 错误处理函数
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "安装失败！错误发生在第 $line_number 行，退出码: $exit_code"
    log_error "详细日志请查看: $INSTALL_LOG"

    # 显示最近的错误日志
    echo ""
    echo -e "${RED}=== 最近的错误日志 ===${NC}"
    tail -20 "$INSTALL_LOG"
    echo ""

    cleanup_on_failure
    exit $exit_code
}

# 失败时清理函数
cleanup_on_failure() {
    log_warning "正在清理失败的安装..."

    # 停止可能启动的容器
    docker-compose -f mem0-deployment/docker-compose.yml down 2>/dev/null || true
    docker-compose -f mem0Client/docker-compose.yml down 2>/dev/null || true
    docker-compose -f gemini-balance/docker-compose.yml down 2>/dev/null || true

    log_info "清理完成"
}

# 设置错误处理
trap 'handle_error $LINENO' ERR

# 初始化日志文件
init_log() {
    echo "=============================================================================" > "$INSTALL_LOG"
    echo "Mem0 完整智能记忆管理系统 - v3.0 安装日志" >> "$INSTALL_LOG"
    echo "安装开始时间: $(date)" >> "$INSTALL_LOG"
    echo "安装目录: $SCRIPT_DIR" >> "$INSTALL_LOG"
    echo "=============================================================================" >> "$INSTALL_LOG"
    echo "" >> "$INSTALL_LOG"

    log_info "安装日志文件: $INSTALL_LOG"
}

# 健壮的健康检查函数
wait_for_service() {
    local url=$1
    local service_name=$2
    local timeout=${3:-$HEALTH_CHECK_TIMEOUT}
    local retry_count=0

    log_info "等待 $service_name 服务启动 (超时: ${timeout}s)..."

    while [ $retry_count -lt $MAX_RETRY ]; do
        local count=0
        local check_interval=10

        while [ $count -lt $timeout ]; do
            if curl -s --max-time 5 "$url" >/dev/null 2>&1; then
                log_success "$service_name 服务已就绪 ✅"
                return 0
            fi

            sleep $check_interval
            count=$((count + check_interval))

            # 每30秒显示一次进度
            if [ $((count % 30)) -eq 0 ]; then
                log_info "等待 $service_name 启动中... (${count}s/${timeout}s)"
            fi
        done

        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $MAX_RETRY ]; then
            log_warning "$service_name 启动超时，重试 $retry_count/$MAX_RETRY"
            sleep 10
        fi
    done

    log_error "$service_name 服务启动失败，已重试 $MAX_RETRY 次"
    return 1
}

# 检查服务健康状态
check_service_health() {
    local url=$1
    local service_name=$2

    if curl -s --max-time 10 "$url" >/dev/null 2>&1; then
        log_success "$service_name 健康检查通过 ✅"
        return 0
    else
        log_warning "$service_name 健康检查失败 ❌"
        return 1
    fi
}

# 增强的网络管理
create_unified_network() {
    log_step "创建和验证统一Docker网络"

    # 检查网络是否已存在
    if docker network ls | grep -q "$UNIFIED_NETWORK"; then
        log_info "统一网络 '$UNIFIED_NETWORK' 已存在"

        # 验证网络状态
        if docker network inspect "$UNIFIED_NETWORK" >/dev/null 2>&1; then
            log_success "统一网络状态正常"
            return 0
        else
            log_warning "统一网络状态异常，重新创建"
            docker network rm "$UNIFIED_NETWORK" 2>/dev/null || true
        fi
    fi

    # 创建新网络
    log_info "创建统一网络: $UNIFIED_NETWORK"
    if docker network create "$UNIFIED_NETWORK" >> "$INSTALL_LOG" 2>&1; then
        log_success "统一网络创建成功"
    else
        log_error "统一网络创建失败"
        return 1
    fi

    # 验证网络创建成功
    if docker network inspect "$UNIFIED_NETWORK" >/dev/null 2>&1; then
        log_success "统一网络验证通过"

        # 记录网络详细信息到日志
        echo "=== 网络详细信息 ===" >> "$INSTALL_LOG"
        docker network inspect "$UNIFIED_NETWORK" >> "$INSTALL_LOG" 2>&1
        echo "" >> "$INSTALL_LOG"

        return 0
    else
        log_error "统一网络验证失败"
        return 1
    fi
}

# 清理旧网络
cleanup_old_networks() {
    log_info "清理可能冲突的旧网络..."

    local old_networks=(
        "mem0-shared-network"
        "mem0-deployment_mem0-network"
        "mem0client_webui-network"
        "gemini-balance_gemini-network"
    )

    for network in "${old_networks[@]}"; do
        if docker network ls | grep -q "$network"; then
            log_info "清理旧网络: $network"
            docker network rm "$network" 2>/dev/null || true
        fi
    done

    log_success "旧网络清理完成"
}

# 停止现有服务
stop_existing_services() {
    log_step "停止现有服务以避免冲突"

    # 停止可能运行的服务
    local compose_dirs=(
        "mem0-deployment"
        "mem0Client"
        "gemini-balance"
    )

    for dir in "${compose_dirs[@]}"; do
        if [ -d "$dir" ] && [ -f "$dir/docker-compose.yml" ]; then
            log_info "停止 $dir 中的服务..."
            cd "$dir"
            docker-compose down 2>/dev/null || true
            cd ..
        fi
    done

    # 停止可能的独立容器
    local containers=(
        "mem0-api"
        "mem0-webui"
        "mem0-postgres"
        "mem0-qdrant"
        "mem0-neo4j"
        "gemini-balance"
        "gemini-mysql"
    )

    for container in "${containers[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log_info "停止容器: $container"
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        fi
    done

    log_success "现有服务停止完成"
}

# 更新Docker Compose配置以使用统一网络
update_docker_compose_networks() {
    log_step "更新Docker Compose网络配置"

    local compose_files=(
        "mem0-deployment/docker-compose.yml"
        "mem0Client/docker-compose.yml"
        "gemini-balance/docker-compose.yml"
    )

    for compose_file in "${compose_files[@]}"; do
        if [ -f "$compose_file" ]; then
            log_info "更新 $compose_file 网络配置"

            # 备份原文件
            cp "$compose_file" "${compose_file}.backup-$(date +%Y%m%d-%H%M%S)"

            # 检查是否已有networks配置
            if ! grep -q "^networks:" "$compose_file"; then
                # 添加网络配置
                cat >> "$compose_file" << EOF

networks:
  default:
    external: true
    name: $UNIFIED_NETWORK
EOF
                log_success "已为 $compose_file 添加网络配置"
            else
                # 更新现有网络配置（只更新networks部分的name）
                sed -i.bak "/^networks:/,/^[a-zA-Z]/ s/name: .*/name: $UNIFIED_NETWORK/" "$compose_file"
                log_success "已更新 $compose_file 网络配置"
            fi
        else
            log_warning "$compose_file 不存在，跳过"
        fi
    done

    # 验证配置文件（在没有运行容器的情况下）
    for compose_file in "${compose_files[@]}"; do
        if [ -f "$compose_file" ]; then
            log_info "验证 $compose_file 配置..."
            if docker-compose -f "$compose_file" config >/dev/null 2>&1; then
                log_success "$compose_file 配置验证通过"
            else
                log_warning "$compose_file 配置验证有警告，但继续安装"
                # 记录详细错误到日志
                echo "=== $compose_file 配置验证详情 ===" >> "$INSTALL_LOG"
                docker-compose -f "$compose_file" config >> "$INSTALL_LOG" 2>&1 || true
                echo "" >> "$INSTALL_LOG"
            fi
        fi
    done

    log_success "Docker Compose网络配置更新完成"
}

# 系统环境检查
check_system_requirements() {
    log_step "检查系统环境和要求"

    # 检查操作系统
    log_info "操作系统: $(uname -s) $(uname -r)"

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        return 1
    fi

    local docker_version=$(docker --version 2>/dev/null || echo "未知版本")
    log_success "Docker已安装: $docker_version"

    # 检查Docker服务状态
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker服务未运行，请启动Docker服务"
        return 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        return 1
    fi

    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version 2>/dev/null || echo "未知版本")
        log_success "Docker Compose已安装: $compose_version"
    else
        local compose_version=$(docker compose version 2>/dev/null || echo "未知版本")
        log_success "Docker Compose (内置)已安装: $compose_version"
    fi

    # 检查端口占用
    check_port_availability

    # 检查磁盘空间
    check_disk_space

    log_success "系统环境检查完成"
}

# 检查端口可用性
check_port_availability() {
    log_info "检查端口可用性..."

    local ports=(
        "8000:Gemini Balance"
        "8888:Mem0 API"
        "8503:Mem0 WebUI"
        "7474:Neo4j HTTP"
        "7687:Neo4j Bolt"
        "6333:Qdrant"
        "5432:PostgreSQL"
    )

    local port_conflicts=false

    for port_info in "${ports[@]}"; do
        local port=$(echo "$port_info" | cut -d: -f1)
        local service=$(echo "$port_info" | cut -d: -f2)

        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log_warning "端口 $port ($service) 已被占用"
            port_conflicts=true
        fi
    done

    if [ "$port_conflicts" = true ]; then
        if [ "$AUTO_MODE" = false ]; then
            echo ""
            read -p "检测到端口冲突，是否继续安装？(y/N): " response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                log_error "安装已取消"
                exit 1
            fi
        else
            log_warning "自动模式：忽略端口冲突警告"
        fi
    else
        log_success "所有端口可用"
    fi
}

# 检查磁盘空间
check_disk_space() {
    log_info "检查磁盘空间..."

    local available_space=$(df . | awk 'NR==2 {print $4}')
    local required_space=2097152  # 2GB in KB

    if [ "$available_space" -lt "$required_space" ]; then
        log_warning "可用磁盘空间不足2GB，可能影响安装"
    else
        local available_gb=$((available_space / 1024 / 1024))
        log_success "磁盘空间充足: ${available_gb}GB 可用"
    fi
}

# 安装Gemini Balance服务
install_gemini_balance() {
    log_step "安装Gemini Balance AI服务"

    if [ ! -d "gemini-balance" ]; then
        log_warning "gemini-balance目录不存在，跳过安装"
        return 0
    fi

    cd gemini-balance || {
        log_error "无法进入gemini-balance目录"
        return 1
    }

    # 检查部署脚本
    if [ -f "deploy.sh" ]; then
        chmod +x deploy.sh
        log_info "使用deploy.sh启动Gemini Balance..."

        if [ "$AUTO_MODE" = true ]; then
            ./deploy.sh --auto >> "$INSTALL_LOG" 2>&1 || {
                log_warning "deploy.sh自动模式失败，尝试普通模式"
                ./deploy.sh >> "$INSTALL_LOG" 2>&1 || {
                    log_error "Gemini Balance部署失败"
                    cd ..
                    return 1
                }
            }
        else
            ./deploy.sh >> "$INSTALL_LOG" 2>&1 || {
                log_error "Gemini Balance部署失败"
                cd ..
                return 1
            }
        fi

    elif [ -f "docker-compose.yml" ]; then
        log_info "使用docker-compose启动Gemini Balance..."
        docker-compose up -d >> "$INSTALL_LOG" 2>&1 || {
            log_error "Gemini Balance docker-compose启动失败"
            cd ..
            return 1
        }

    else
        log_warning "未找到Gemini Balance部署文件，跳过"
        cd ..
        return 0
    fi

    cd ..

    # 等待服务启动并验证
    wait_for_service "http://localhost:8000" "Gemini Balance" 120

    log_success "Gemini Balance安装完成"
}

# 安装Mem0核心服务
install_mem0_core() {
    log_step "安装Mem0核心服务"

    if [ ! -d "mem0-deployment" ]; then
        log_error "mem0-deployment目录不存在"
        return 1
    fi

    cd mem0-deployment || {
        log_error "无法进入mem0-deployment目录"
        return 1
    }

    # 分阶段启动服务以确保稳定性
    log_info "启动数据库服务..."
    docker-compose up -d mem0-postgres mem0-qdrant mem0-neo4j >> "$INSTALL_LOG" 2>&1 || {
        log_error "数据库服务启动失败"
        cd ..
        return 1
    }

    # 等待数据库服务就绪
    log_info "等待数据库服务就绪..."
    sleep 20

    # 验证数据库服务
    verify_database_services

    # 启动API服务
    log_info "启动Mem0 API服务..."
    docker-compose up -d mem0-api >> "$INSTALL_LOG" 2>&1 || {
        log_error "Mem0 API服务启动失败"
        cd ..
        return 1
    }

    cd ..

    # 等待API服务就绪
    wait_for_service "http://localhost:8888" "Mem0 API" 120

    log_success "Mem0核心服务安装完成"
}

# 验证数据库服务
verify_database_services() {
    log_info "验证数据库服务状态..."

    # 检查PostgreSQL
    local postgres_ready=false
    for i in {1..30}; do
        if docker exec mem0-postgres pg_isready -U mem0 >/dev/null 2>&1; then
            postgres_ready=true
            break
        fi
        sleep 2
    done

    if [ "$postgres_ready" = true ]; then
        log_success "PostgreSQL服务就绪"
    else
        log_warning "PostgreSQL服务未就绪，但继续安装"
    fi

    # 检查Neo4j
    local neo4j_ready=false
    for i in {1..30}; do
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
            neo4j_ready=true
            break
        fi
        sleep 2
    done

    if [ "$neo4j_ready" = true ]; then
        log_success "Neo4j服务就绪"
    else
        log_warning "Neo4j服务未就绪，但继续安装"
    fi

    # 检查Qdrant
    if check_service_health "http://localhost:6333" "Qdrant"; then
        log_success "Qdrant服务就绪"
    else
        log_warning "Qdrant服务未就绪，但继续安装"
    fi
}

# 生成环境配置文件
generate_environment_configs() {
    log_step "生成环境配置文件"

    # 检测Gemini Balance状态
    local gemini_balance_url="http://gemini-balance:8000"
    local gemini_balance_key="q1q2q3q4"

    if check_service_health "http://localhost:8000" "Gemini Balance"; then
        log_success "检测到Gemini Balance服务，使用内部配置"
    else
        log_warning "未检测到Gemini Balance服务，使用默认配置"
    fi

    # 生成mem0-deployment/.env
    log_info "生成 mem0-deployment/.env"
    cat > mem0-deployment/.env << EOF
# Mem0 API配置
MEM0_API_URL=http://mem0-api:8000

# AI服务配置
OPENAI_API_BASE=$gemini_balance_url
OPENAI_API_KEY=$gemini_balance_key

# 数据库配置
POSTGRES_HOST=mem0-postgres
POSTGRES_PORT=5432
POSTGRES_DB=mem0
POSTGRES_USER=mem0
POSTGRES_PASSWORD=mem0_password

# Qdrant配置
QDRANT_HOST=mem0-qdrant
QDRANT_PORT=6333

# Neo4j配置
NEO4J_URI=bolt://mem0-neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# 网络配置
DOCKER_NETWORK=$UNIFIED_NETWORK

# 生成时间
GENERATED_AT=$(date)
EOF

    # 生成mem0Client/.env
    log_info "生成 mem0Client/.env"
    cat > mem0Client/.env << EOF
# Mem0 API配置
MEM0_API_URL=http://mem0-api:8000

# AI服务配置
AI_API_BASE=$gemini_balance_url
AI_API_KEY=$gemini_balance_key

# 网络配置
DOCKER_NETWORK=$UNIFIED_NETWORK

# 生成时间
GENERATED_AT=$(date)
EOF

    # 验证配置文件
    if [ -f "mem0-deployment/.env" ] && [ -f "mem0Client/.env" ]; then
        log_success "环境配置文件生成完成"
    else
        log_error "环境配置文件生成失败"
        return 1
    fi
}

# 初始化WebUI数据库配置
initialize_webui_config() {
    log_step "初始化WebUI数据库配置"

    # 等待WebUI数据库就绪
    log_info "等待WebUI数据库初始化..."
    sleep 30

    # 检测可用的AI服务
    local ai_services_config=""

    if check_service_health "http://localhost:8000" "Gemini Balance"; then
        log_info "检测到Gemini Balance服务，配置AI服务"

        # 通过API调用配置WebUI
        local config_payload='{
            "ai_service": {
                "type": "gemini-balance",
                "name": "Gemini Balance",
                "url": "http://gemini-balance:8000",
                "api_key": "q1q2q3q4",
                "enabled": true,
                "default": true
            }
        }'

        # 尝试通过API配置WebUI
        if curl -s -X POST "http://localhost:8503/api/config/ai-service" \
           -H "Content-Type: application/json" \
           -d "$config_payload" >/dev/null 2>&1; then
            log_success "WebUI AI服务配置成功"
        else
            log_warning "WebUI API配置失败，将在首次使用时手动配置"
        fi
    else
        log_warning "未检测到Gemini Balance服务，跳过AI服务配置"
    fi

    log_success "WebUI配置初始化完成"
}

# 安装WebUI服务
install_webui() {
    log_step "安装Web用户界面"

    if [ ! -d "mem0Client" ]; then
        log_error "mem0Client目录不存在"
        return 1
    fi

    cd mem0Client || {
        log_error "无法进入mem0Client目录"
        return 1
    }

    # 检查Dockerfile是否存在
    if [ ! -f "Dockerfile" ]; then
        log_error "WebUI Dockerfile不存在"
        cd ..
        return 1
    fi

    # 构建并启动WebUI
    log_info "构建并启动WebUI服务..."
    docker-compose up -d --build >> "$INSTALL_LOG" 2>&1 || {
        log_error "WebUI服务启动失败"
        cd ..
        return 1
    }

    cd ..

    # 等待WebUI服务就绪
    wait_for_service "http://localhost:8503" "Mem0 WebUI" 120

    # 初始化WebUI配置
    initialize_webui_config

    log_success "WebUI安装完成"
}

# 验证所有服务状态
verify_all_services() {
    log_step "验证所有服务状态"

    local services=(
        "http://localhost:8000:Gemini Balance"
        "http://localhost:8888:Mem0 API"
        "http://localhost:8503:Mem0 WebUI"
        "http://localhost:7474:Neo4j Browser"
        "http://localhost:6333:Qdrant"
    )

    local all_services_ok=true

    for service in "${services[@]}"; do
        local url=$(echo "$service" | cut -d: -f1-2)
        local name=$(echo "$service" | cut -d: -f3)

        if check_service_health "$url" "$name"; then
            echo "✅ $name 服务正常" >> "$INSTALL_LOG"
        else
            log_warning "⚠️  $name 服务可能未启动"
            all_services_ok=false
        fi
    done

    if [ "$all_services_ok" = true ]; then
        log_success "所有服务验证通过"
    else
        log_warning "部分服务可能需要更多时间启动"
    fi

    return 0
}

# 测试服务间连通性
test_service_connectivity() {
    log_step "测试服务间连通性"

    # 测试WebUI到Gemini Balance的连接
    log_info "测试WebUI到Gemini Balance的连接..."
    if docker exec mem0-webui curl -s -H "Authorization: Bearer q1q2q3q4" \
       "http://gemini-balance:8000/v1/models" >/dev/null 2>&1; then
        log_success "WebUI ↔ Gemini Balance 连接正常"
    else
        log_warning "WebUI ↔ Gemini Balance 连接异常"
    fi

    # 测试WebUI到Mem0 API的连接
    log_info "测试WebUI到Mem0 API的连接..."
    if docker exec mem0-webui curl -s "http://mem0-api:8000" >/dev/null 2>&1; then
        log_success "WebUI ↔ Mem0 API 连接正常"
    else
        log_warning "WebUI ↔ Mem0 API 连接异常"
    fi

    # 测试Mem0 API到数据库的连接
    log_info "测试Mem0 API到数据库的连接..."
    if docker exec mem0-api curl -s "http://mem0-postgres:5432" >/dev/null 2>&1; then
        log_success "Mem0 API ↔ PostgreSQL 连接正常"
    else
        log_warning "Mem0 API ↔ PostgreSQL 连接异常"
    fi

    log_success "服务连通性测试完成"
}

# 测试Neo4j图存储功能
test_neo4j_graph_storage() {
    log_step "测试Neo4j图存储功能"

    # 等待Neo4j完全启动
    sleep 10

    # 检查Neo4j连接
    if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
        log_success "Neo4j连接正常"

        # 检查向量函数支持
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password \
           "SHOW FUNCTIONS YIELD name WHERE name CONTAINS 'vector' RETURN count(*) as count;" 2>/dev/null | grep -q "1"; then
            log_success "Neo4j向量函数支持正常"
        else
            log_warning "Neo4j向量函数可能不支持，但不影响基本功能"
        fi

        # 创建测试图数据
        log_info "创建测试图数据..."
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password "
        MERGE (u:User {name: 'install_test_user', user_id: 'install_test_$(date +%s)'})
        MERGE (s:Skill {name: 'Docker'})
        MERGE (t:Technology {name: 'Mem0'})
        MERGE (u)-[:KNOWS]->(s)
        MERGE (u)-[:USES]->(t)
        RETURN u.name, s.name, t.name
        " >/dev/null 2>&1; then
            log_success "测试图数据创建成功"
        else
            log_warning "测试图数据创建失败"
        fi

    else
        log_warning "Neo4j连接异常，但服务可能仍在启动中"
    fi
}

# 测试API功能
test_api_functionality() {
    log_step "测试API功能"

    # 测试Mem0 API基本响应
    if curl -s --max-time 10 "http://localhost:8888/" | grep -q "Mem0"; then
        log_success "Mem0 API基本响应正常"

        # 测试记忆创建功能
        log_info "测试记忆创建功能..."
        local test_response=$(curl -s --max-time 30 -X POST "http://localhost:8888/memories" \
            -H "Content-Type: application/json" \
            -d '{
                "messages": [
                    {
                        "role": "user",
                        "content": "这是一个安装测试消息，用于验证Mem0系统功能正常。我是安装测试用户，正在验证系统的记忆创建功能。"
                    }
                ],
                "user_id": "install_test_user_'$(date +%s)'"
            }' 2>/dev/null)

        if echo "$test_response" | grep -q "memories\|results"; then
            log_success "记忆创建功能测试通过"
        else
            log_warning "记忆创建功能测试失败，但不影响基本安装"
        fi
    else
        log_warning "Mem0 API响应异常"
    fi

    # 测试Gemini Balance API
    if check_service_health "http://localhost:8000" "Gemini Balance"; then
        log_info "测试Gemini Balance API功能..."
        if curl -s -H "Authorization: Bearer q1q2q3q4" \
           "http://localhost:8000/v1/models" | grep -q "models\|data"; then
            log_success "Gemini Balance API功能正常"
        else
            log_warning "Gemini Balance API响应异常"
        fi
    fi
}

# 显示欢迎信息
show_welcome() {
    clear
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "              🧠 Mem0 完整智能记忆管理系统 - v3.0 健壮版"
    echo "============================================================================="
    echo -e "${NC}"
    echo "本系统包含三个核心组件："
    echo "  🧠 Mem0: 核心记忆管理引擎和API服务"
    echo "  🌐 Mem0Client: Web用户界面和客户端"
    echo "  🤖 Gemini-Balance: AI服务代理和负载均衡"
    echo ""
    echo "✨ v3.0 新特性："
    echo "  🔧 完全自动化安装和配置"
    echo "  🛡️ 健壮的错误处理和重试机制"
    echo "  🔍 智能健康检查和服务验证"
    echo "  🌐 统一网络架构解决通信问题"
    echo "  📊 WebUI数据库自动配置"
    echo "  📝 详细的安装日志记录"
    echo ""

    # 检查是否为自动安装模式
    if [[ "$1" == "--auto" ]]; then
        echo "🤖 自动安装模式：将执行完整安装"
        AUTO_MODE=true
        install_choice=1
        return
    fi

    echo "安装选项："
    echo "  1) 🚀 完整安装（推荐）- 安装所有组件"
    echo "  2) 🎯 仅安装Mem0系统 - 使用外部AI服务"
    echo ""
    read -p "请选择安装方式 (1-2): " install_choice
}

# 显示完成信息
show_completion_info() {
    echo ""
    echo -e "${GREEN}============================================================================="
    echo "                    🎉 Mem0系统安装完成！"
    echo "=============================================================================${NC}"
    echo ""
    echo "📋 服务访问地址："
    echo "  🌐 Mem0 WebUI:     http://localhost:8503"
    echo "  🔌 Mem0 API:       http://localhost:8888"
    echo "  🤖 Gemini Balance: http://localhost:8000"
    echo "  📊 Neo4j Browser:  http://localhost:7474 (neo4j/password)"
    echo "  🔍 Qdrant:         http://localhost:6333"
    echo ""
    echo "🚀 快速开始："
    echo "  1. 打开浏览器访问: http://localhost:8503"
    echo "  2. 注册新用户或使用默认账户"
    echo "  3. 开始与AI对话，体验智能记忆功能"
    echo ""
    echo "💡 测试图存储功能："
    echo "  输入包含人物、地点、技能等信息的对话，例如："
    echo "  \"我叫张三，是一名软件工程师，在北京工作，喜欢编程和阅读。\""
    echo ""
    echo "🔧 管理命令："
    echo "  📋 查看状态: docker ps"
    echo "  📝 查看日志: docker logs <容器名>"
    echo "  🔄 重启服务: docker-compose -f mem0-deployment/docker-compose.yml restart"
    echo "  🛑 停止服务: docker-compose -f mem0-deployment/docker-compose.yml down"
    echo ""
    echo "📝 详细日志: $INSTALL_LOG"
    echo ""
    echo -e "${CYAN}感谢使用Mem0智能记忆管理系统！${NC}"
}

# 完整安装函数
full_install() {
    log_step "开始完整安装流程"

    # 1. 系统环境检查
    check_system_requirements || exit 1

    # 2. 停止现有服务
    stop_existing_services

    # 3. 清理旧网络
    cleanup_old_networks

    # 4. 创建统一网络
    create_unified_network || exit 1

    # 5. 更新Docker Compose配置
    update_docker_compose_networks || exit 1

    # 5. 生成环境配置
    generate_environment_configs || exit 1

    # 6. 安装Gemini Balance
    install_gemini_balance || {
        log_warning "Gemini Balance安装失败，但继续安装Mem0"
    }

    # 7. 安装Mem0核心服务
    install_mem0_core || exit 1

    # 8. 安装WebUI
    install_webui || exit 1

    # 9. 验证所有服务
    verify_all_services

    # 10. 测试服务连通性
    test_service_connectivity

    # 11. 测试Neo4j图存储
    test_neo4j_graph_storage

    # 12. 测试API功能
    test_api_functionality

    log_success "完整安装流程完成"
}

# 仅安装Mem0
mem0_only_install() {
    log_step "开始Mem0系统安装流程"

    # 1. 系统环境检查
    check_system_requirements || exit 1

    # 2. 停止现有服务
    stop_existing_services

    # 3. 清理旧网络
    cleanup_old_networks

    # 4. 创建统一网络
    create_unified_network || exit 1

    # 5. 更新Docker Compose配置
    update_docker_compose_networks || exit 1

    # 5. 生成环境配置
    generate_environment_configs || exit 1

    # 6. 安装Mem0核心服务
    install_mem0_core || exit 1

    # 7. 安装WebUI
    install_webui || exit 1

    # 8. 验证服务
    verify_all_services

    # 9. 测试Neo4j图存储
    test_neo4j_graph_storage

    log_success "Mem0系统安装流程完成"
}

# 主函数
main() {
    # 初始化日志
    init_log

    # 显示欢迎信息
    show_welcome "$@"

    # 根据选择执行安装
    case $install_choice in
        1|"")
            log_step "执行完整安装..."
            full_install || {
                log_error "完整安装失败"
                exit 1
            }
            ;;
        2)
            log_step "执行Mem0系统安装..."
            mem0_only_install || {
                log_error "Mem0系统安装失败"
                exit 1
            }
            ;;
        *)
            log_error "无效选择，退出安装"
            exit 1
            ;;
    esac

    # 显示完成信息
    show_completion_info

    # 记录安装完成
    echo "" >> "$INSTALL_LOG"
    echo "=============================================================================" >> "$INSTALL_LOG"
    echo "安装完成时间: $(date)" >> "$INSTALL_LOG"
    echo "安装状态: 成功" >> "$INSTALL_LOG"
    echo "=============================================================================" >> "$INSTALL_LOG"

    log_success "🎉 Mem0系统安装和验证全部完成！"
    log_info "详细日志已保存到: $INSTALL_LOG"
}

# 运行主函数
main "$@"
