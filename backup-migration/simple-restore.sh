#!/bin/bash

# =============================================================================
# Mem0 简化恢复脚本
# 版本: 1.0.0
# 描述: 基于mem0官方文档的简化恢复方案
# =============================================================================

set -euo pipefail

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

# 显示使用说明
show_usage() {
    echo "使用方法: $0 <备份文件路径>"
    echo "示例: $0 /path/to/backup-20241224-143022.tar.gz"
    exit 1
}

# 解压备份文件
extract_backup() {
    local backup_file="$1"
    local extract_dir="$2"

    info "解压备份文件: $(basename "$backup_file")" >&2

    if ! tar -xzf "$backup_file" -C "$extract_dir" 2>/dev/null; then
        error "备份文件解压失败" >&2
        return 1
    fi

    # 查找解压后的目录
    local backup_name=$(basename "$backup_file" .tar.gz)
    local backup_path="$extract_dir/$backup_name"

    if [[ ! -d "$backup_path" ]]; then
        error "解压后的备份目录不存在: $backup_path" >&2
        return 1
    fi

    echo "$backup_path"
}

# 恢复Qdrant数据
restore_qdrant() {
    local backup_path="$1"
    local qdrant_dir="$backup_path/qdrant"

    info "检查Qdrant备份路径: $qdrant_dir"

    if [[ ! -d "$qdrant_dir" ]]; then
        warn "未找到Qdrant备份数据: $qdrant_dir"
        return 0
    fi

    info "恢复Qdrant向量数据库..."

    # 恢复每个collection的快照
    for snapshot_file in "$qdrant_dir"/*.snapshot; do
        if [[ -f "$snapshot_file" ]]; then
            local collection_name=$(basename "$snapshot_file" .snapshot)
            info "恢复Collection: $collection_name"

            # 先创建collection（如果不存在）
            curl -s -X PUT "http://localhost:6333/collections/$collection_name" \
                -H "Content-Type: application/json" \
                -d '{"vectors": {"size": 1536, "distance": "Cosine"}}' >/dev/null 2>&1 || true

            # 上传快照文件恢复数据
            if curl -s -X POST "http://localhost:6333/collections/$collection_name/snapshots/upload" \
                -F "snapshot=@$snapshot_file" >/dev/null 2>&1; then
                success "Collection $collection_name 恢复完成"
            else
                warn "Collection $collection_name 恢复失败，尝试直接恢复快照"
                # 尝试通过快照恢复整个collection
                curl -s -X POST "http://localhost:6333/collections/$collection_name/snapshots/recover" \
                    -F "snapshot=@$snapshot_file" >/dev/null 2>&1 || true
            fi
        fi
    done
}

# 恢复PostgreSQL数据
restore_postgres() {
    local backup_path="$1"
    local postgres_dir="$backup_path/postgres"

    info "检查PostgreSQL备份路径: $postgres_dir"

    if [[ ! -d "$postgres_dir" ]]; then
        warn "未找到PostgreSQL备份数据: $postgres_dir"
        return 0
    fi

    info "恢复PostgreSQL数据库..."
    
    # 恢复用户权限
    if [[ -f "$postgres_dir/roles.sql" ]]; then
        docker exec -i mem0-postgres psql -U mem0 < "$postgres_dir/roles.sql" >/dev/null 2>&1 || true
    fi
    
    # 恢复mem0数据库
    if [[ -f "$postgres_dir/mem0.sql" ]]; then
        info "恢复mem0数据库..."
        docker exec mem0-postgres createdb -U mem0 mem0 2>/dev/null || true
        docker exec -i mem0-postgres psql -U mem0 -d mem0 < "$postgres_dir/mem0.sql" >/dev/null 2>&1
        success "mem0数据库恢复完成"
    fi
    
    # 恢复webui数据库
    if [[ -f "$postgres_dir/webui.sql" ]]; then
        info "恢复webui数据库..."
        docker exec mem0-postgres createdb -U mem0 webui 2>/dev/null || true
        docker exec -i mem0-postgres psql -U mem0 -d webui < "$postgres_dir/webui.sql" >/dev/null 2>&1
        success "webui数据库恢复完成"
    fi
}

# 恢复配置文件
restore_configs() {
    local backup_path="$1"
    local configs_dir="$backup_path/configs"
    
    if [[ ! -d "$configs_dir" ]]; then
        warn "未找到配置文件备份"
        return 0
    fi
    
    info "恢复配置文件..."
    
    # 恢复配置文件
    for config_file in "$configs_dir"/*; do
        if [[ -f "$config_file" ]]; then
            local filename=$(basename "$config_file")
            local target_dir=""
            local target_name=""
            
            # 解析文件名格式: dirname_filename
            if [[ "$filename" =~ ^(.+)_(.+)$ ]]; then
                local dir_name="${BASH_REMATCH[1]}"
                target_name="${BASH_REMATCH[2]}"
                target_dir="$PROJECT_ROOT/mem0-deployment/$dir_name"
            else
                target_name="$filename"
                target_dir="$PROJECT_ROOT/mem0-deployment"
            fi
            
            # 创建目标目录
            mkdir -p "$target_dir"
            
            # 复制配置文件
            cp "$config_file" "$target_dir/$target_name"
            success "配置文件 $target_name 恢复完成"
        fi
    done
}

# 重启服务
restart_services() {
    info "重启Mem0服务..."
    
    cd "$PROJECT_ROOT/mem0-deployment" || exit 1
    
    # 停止服务
    docker-compose down >/dev/null 2>&1 || true
    
    # 启动服务
    if docker-compose up -d >/dev/null 2>&1; then
        success "服务重启完成"
        
        # 等待服务启动
        info "等待服务启动..."
        sleep 15
        
        # 验证服务状态
        if curl -s http://localhost:6333/collections >/dev/null 2>&1 && \
           docker exec mem0-postgres pg_isready -U mem0 >/dev/null 2>&1; then
            success "服务验证通过"
        else
            warn "服务可能未完全启动，请手动检查"
        fi
    else
        error "服务启动失败"
        return 1
    fi
}

# 显示恢复信息
show_restore_info() {
    local backup_path="$1"
    local info_file="$backup_path/backup_info.txt"
    
    if [[ -f "$info_file" ]]; then
        echo
        echo -e "${BLUE}备份信息:${NC}"
        echo "----------------------------------------"
        cat "$info_file"
        echo "----------------------------------------"
    fi
}

# 主函数
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                  Mem0 简化恢复工具                          ║"
    echo "║                   版本: 1.0.0                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # 检查参数
    if [[ $# -ne 1 ]]; then
        show_usage
    fi
    
    local backup_file="$1"
    
    # 检查备份文件
    if [[ ! -f "$backup_file" ]]; then
        error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    info "开始恢复: $(basename "$backup_file")"
    
    # 创建临时目录
    local temp_dir=$(mktemp -d)
    trap "rm -rf '$temp_dir'" EXIT
    
    # 解压备份
    local backup_path
    if ! backup_path=$(extract_backup "$backup_file" "$temp_dir"); then
        exit 1
    fi
    
    # 显示备份信息
    show_restore_info "$backup_path"
    
    # 确认恢复
    echo
    read -p "确认要恢复此备份吗？这将覆盖现有数据 [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "恢复已取消"
        exit 0
    fi
    
    # 执行恢复
    restore_configs "$backup_path"
    restore_postgres "$backup_path"
    restart_services
    restore_qdrant "$backup_path"
    
    echo
    success "恢复完成！"
    echo
    echo "💡 建议验证步骤："
    echo "1. 访问 http://localhost:8503 检查WebUI"
    echo "2. 检查API服务: curl http://localhost:8888/health"
    echo "3. 运行验证脚本: ./validate.sh"
}

# 执行主函数
main "$@"
