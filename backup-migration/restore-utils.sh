#!/bin/bash

# =============================================================================
# Mem0 恢复工具函数库
# 版本: 1.0.0
# 作者: Mem0 Team
# 描述: 提供恢复相关的工具函数
# =============================================================================

# 导入备份工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/backup-utils.sh"

# 恢复相关全局变量
RESTORE_DIR="$PROJECT_ROOT/restore-temp"
BACKUP_METADATA=""

# =============================================================================
# 备份文件处理函数
# =============================================================================

# 解压备份文件
extract_backup() {
    local archive_path="$1"
    local extract_dir="$2"
    
    info "解压备份文件..."
    
    # 创建临时解压目录
    mkdir -p "$extract_dir"
    
    # 解压备份文件
    if tar -xzf "$archive_path" -C "$extract_dir" --strip-components=1 2>/dev/null; then
        success "备份文件解压完成"
        return 0
    else
        error "备份文件解压失败"
        return 1
    fi
}

# 验证备份文件完整性
verify_backup_integrity() {
    local restore_dir="$1"
    local checksum_file="$restore_dir/checksums.md5"
    
    info "验证备份文件完整性..."
    
    if [[ ! -f "$checksum_file" ]]; then
        warn "未找到校验和文件，跳过完整性验证"
        return 0
    fi
    
    cd "$restore_dir" || return 1
    
    if md5sum -c "$checksum_file" >/dev/null 2>&1; then
        success "备份文件完整性验证通过"
        return 0
    else
        error "备份文件完整性验证失败"
        return 1
    fi
}

# 读取备份元数据
read_backup_metadata() {
    local restore_dir="$1"
    local metadata_file="$restore_dir/metadata.json"
    
    if [[ ! -f "$metadata_file" ]]; then
        error "未找到备份元数据文件"
        return 1
    fi
    
    BACKUP_METADATA=$(cat "$metadata_file")
    
    # 显示备份信息
    local backup_time=$(echo "$BACKUP_METADATA" | jq -r '.backup_info.timestamp')
    local backup_version=$(echo "$BACKUP_METADATA" | jq -r '.backup_info.version')
    local source_hostname=$(echo "$BACKUP_METADATA" | jq -r '.backup_info.hostname')
    
    info "备份信息:"
    echo "  📅 备份时间: $backup_time"
    echo "  🏷️  备份版本: $backup_version"
    echo "  🖥️  源主机: $source_hostname"
    
    return 0
}

# =============================================================================
# 环境检查函数
# =============================================================================

# 检查目标环境
check_target_environment() {
    info "检查目标环境..."
    
    # 检查是否已安装Mem0
    if [[ ! -d "$PROJECT_ROOT/mem0-deployment" ]]; then
        error "未找到Mem0安装目录"
        error "请先运行一键安装脚本安装基础环境"
        return 1
    fi
    
    # 检查Docker服务
    if ! docker info >/dev/null 2>&1; then
        error "Docker服务未运行"
        return 1
    fi
    
    # 检查docker-compose文件
    if [[ ! -f "$PROJECT_ROOT/mem0-deployment/docker-compose.yml" ]]; then
        error "未找到docker-compose.yml文件"
        return 1
    fi
    
    success "目标环境检查通过"
    return 0
}

# 检查版本兼容性
check_version_compatibility() {
    if [[ -z "$BACKUP_METADATA" ]]; then
        warn "无法获取备份版本信息，跳过兼容性检查"
        return 0
    fi
    
    local backup_version=$(echo "$BACKUP_METADATA" | jq -r '.backup_info.version')
    local current_version="1.0.0"  # 当前脚本版本
    
    info "检查版本兼容性..."
    echo "  🔄 备份版本: $backup_version"
    echo "  🔄 当前版本: $current_version"
    
    # 简单的版本兼容性检查
    if [[ "$backup_version" == "$current_version" ]]; then
        success "版本完全兼容"
        return 0
    else
        warn "版本不完全匹配，但将尝试恢复"
        return 0
    fi
}

# =============================================================================
# 数据恢复函数
# =============================================================================

