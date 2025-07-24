#!/bin/bash

# =============================================================================
# Mem0 完整系统备份脚本
# 版本: 1.0.0
# 作者: Mem0 Team
# 描述: 一键备份Mem0系统的所有数据和配置
# =============================================================================

set -euo pipefail

# 导入工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/backup-utils.sh"

# 全局变量
BACKUP_NAME=""
BACKUP_PATH=""
DRY_RUN=false
QUIET=false
INCLUDE_LOGS=false

# =============================================================================
# 帮助信息
# =============================================================================

show_help() {
    cat << EOF
Mem0 系统备份脚本

用法: $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -n, --name NAME     指定备份名称 (默认: backup-YYYYMMDD-HHMMSS)
    -d, --dry-run       干运行模式，不执行实际备份
    -q, --quiet         静默模式，减少输出
    -l, --include-logs  包含日志文件
    --debug             启用调试模式

示例:
    $0                              # 使用默认名称备份
    $0 -n my-backup               # 使用自定义名称备份
    $0 --dry-run                  # 干运行，查看将要备份的内容
    $0 -l                         # 包含日志文件的完整备份

备份内容:
    ✓ Qdrant向量数据库数据
    ✓ PostgreSQL用户数据
    ✓ Mem0配置文件
    ✓ Docker配置文件
    ✓ 环境变量和密钥
    ✓ 系统元数据
    ○ 日志文件 (可选)

EOF
}

# =============================================================================
# 参数解析
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -n|--name)
                BACKUP_NAME="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -l|--include-logs)
                INCLUDE_LOGS=true
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
}

# =============================================================================
# 备份函数
# =============================================================================

