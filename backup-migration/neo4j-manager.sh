#!/bin/bash

# =============================================================================
# Neo4j 图数据库管理工具
# 专门用于Mem0系统中Neo4j的备份、恢复和管理
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
    echo -e "${BLUE}[NEO4J-MGR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[NEO4J-MGR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[NEO4J-MGR]${NC} $1"
}

log_error() {
    echo -e "${RED}[NEO4J-MGR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "Neo4j 图数据库管理工具"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  status      显示Neo4j状态"
    echo "  backup      备份Neo4j数据"
    echo "  restore     恢复Neo4j数据"
    echo "  reset       重置Neo4j数据库"
    echo "  stats       显示数据统计"
    echo "  query       执行Cypher查询"
    echo "  browser     打开Neo4j Browser"
    echo "  logs        查看Neo4j日志"
    echo ""
    echo "选项:"
    echo "  -h, --help  显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 status                    # 查看状态"
    echo "  $0 backup /path/to/backup    # 备份到指定路径"
    echo "  $0 restore /path/to/backup   # 从指定路径恢复"
    echo "  $0 query \"MATCH (n) RETURN count(n)\"  # 执行查询"
}

# 检查Neo4j状态
check_neo4j_status() {
    if ! docker ps | grep -q "mem0-neo4j"; then
        log_error "Neo4j容器未运行"
        return 1
    fi
    
    if ! docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
        log_error "无法连接到Neo4j"
        return 1
    fi
    
    return 0
}

# 显示Neo4j状态
show_status() {
    log_info "检查Neo4j状态..."
    
    # 检查容器状态
    if docker ps | grep -q "mem0-neo4j"; then
        log_success "Neo4j容器正在运行"
        
        # 检查连接
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
            log_success "Neo4j数据库连接正常"
            
            # 显示版本信息
            local version=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "CALL dbms.components() YIELD name, versions RETURN versions[0] as version" 2>/dev/null | tail -1 | tr -d '"')
            log_info "Neo4j版本: $version"
            
            # 显示数据统计
            show_stats
            
        else
            log_error "Neo4j数据库连接失败"
        fi
    else
        log_error "Neo4j容器未运行"
    fi
}

# 显示数据统计
show_stats() {
    log_info "数据统计:"
    
    # 节点数量
    local node_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
    echo "  节点数量: $node_count"
    
    # 关系数量
    local rel_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN count(r) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
    echo "  关系数量: $rel_count"
    
    # 标签统计
    echo "  节点标签:"
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "CALL db.labels() YIELD label RETURN label" 2>/dev/null | grep -v "^label$" | sed 's/^/    - /' || echo "    无"
    
    # 关系类型统计
    echo "  关系类型:"
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType" 2>/dev/null | grep -v "^relationshipType$" | sed 's/^/    - /' || echo "    无"
    
    # 索引数量
    local index_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "SHOW INDEXES YIELD name RETURN count(name) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
    echo "  索引数量: $index_count"
}

# 备份Neo4j数据
backup_neo4j() {
    local backup_path="$1"
    
    if [[ -z "$backup_path" ]]; then
        log_error "请指定备份路径"
        return 1
    fi
    
    log_info "开始备份Neo4j到: $backup_path"
    
    if ! check_neo4j_status; then
        return 1
    fi
    
    # 创建备份目录
    mkdir -p "$backup_path"
    
    # 导出数据
    log_info "导出图数据..."
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    CALL apoc.export.csv.all('/tmp/neo4j-backup.csv', {})
    " >/dev/null 2>&1 && docker cp mem0-neo4j:/tmp/neo4j-backup.csv "$backup_path/" || log_warning "CSV导出失败"
    
    # 导出索引和约束
    log_info "导出索引和约束..."
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties
    " > "$backup_path/indexes.cypher" 2>/dev/null || true
    
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties
    " >> "$backup_path/constraints.cypher" 2>/dev/null || true
    
    # 创建备份信息
    cat > "$backup_path/backup-info.txt" << EOF
Neo4j备份信息
备份时间: $(date)
节点数量: $(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"')
关系数量: $(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN count(r) as count" 2>/dev/null | tail -1 | tr -d '"')
EOF
    
    log_success "Neo4j备份完成"
}

# 恢复Neo4j数据
restore_neo4j() {
    local backup_path="$1"
    
    if [[ -z "$backup_path" ]]; then
        log_error "请指定备份路径"
        return 1
    fi
    
    if [[ ! -d "$backup_path" ]]; then
        log_error "备份路径不存在: $backup_path"
        return 1
    fi
    
    log_info "开始从备份恢复Neo4j: $backup_path"
    
    if ! check_neo4j_status; then
        return 1
    fi
    
    # 清空现有数据
    log_warning "清空现有数据..."
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    MATCH (n) DETACH DELETE n
    " >/dev/null 2>&1 || true
    
    # 恢复索引和约束
    if [[ -f "$backup_path/indexes.cypher" ]]; then
        log_info "恢复索引..."
        docker exec -i mem0-neo4j cypher-shell -u neo4j -p password < "$backup_path/indexes.cypher" >/dev/null 2>&1 || true
    fi
    
    if [[ -f "$backup_path/constraints.cypher" ]]; then
        log_info "恢复约束..."
        docker exec -i mem0-neo4j cypher-shell -u neo4j -p password < "$backup_path/constraints.cypher" >/dev/null 2>&1 || true
    fi
    
    # 恢复数据
    if [[ -f "$backup_path/neo4j-backup.csv" ]]; then
        log_info "恢复数据..."
        docker cp "$backup_path/neo4j-backup.csv" mem0-neo4j:/tmp/
        docker exec mem0-neo4j cypher-shell -u neo4j -p password "
        CALL apoc.import.csv([{fileName: '/tmp/neo4j-backup.csv', labels: ['Data']}], [], {})
        " >/dev/null 2>&1 || log_warning "数据恢复失败"
    fi
    
    log_success "Neo4j恢复完成"
    show_stats
}

# 重置Neo4j数据库
reset_neo4j() {
    log_warning "这将删除所有Neo4j数据！"
    read -p "确认继续？(y/N): " confirm
    
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_info "操作已取消"
        return 0
    fi
    
    if ! check_neo4j_status; then
        return 1
    fi
    
    log_info "重置Neo4j数据库..."
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    MATCH (n) DETACH DELETE n
    " >/dev/null 2>&1 || true
    
    log_success "Neo4j数据库已重置"
}

# 执行Cypher查询
execute_query() {
    local query="$1"
    
    if [[ -z "$query" ]]; then
        log_error "请提供Cypher查询"
        return 1
    fi
    
    if ! check_neo4j_status; then
        return 1
    fi
    
    log_info "执行查询: $query"
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "$query"
}

# 打开Neo4j Browser
open_browser() {
    log_info "Neo4j Browser访问信息:"
    echo "  URL: http://localhost:7474"
    echo "  用户名: neo4j"
    echo "  密码: password"
    echo ""
    echo "如果在本地环境，可以直接访问上述URL"
}

# 查看Neo4j日志
show_logs() {
    log_info "显示Neo4j日志..."
    docker logs mem0-neo4j --tail 50 -f
}

# 主函数
main() {
    case "${1:-}" in
        "status")
            show_status
            ;;
        "backup")
            backup_neo4j "$2"
            ;;
        "restore")
            restore_neo4j "$2"
            ;;
        "reset")
            reset_neo4j
            ;;
        "stats")
            show_stats
            ;;
        "query")
            execute_query "$2"
            ;;
        "browser")
            open_browser
            ;;
        "logs")
            show_logs
            ;;
        "-h"|"--help"|"help"|"")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