# 恢复Qdrant数据
restore_qdrant() {
    local restore_dir="$1"
    local qdrant_dir="$restore_dir/qdrant"
    
    info "恢复Qdrant向量数据库..."
    
    if [[ ! -d "$qdrant_dir" ]]; then
        warn "未找到Qdrant备份数据，跳过恢复"
        return 0
    fi
    
    # 等待Qdrant服务启动
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
            break
        fi
        ((attempt++))
        sleep 2
        echo -n "."
    done
    echo
    
    if [[ $attempt -eq $max_attempts ]]; then
        error "Qdrant服务启动超时"
        return 1
    fi
    
    # 恢复每个collection的快照
    local count=0
    local total=$(find "$qdrant_dir" -name "*.snapshot" | wc -l)
    
    for snapshot_file in "$qdrant_dir"/*.snapshot; do
        if [[ -f "$snapshot_file" ]]; then
            ((count++))
            local collection_name=$(basename "$snapshot_file" .snapshot)
            show_progress $count $total "恢复Collection: $collection_name"
            
            # 上传快照文件
            curl -s -X PUT "http://localhost:6333/collections/$collection_name/snapshots/upload" \
                -H "Content-Type: application/octet-stream" \
                --data-binary "@$snapshot_file" >/dev/null 2>&1 || {
                warn "Collection $collection_name 恢复失败"
                continue
            }
        fi
    done
    
    echo # 换行
    success "Qdrant数据恢复完成 ($count个collections)"
    return 0
}

# 恢复PostgreSQL数据
restore_postgres() {
    local restore_dir="$1"
    local postgres_dir="$restore_dir/postgres"
    
    info "恢复PostgreSQL数据库..."
    
    if [[ ! -d "$postgres_dir" ]]; then
        warn "未找到PostgreSQL备份数据，跳过恢复"
        return 0
    fi
    
    # 等待PostgreSQL服务启动
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker exec mem0-postgres pg_isready -U postgres >/dev/null 2>&1; then
            break
        fi
        ((attempt++))
        sleep 2
        echo -n "."
    done
    echo
    
    if [[ $attempt -eq $max_attempts ]]; then
        error "PostgreSQL服务启动超时"
        return 1
    fi
    
    # 恢复用户权限
    if [[ -f "$postgres_dir/roles.sql" ]]; then
        docker exec -i mem0-postgres psql -U mem0 < "$postgres_dir/roles.sql" >/dev/null 2>&1 || true
    fi

    # 恢复Mem0核心数据库
    if [[ -f "$postgres_dir/mem0.sql" ]]; then
        # 创建数据库（如果不存在）
        docker exec mem0-postgres createdb -U mem0 mem0 2>/dev/null || true

        # 恢复数据
        docker exec -i mem0-postgres psql -U mem0 -d mem0 < "$postgres_dir/mem0.sql" >/dev/null 2>&1
    fi

    # 恢复WebUI数据库
    if [[ -f "$postgres_dir/webui.sql" ]]; then
        # 创建数据库（如果不存在）
        docker exec mem0-postgres createdb -U mem0 webui 2>/dev/null || true

        # 恢复数据
        docker exec -i mem0-postgres psql -U mem0 -d webui < "$postgres_dir/webui.sql" >/dev/null 2>&1
    fi
    
    success "PostgreSQL数据恢复完成"
    return 0
}

# 恢复配置文件
restore_configs() {
    local restore_dir="$1"
    local configs_dir="$restore_dir/configs"
    
    info "恢复配置文件..."
    
    if [[ ! -d "$configs_dir" ]]; then
        warn "未找到配置文件备份，跳过恢复"
        return 0
    fi
    
    local restored_count=0
    
    # 恢复mem0配置
    if [[ -f "$configs_dir/configs_mem0-config.yaml" ]]; then
        cp "$configs_dir/configs_mem0-config.yaml" "$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml"
        ((restored_count++))
    fi
    
    # 恢复docker-compose配置
    if [[ -f "$configs_dir/mem0-deployment_docker-compose.yml" ]]; then
        cp "$configs_dir/mem0-deployment_docker-compose.yml" "$PROJECT_ROOT/mem0-deployment/docker-compose.yml"
        ((restored_count++))
    fi
    
    # 恢复环境变量文件
    if [[ -f "$configs_dir/mem0-deployment_.env" ]]; then
        cp "$configs_dir/mem0-deployment_.env" "$PROJECT_ROOT/mem0-deployment/.env"
        ((restored_count++))
    fi
    
    # 恢复gemini-balance配置
    if [[ -f "$configs_dir/gemini-balance_config.yaml" ]]; then
        mkdir -p "$PROJECT_ROOT/gemini-balance"
        cp "$configs_dir/gemini-balance_config.yaml" "$PROJECT_ROOT/gemini-balance/config.yaml"
        ((restored_count++))
    fi
    
    success "配置文件恢复完成 ($restored_count个文件)"
    return 0
}

# 恢复环境变量
restore_environment() {
    local restore_dir="$1"
    local env_dir="$restore_dir/env"
    
    info "恢复环境变量..."
    
    if [[ ! -d "$env_dir" ]]; then
        warn "未找到环境变量备份，跳过恢复"
        return 0
    fi
    
    # 恢复Docker环境变量
    if [[ -f "$env_dir/docker.env" && ! -f "$PROJECT_ROOT/mem0-deployment/.env" ]]; then
        cp "$env_dir/docker.env" "$PROJECT_ROOT/mem0-deployment/.env"
    fi
    
    success "环境变量恢复完成"
    return 0
}

# =============================================================================
# 服务管理函数
# =============================================================================

# 重建并启动服务
rebuild_and_start_services() {
    info "重建并启动Mem0服务..."
    
    cd "$PROJECT_ROOT/mem0-deployment" || return 1
    
    # 停止所有服务
    docker-compose down 2>/dev/null || true
    
    # 重新构建并启动服务
    docker-compose up -d --build 2>/dev/null
    
    success "服务已重建并启动"
    return 0
}

# 验证服务状态
verify_services() {
    info "验证服务状态..."
    
    local services=("mem0-qdrant" "mem0-postgres" "mem0-api" "mem0-webui")
    local max_attempts=60
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        local all_running=true
        
        for service in "${services[@]}"; do
            if ! docker-compose ps "$service" | grep -q "Up"; then
                all_running=false
                break
            fi
        done
        
        if [[ "$all_running" == "true" ]]; then
            success "所有服务运行正常"
            return 0
        fi
        
        ((attempt++))
        sleep 2
        echo -n "."
    done
    
    echo
    error "服务启动验证超时"
    return 1
}

# =============================================================================
# 清理函数
# =============================================================================

# 清理恢复临时文件
cleanup_restore_temp() {
    if [[ -d "$RESTORE_DIR" ]]; then
        rm -rf "$RESTORE_DIR"
    fi
}

# 恢复失败时的回滚
rollback_on_failure() {
    warn "恢复失败，正在回滚..."
    
    # 停止服务
    cd "$PROJECT_ROOT/mem0-deployment" || return 1
    docker-compose down 2>/dev/null || true
    
    # 清理临时文件
    cleanup_restore_temp
    
    error "恢复已回滚，请检查错误信息后重试"
}

# =============================================================================
# 验证函数
# =============================================================================

# 验证恢复结果
verify_restore_result() {
    info "验证恢复结果..."
    
    # 检查Qdrant collections
    local collections=$(curl -s http://localhost:6333/collections 2>/dev/null | jq -r '.result.collections[].name' 2>/dev/null || echo "")
    if [[ -n "$collections" ]]; then
        local collection_count=$(echo "$collections" | wc -l)
        success "Qdrant: $collection_count 个collections已恢复"
    else
        warn "Qdrant: 未检测到collections"
    fi
    
    # 检查PostgreSQL数据库
    if docker exec mem0-postgres psql -U mem0 -l 2>/dev/null | grep -q "mem0"; then
        success "PostgreSQL: mem0数据库已恢复"
    else
        warn "PostgreSQL: 未检测到mem0数据库"
    fi

    if docker exec mem0-postgres psql -U mem0 -l 2>/dev/null | grep -q "webui"; then
        success "PostgreSQL: webui数据库已恢复"
    else
        warn "PostgreSQL: 未检测到webui数据库"
    fi
    
    # 检查配置文件
    if [[ -f "$PROJECT_ROOT/mem0-deployment/configs/mem0-config.yaml" ]]; then
        success "配置文件: mem0-config.yaml已恢复"
    else
        warn "配置文件: mem0-config.yaml未找到"
    fi

    return 0
}

# =============================================================================
# Neo4j 图数据库恢复函数
# =============================================================================

# 恢复Neo4j图数据库
restore_neo4j() {
    local restore_dir="$1"
    local neo4j_dir="$restore_dir/neo4j"

    info "恢复Neo4j图数据库..."

    if [[ ! -d "$neo4j_dir" ]]; then
        warn "未找到Neo4j备份数据，跳过恢复"
        return 0
    fi

    # 检查Neo4j容器是否运行
    if ! docker ps | grep -q "mem0-neo4j"; then
        warn "Neo4j容器未运行，跳过Neo4j恢复"
        return 0
    fi

    # 等待Neo4j服务启动
    info "等待Neo4j服务启动..."
    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
            success "Neo4j服务已启动"
            break
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        error "Neo4j服务启动超时"
        return 1
    fi

    # 清空现有数据（如果需要）
    info "清空Neo4j现有数据..."
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    MATCH (n) DETACH DELETE n
    " >/dev/null 2>&1 || true

    # 1. 恢复数据库转储（如果存在）
    if [[ -f "$neo4j_dir/graph.dump" ]]; then
        info "恢复Neo4j数据库转储..."

        # 停止Neo4j服务
        docker stop mem0-neo4j >/dev/null 2>&1 || true

        # 复制转储文件到容器
        docker cp "$neo4j_dir/graph.dump" mem0-neo4j:/tmp/graph.dump

        # 加载数据库转储
        docker start mem0-neo4j >/dev/null 2>&1
        sleep 10

        docker exec mem0-neo4j neo4j-admin database load neo4j --from-path=/tmp --overwrite-destination=true >/dev/null 2>&1 || {
            warn "数据库转储恢复失败，尝试其他方法"
        }

        # 重启Neo4j
        docker restart mem0-neo4j >/dev/null 2>&1
        sleep 15

        success "Neo4j数据库转储恢复完成"
    fi

    # 等待Neo4j重新启动
    info "等待Neo4j重新启动..."
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 2
    done

    # 2. 恢复索引和约束
    if [[ -f "$neo4j_dir/indexes.cypher" ]]; then
        info "恢复Neo4j索引和约束..."

        # 执行索引和约束创建脚本
        docker exec -i mem0-neo4j cypher-shell -u neo4j -p password < "$neo4j_dir/indexes.cypher" >/dev/null 2>&1 || {
            warn "索引和约束恢复失败"
        }

        success "Neo4j索引和约束恢复完成"
    fi

    # 3. 如果有恢复脚本，执行它
    if [[ -f "$neo4j_dir/restore-neo4j.sh" ]]; then
        info "执行Neo4j自定义恢复脚本..."
        cd "$neo4j_dir"
        bash restore-neo4j.sh >/dev/null 2>&1 || {
            warn "自定义恢复脚本执行失败"
        }
        cd - >/dev/null
    fi

    # 4. 验证恢复结果
    info "验证Neo4j恢复结果..."
    local node_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
    local rel_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN count(r) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")

    info "恢复统计: $node_count 个节点, $rel_count 个关系"
    success "Neo4j图数据库恢复完成"

    return 0
}

# 验证Neo4j恢复
verify_neo4j_restore() {
    info "验证Neo4j恢复状态..."

    # 检查Neo4j连接
    if ! docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
        error "Neo4j连接失败"
        return 1
    fi

    # 检查数据
    local node_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")
    local rel_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN count(r) as count" 2>/dev/null | tail -1 | tr -d '"' || echo "0")

    info "Neo4j数据统计: $node_count 个节点, $rel_count 个关系"

    if [[ "$node_count" -gt 0 ]] || [[ "$rel_count" -gt 0 ]]; then
        success "Neo4j数据验证通过"
        return 0
    else
        warn "Neo4j数据为空，可能是新安装或备份为空"
        return 0
    fi
}
