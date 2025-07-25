#!/bin/bash

# =============================================================================
# Mem0 简化备份脚本
# 版本: 1.0.0
# 描述: 基于mem0官方文档的简化备份方案
# =============================================================================

set -euo pipefail

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# 创建备份目录
create_backup_dir() {
    info "创建备份目录: $BACKUP_PATH"
    mkdir -p "$BACKUP_PATH"/{qdrant,postgres,neo4j,configs}
}

# 备份Qdrant数据
backup_qdrant() {
    info "备份Qdrant向量数据库..."
    
    # 获取collections
    local collections=$(curl -s http://localhost:6333/collections 2>/dev/null | jq -r '.result.collections[].name' 2>/dev/null || echo "")
    
    if [[ -z "$collections" ]]; then
        warn "未找到Qdrant collections"
        return 0
    fi
    
    # 备份每个collection
    for collection in $collections; do
        info "备份Collection: $collection"
        
        # 创建快照
        local snapshot_result=$(curl -s -X POST "http://localhost:6333/collections/$collection/snapshots" \
            -H "Content-Type: application/json" 2>/dev/null)
        
        local snapshot_name=$(echo "$snapshot_result" | jq -r '.result.name' 2>/dev/null)
        
        if [[ -n "$snapshot_name" && "$snapshot_name" != "null" ]]; then
            # 下载快照
            curl -s "http://localhost:6333/collections/$collection/snapshots/$snapshot_name" \
                -o "$BACKUP_PATH/qdrant/${collection}.snapshot" 2>/dev/null
            
            # 删除远程快照
            curl -s -X DELETE "http://localhost:6333/collections/$collection/snapshots/$snapshot_name" >/dev/null 2>&1
            
            success "Collection $collection 备份完成"
        else
            warn "Collection $collection 快照创建失败"
        fi
    done
}

# 备份PostgreSQL数据
backup_postgres() {
    info "备份PostgreSQL数据库..."
    
    # 备份mem0数据库
    if docker exec mem0-postgres pg_dump -U mem0 mem0 > "$BACKUP_PATH/postgres/mem0.sql" 2>/dev/null; then
        success "mem0数据库备份完成"
    else
        warn "mem0数据库备份失败"
    fi
    
    # 备份webui数据库
    if docker exec mem0-postgres pg_dump -U mem0 webui > "$BACKUP_PATH/postgres/webui.sql" 2>/dev/null; then
        success "webui数据库备份完成"
    else
        warn "webui数据库备份失败"
    fi
    
    # 备份用户权限
    docker exec mem0-postgres pg_dumpall -U mem0 --roles-only > "$BACKUP_PATH/postgres/roles.sql" 2>/dev/null || true
}

# 备份Neo4j数据
backup_neo4j() {
    info "备份Neo4j图数据库..."

    # 检查Neo4j是否运行
    if ! docker ps | grep -q "mem0-neo4j"; then
        warn "Neo4j容器未运行，跳过备份"
        return 0
    fi

    # 检查连接
    if ! docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
        warn "无法连接到Neo4j，跳过备份"
        return 0
    fi

    # 导出图数据
    if docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    CALL apoc.export.csv.all('/tmp/neo4j-export.csv', {})
    " >/dev/null 2>&1; then
        docker cp mem0-neo4j:/tmp/neo4j-export.csv "$BACKUP_PATH/neo4j/" 2>/dev/null || true
        success "Neo4j数据导出完成"
    else
        warn "Neo4j数据导出失败"
    fi

    # 导出索引信息
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties
    " > "$BACKUP_PATH/neo4j/indexes.cypher" 2>/dev/null || true
}

# 备份配置文件
backup_configs() {
    info "备份配置文件..."
    
    local config_files=(
        "$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml"
        "$PROJECT_ROOT/mem0-deployment/docker-compose.yml"
        "$PROJECT_ROOT/mem0-deployment/.env"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            local filename=$(basename "$config_file")
            local dirname=$(basename "$(dirname "$config_file")")
            cp "$config_file" "$BACKUP_PATH/configs/${dirname}_${filename}"
            success "配置文件 $filename 备份完成"
        fi
    done
}

# 生成备份信息
generate_backup_info() {
    info "生成备份信息..."
    
    cat > "$BACKUP_PATH/backup_info.txt" << EOF
Mem0 系统备份信息
================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份名称: $BACKUP_NAME
主机名称: $(hostname)
用户名称: $(whoami)

备份内容:
- Qdrant向量数据库
- PostgreSQL数据库 (mem0, webui)
- Neo4j图数据库
- 配置文件

恢复说明:
1. 确保目标服务器已安装Mem0基础环境
2. 解压备份文件到项目目录
3. 运行恢复脚本: ./simple-restore.sh
EOF
}

# 压缩备份
compress_backup() {
    info "压缩备份文件..."
    
    cd "$BACKUP_DIR" || exit 1
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME" 2>/dev/null
    
    if [[ $? -eq 0 && -f "${BACKUP_NAME}.tar.gz" ]]; then
        local size=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
        success "备份已压缩: ${BACKUP_NAME}.tar.gz (大小: $size)"
        
        # 删除临时目录
        rm -rf "$BACKUP_NAME"
        
        echo "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
        return 0
    else
        error "备份压缩失败"
        return 1
    fi
}

# 主函数
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                  Mem0 简化备份工具                          ║"
    echo "║                   版本: 1.0.0                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    info "开始备份: $BACKUP_NAME"
    
    # 检查服务状态
    if ! curl -s http://localhost:6333/collections >/dev/null 2>&1; then
        error "Qdrant服务不可用，请确保服务正在运行"
        exit 1
    fi
    
    if ! docker exec mem0-postgres pg_isready -U mem0 >/dev/null 2>&1; then
        error "PostgreSQL服务不可用，请确保服务正在运行"
        exit 1
    fi
    
    # 执行备份
    create_backup_dir
    backup_qdrant
    backup_postgres
    backup_neo4j
    backup_configs
    generate_backup_info
    
    # 压缩备份
    local archive_path
    if archive_path=$(compress_backup); then
        echo
        success "备份完成！"
        echo -e "📁 备份文件: ${GREEN}$archive_path${NC}"
        echo -e "📊 文件大小: ${YELLOW}$(du -h "$archive_path" | cut -f1)${NC}"
        echo
        echo "💡 恢复命令: ./simple-restore.sh \"$archive_path\""
    else
        error "备份失败"
        exit 1
    fi
}

# 执行主函数
main "$@"
