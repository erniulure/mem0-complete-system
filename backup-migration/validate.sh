#!/bin/bash

# =============================================================================
# Mem0 系统验证脚本
# 版本: 1.0.0
# 作者: Mem0 Team
# 描述: 验证Mem0系统的完整性和功能
# =============================================================================

set -euo pipefail

# 导入工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/backup-utils.sh"

# 验证结果
VALIDATION_RESULTS=()
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# =============================================================================
# 帮助信息
# =============================================================================

show_help() {
    cat << EOF
Mem0 系统验证脚本

用法: $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -q, --quiet         静默模式，只显示结果
    -v, --verbose       详细模式，显示所有检查详情
    --api-only          仅验证API功能
    --data-only         仅验证数据完整性
    --config-only       仅验证配置文件
    --debug             启用调试模式

验证内容:
    ✓ Docker服务状态
    ✓ 数据库连接性
    ✓ API接口功能
    ✓ 配置文件完整性
    ✓ 数据一致性
    ✓ 网络连通性

EOF
}

# =============================================================================
# 验证函数
# =============================================================================

# 记录验证结果
record_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [[ "$status" == "PASS" ]]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        success "✅ $test_name: $message"
    else
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        error "❌ $test_name: $message"
    fi
    
    VALIDATION_RESULTS+=("$status|$test_name|$message")
}

# 验证Docker服务
validate_docker_services() {
    info "验证Docker服务状态..."
    
    local services=("mem0-qdrant" "mem0-postgres" "mem0-api" "mem0-webui")
    
    for service in "${services[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
            if docker ps --format "{{.Names}}\t{{.Status}}" | grep "^${service}" | grep -q "Up"; then
                record_result "Docker服务-$service" "PASS" "运行正常"
            else
                record_result "Docker服务-$service" "FAIL" "服务已停止"
            fi
        else
            record_result "Docker服务-$service" "FAIL" "容器不存在"
        fi
    done
}