# 备份Qdrant数据
backup_qdrant() {
    local backup_path="$1"
    local qdrant_dir="$backup_path/qdrant"
    
    info "备份Qdrant向量数据库..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] 将备份Qdrant collections"
        return 0
    fi
    
    # 获取所有collections
    local collections=$(curl -s http://localhost:6333/collections 2>/dev/null | jq -r '.result.collections[].name' 2>/dev/null)

    if [[ -z "$collections" ]]; then
        warn "未找到Qdrant collections或服务不可用"
        return 0
    fi

    # 备份每个collection
    local count=0
    local total=$(echo "$collections" | wc -l)

    for collection in $collections; do
        if [[ -n "$collection" ]]; then
            ((count++))
            echo "备份Collection: $collection ($count/$total)"

            # 创建collection快照
            local snapshot_result=$(curl -s -X POST "http://localhost:6333/collections/$collection/snapshots" \
                -H "Content-Type: application/json" 2>/dev/null)

            # 获取快照名称
            local snapshot_name=$(echo "$snapshot_result" | jq -r '.result.name' 2>/dev/null)

            if [[ -n "$snapshot_name" && "$snapshot_name" != "null" ]]; then
                # 下载快照
                if curl -s "http://localhost:6333/collections/$collection/snapshots/$snapshot_name" \
                    -o "$qdrant_dir/${collection}.snapshot" 2>/dev/null; then
                    echo "✓ Collection $collection 备份成功"
                else
                    warn "Collection $collection 下载失败"
                fi

                # 删除远程快照
                curl -s -X DELETE "http://localhost:6333/collections/$collection/snapshots/$snapshot_name" >/dev/null 2>&1
            else
                warn "Collection $collection 快照创建失败"
            fi
        fi
    done
    
    echo # 换行
    success "Qdrant数据备份完成 ($count个collections)"
    
    # 更新元数据
    local metadata_file="$backup_path/metadata.json"
    jq --argjson collections "$(echo "$collections" | jq -R . | jq -s .)" \
       '.services.qdrant_collections = $collections' "$metadata_file" > "$metadata_file.tmp" && \
       mv "$metadata_file.tmp" "$metadata_file"
    
    return 0
}

# 备份PostgreSQL数据
backup_postgres() {
    local backup_path="$1"
    local postgres_dir="$backup_path/postgres"
    
    info "备份PostgreSQL数据库..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] 将备份PostgreSQL数据"
        return 0
    fi
    
    # 备份Mem0核心数据库
    docker exec mem0-postgres pg_dump -U mem0 mem0 > "$postgres_dir/mem0.sql" 2>/dev/null || {
        warn "Mem0数据库备份失败，可能是数据库不存在或服务未运行"
    }

    # 备份WebUI数据库
    docker exec mem0-postgres pg_dump -U mem0 webui > "$postgres_dir/webui.sql" 2>/dev/null || {
        warn "WebUI数据库备份失败，可能是数据库不存在或服务未运行"
    }

    # 备份用户权限
    docker exec mem0-postgres pg_dumpall -U mem0 --roles-only > "$postgres_dir/roles.sql" 2>/dev/null

    success "PostgreSQL数据备份完成"

    # 更新元数据
    local metadata_file="$backup_path/metadata.json"
    jq '.services.postgres_databases = ["mem0", "webui"]' "$metadata_file" > "$metadata_file.tmp" && \
       mv "$metadata_file.tmp" "$metadata_file"
    
    return 0
}

# 备份配置文件
backup_configs() {
    local backup_path="$1"
    local configs_dir="$backup_path/configs"
    
    info "备份配置文件..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] 将备份配置文件"
        return 0
    fi
    
    local config_files=(
        "$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml"
        "$PROJECT_ROOT/mem0-deployment/docker-compose.yml"
        "$PROJECT_ROOT/mem0-deployment/.env"
        "$PROJECT_ROOT/gemini-balance/config.yaml"
    )
    
    local backed_up_files=()
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            local filename=$(basename "$config_file")
            local dirname=$(basename "$(dirname "$config_file")")
            cp "$config_file" "$configs_dir/${dirname}_${filename}"
            backed_up_files+=("${dirname}_${filename}")
        fi
    done
    
    success "配置文件备份完成 (${#backed_up_files[@]}个文件)"
    
    # 更新元数据
    local metadata_file="$backup_path/metadata.json"
    jq --argjson files "$(printf '%s\n' "${backed_up_files[@]}" | jq -R . | jq -s .)" \
       '.services.config_files = $files' "$metadata_file" > "$metadata_file.tmp" && \
       mv "$metadata_file.tmp" "$metadata_file"
    
    return 0
}

# 备份环境变量
backup_environment() {
    local backup_path="$1"
    local env_dir="$backup_path/env"
    
    info "备份环境变量..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] 将备份环境变量"
        return 0
    fi
    
    # 备份Docker环境变量
    if [[ -f "$PROJECT_ROOT/mem0-deployment/.env" ]]; then
        cp "$PROJECT_ROOT/mem0-deployment/.env" "$env_dir/docker.env"
    fi
    
    # 备份系统环境变量（过滤敏感信息）
    env | grep -E '^(MEM0_|QDRANT_|POSTGRES_)' > "$env_dir/system.env" 2>/dev/null || true
    
    success "环境变量备份完成"
    return 0
}

# 备份日志文件
backup_logs() {
    local backup_path="$1"
    local logs_dir="$backup_path/logs"
    
    if [[ "$INCLUDE_LOGS" != "true" ]]; then
        return 0
    fi
    
    info "备份日志文件..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] 将备份日志文件"
        return 0
    fi
    
    # 备份Docker容器日志
    local containers=("mem0-api" "mem0-qdrant" "mem0-postgres" "mem0-webui")
    
    for container in "${containers[@]}"; do
        if docker ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
            docker logs "$container" > "$logs_dir/${container}.log" 2>&1 || true
        fi
    done
    
    # 备份系统日志
    if [[ -f "$LOG_FILE" ]]; then
        cp "$LOG_FILE" "$logs_dir/backup.log"
    fi
    
    success "日志文件备份完成"
    return 0
}

# =============================================================================
# 主函数
# =============================================================================

main() {
    # 解析参数
    parse_args "$@"
    
    # 设置备份名称
    if [[ -z "$BACKUP_NAME" ]]; then
        BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
    fi
    
    # 初始化
    init_log
    
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${CYAN}"
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║                    Mem0 系统备份工具                        ║"
        echo "║                     版本: 1.0.0                            ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
    
    info "开始备份: $BACKUP_NAME"
    
    # 检查依赖
    if ! check_dependencies; then
        exit 1
    fi
    
    # 检查服务状态
    if ! check_docker_services; then
        error "请确保Mem0服务正在运行"
        exit 1
    fi
    
    # 创建备份目录
    if ! BACKUP_PATH=$(create_backup_dir "$BACKUP_NAME"); then
        exit 1
    fi
    
    # 生成元数据
    if ! generate_metadata "$BACKUP_PATH"; then
        cleanup_on_error "$BACKUP_PATH"
        exit 1
    fi
    
    # 设置错误处理
    trap 'cleanup_on_error "$BACKUP_PATH"' ERR

    # 先备份需要服务运行的数据
    backup_qdrant "$BACKUP_PATH"

    # 停止服务（确保数据一致性）
    if [[ "$DRY_RUN" != "true" ]]; then
        stop_services
    fi

    # 执行其他备份
    backup_postgres "$BACKUP_PATH"
    backup_configs "$BACKUP_PATH"
    backup_environment "$BACKUP_PATH"
    backup_logs "$BACKUP_PATH"

    # 重启服务
    if [[ "$DRY_RUN" != "true" ]]; then
        start_services
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "干运行完成，未执行实际备份"
        rm -rf "$BACKUP_PATH"
        exit 0
    fi
    
    # 计算校验和
    calculate_checksums "$BACKUP_PATH"
    
    # 压缩备份
    local archive_path
    if archive_path=$(compress_backup "$BACKUP_PATH"); then
        # 验证备份
        if verify_backup "$archive_path"; then
            success "备份完成: $archive_path"
            
            # 清理旧备份
            cleanup_old_backups 7
            
            if [[ "$QUIET" != "true" ]]; then
                echo
                echo -e "${GREEN}✅ 备份成功完成！${NC}"
                echo -e "📁 备份文件: ${CYAN}$archive_path${NC}"
                echo -e "📊 文件大小: ${YELLOW}$(du -h "$archive_path" | cut -f1)${NC}"
                echo -e "🔍 校验和: ${PURPLE}$(md5sum "$archive_path" | cut -d' ' -f1)${NC}"
                echo
                echo "💡 恢复命令: ./restore.sh \"$archive_path\""
            fi
        else
            error "备份验证失败"
            exit 1
        fi
    else
        error "备份压缩失败"
        exit 1
    fi
}

# 执行主函数
main "$@"