# 验证Qdrant数据库
validate_qdrant() {
    info "验证Qdrant向量数据库..."
    
    # 检查连接性
    if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
        record_result "Qdrant连接" "PASS" "连接成功"
        
        # 检查collections
        local collections=$(curl -s http://localhost:6333/collections | jq -r '.result.collections[].name' 2>/dev/null || echo "")
        if [[ -n "$collections" ]]; then
            local count=$(echo "$collections" | wc -l)
            record_result "Qdrant数据" "PASS" "发现 $count 个collections"
            
            # 验证每个collection的状态
            while IFS= read -r collection; do
                if [[ -n "$collection" ]]; then
                    local info=$(curl -s "http://localhost:6333/collections/$collection" 2>/dev/null)
                    local points_count=$(echo "$info" | jq -r '.result.points_count' 2>/dev/null || echo "0")
                    local status=$(echo "$info" | jq -r '.result.status' 2>/dev/null || echo "unknown")
                    
                    if [[ "$status" == "green" ]]; then
                        record_result "Collection-$collection" "PASS" "$points_count 个向量点，状态正常"
                    else
                        record_result "Collection-$collection" "FAIL" "状态异常: $status"
                    fi
                fi
            done <<< "$collections"
        else
            record_result "Qdrant数据" "FAIL" "未发现collections"
        fi
    else
        record_result "Qdrant连接" "FAIL" "无法连接到Qdrant服务"
    fi
}

# 验证PostgreSQL数据库
validate_postgres() {
    info "验证PostgreSQL数据库..."
    
    # 检查连接性
    if docker exec mem0-postgres pg_isready -U mem0 >/dev/null 2>&1; then
        record_result "PostgreSQL连接" "PASS" "连接成功"

        # 检查Mem0核心数据库
        if docker exec mem0-postgres psql -U mem0 -l 2>/dev/null | grep -q "mem0"; then
            record_result "PostgreSQL-Mem0数据库" "PASS" "mem0数据库存在"

            # 检查Mem0表结构
            local mem0_tables=$(docker exec mem0-postgres psql -U mem0 -d mem0 -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';" 2>/dev/null | tr -d ' ' | grep -v '^$' || echo "")
            if [[ -n "$mem0_tables" ]]; then
                local mem0_table_count=$(echo "$mem0_tables" | wc -l)
                record_result "PostgreSQL-Mem0表结构" "PASS" "发现 $mem0_table_count 个表"
            else
                record_result "PostgreSQL-Mem0表结构" "WARN" "未发现表（可能是新安装）"
            fi
        else
            record_result "PostgreSQL-Mem0数据库" "FAIL" "mem0数据库不存在"
        fi

        # 检查WebUI数据库
        if docker exec mem0-postgres psql -U mem0 -l 2>/dev/null | grep -q "webui"; then
            record_result "PostgreSQL-WebUI数据库" "PASS" "webui数据库存在"

            # 检查WebUI表结构
            local webui_tables=$(docker exec mem0-postgres psql -U mem0 -d webui -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';" 2>/dev/null | tr -d ' ' | grep -v '^$' || echo "")
            if [[ -n "$webui_tables" ]]; then
                local webui_table_count=$(echo "$webui_tables" | wc -l)
                record_result "PostgreSQL-WebUI表结构" "PASS" "发现 $webui_table_count 个表"
            else
                record_result "PostgreSQL-WebUI表结构" "WARN" "未发现表（可能是新安装）"
            fi
        else
            record_result "PostgreSQL-WebUI数据库" "FAIL" "webui数据库不存在"
        fi
    else
        record_result "PostgreSQL连接" "FAIL" "无法连接到PostgreSQL服务"
    fi
}

# 验证Mem0 API
validate_mem0_api() {
    info "验证Mem0 API功能..."
    
    # 检查API连接性
    if curl -s http://localhost:8888/health >/dev/null 2>&1; then
        record_result "Mem0 API连接" "PASS" "API服务可访问"
        
        # 测试获取记忆列表
        local response=$(curl -s "http://localhost:8888/memories?user_id=test_user&limit=1" 2>/dev/null || echo "")
        if [[ -n "$response" ]]; then
            record_result "Mem0 API功能" "PASS" "记忆接口正常"
        else
            record_result "Mem0 API功能" "FAIL" "记忆接口异常"
        fi
        
        # 测试搜索功能
        local search_response=$(curl -s -X POST http://localhost:8888/search \
            -H "Content-Type: application/json" \
            -d '{"query": "test", "user_id": "test_user", "limit": 1}' 2>/dev/null || echo "")
        if [[ -n "$search_response" ]]; then
            record_result "Mem0搜索功能" "PASS" "搜索接口正常"
        else
            record_result "Mem0搜索功能" "FAIL" "搜索接口异常"
        fi
    else
        record_result "Mem0 API连接" "FAIL" "无法连接到Mem0 API服务"
    fi
}

# 验证WebUI
validate_webui() {
    info "验证WebUI服务..."
    
    if curl -s http://localhost:8503 >/dev/null 2>&1; then
        record_result "WebUI服务" "PASS" "WebUI可访问"
    else
        record_result "WebUI服务" "FAIL" "WebUI不可访问"
    fi
}

# 验证配置文件
validate_configs() {
    info "验证配置文件..."
    
    local config_files=(
        "$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml"
        "$PROJECT_ROOT/mem0-deployment/docker-compose.yml"
        "$PROJECT_ROOT/mem0-deployment/.env"
    )
    
    for config_file in "${config_files[@]}"; do
        local filename=$(basename "$config_file")
        if [[ -f "$config_file" ]]; then
            # 检查文件是否为空
            if [[ -s "$config_file" ]]; then
                record_result "配置文件-$filename" "PASS" "文件存在且非空"
            else
                record_result "配置文件-$filename" "FAIL" "文件为空"
            fi
        else
            record_result "配置文件-$filename" "FAIL" "文件不存在"
        fi
    done
    
    # 验证YAML配置文件语法
    if command -v python3 >/dev/null 2>&1; then
        if [[ -f "$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml" ]]; then
            if python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml'))" 2>/dev/null; then
                record_result "YAML语法检查" "PASS" "mem0-config.yaml语法正确"
            else
                record_result "YAML语法检查" "FAIL" "mem0-config.yaml语法错误"
            fi
        fi
    fi
}

# 验证网络连通性
validate_network() {
    info "验证网络连通性..."
    
    local endpoints=(
        "localhost:6333|Qdrant"
        "localhost:5432|PostgreSQL"
        "localhost:8888|Mem0 API"
        "localhost:8503|WebUI"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local addr=$(echo "$endpoint" | cut -d'|' -f1)
        local name=$(echo "$endpoint" | cut -d'|' -f2)
        local host=$(echo "$addr" | cut -d':' -f1)
        local port=$(echo "$addr" | cut -d':' -f2)
        
        if timeout 5 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
            record_result "网络连通-$name" "PASS" "$addr 端口开放"
        else
            record_result "网络连通-$name" "FAIL" "$addr 端口不可达"
        fi
    done
}

# 验证系统资源
validate_system_resources() {
    info "验证系统资源..."
    
    # 检查磁盘空间
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -lt 90 ]]; then
        record_result "磁盘空间" "PASS" "使用率 ${disk_usage}%"
    else
        record_result "磁盘空间" "FAIL" "使用率过高 ${disk_usage}%"
    fi
    
    # 检查内存使用
    local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $mem_usage -lt 90 ]]; then
        record_result "内存使用" "PASS" "使用率 ${mem_usage}%"
    else
        record_result "内存使用" "FAIL" "使用率过高 ${mem_usage}%"
    fi
    
    # 检查Docker资源
    local docker_containers=$(docker ps -q | wc -l)
    record_result "Docker容器" "PASS" "运行中容器: $docker_containers"
}

# =============================================================================
# 报告生成
# =============================================================================

generate_report() {
    echo
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                      验证报告                                ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    echo -e "${BLUE}📊 验证统计:${NC}"
    echo -e "  总检查项: ${YELLOW}$TOTAL_CHECKS${NC}"
    echo -e "  通过项目: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "  失败项目: ${RED}$FAILED_CHECKS${NC}"
    echo -e "  成功率: ${YELLOW}$(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%${NC}"
    echo
    
    if [[ $FAILED_CHECKS -gt 0 ]]; then
        echo -e "${RED}❌ 失败的检查项:${NC}"
        for result in "${VALIDATION_RESULTS[@]}"; do
            local status=$(echo "$result" | cut -d'|' -f1)
            local name=$(echo "$result" | cut -d'|' -f2)
            local message=$(echo "$result" | cut -d'|' -f3)
            
            if [[ "$status" == "FAIL" ]]; then
                echo -e "  • ${RED}$name${NC}: $message"
            fi
        done
        echo
    fi
    
    # 总体状态
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}🎉 系统验证通过！所有检查项目都正常。${NC}"
        return 0
    elif [[ $FAILED_CHECKS -lt 3 ]]; then
        echo -e "${YELLOW}⚠️  系统基本正常，但有少量问题需要关注。${NC}"
        return 1
    else
        echo -e "${RED}🚨 系统存在严重问题，请检查失败项目。${NC}"
        return 2
    fi
}

# =============================================================================
# 主函数
# =============================================================================

main() {
    # 解析参数
    local api_only=false
    local data_only=false
    local config_only=false
    local verbose=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --api-only)
                api_only=true
                shift
                ;;
            --data-only)
                data_only=true
                shift
                ;;
            --config-only)
                config_only=true
                shift
                ;;
            --debug)
                DEBUG=1
                shift
                ;;
            *)
                error "未知参数: $1"
                echo "使用 $0 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done
    
    # 初始化
    init_log
    
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${CYAN}"
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║                    Mem0 系统验证工具                        ║"
        echo "║                     版本: 1.0.0                            ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
    
    info "开始系统验证..."
    
    # 执行验证
    if [[ "$config_only" == "true" ]]; then
        validate_configs
    elif [[ "$data_only" == "true" ]]; then
        validate_qdrant
        validate_postgres
    elif [[ "$api_only" == "true" ]]; then
        validate_mem0_api
        validate_webui
    else
        # 完整验证
        validate_docker_services
        validate_qdrant
        validate_postgres
        validate_mem0_api
        validate_webui
        validate_configs
        validate_network
        validate_system_resources
    fi
    
    # 生成报告
    generate_report
}

# 执行主函数
main "$@"
