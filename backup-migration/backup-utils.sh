#!/bin/bash

# =============================================================================
# Mem0 备份工具函数库
# 版本: 1.0.0
# 作者: Mem0 Team
# 描述: 提供备份相关的工具函数
# =============================================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="$BACKUP_DIR/backup.log"

# =============================================================================
# 日志和输出函数
# =============================================================================

# 初始化日志
init_log() {
    mkdir -p "$BACKUP_DIR"
    echo "=== Mem0 备份日志 - $(date '+%Y-%m-%d %H:%M:%S') ===" > "$LOG_FILE"
}

# 记录日志
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# 信息输出
info() {
    echo -e "${BLUE}[INFO]${NC} $*"
    log "INFO" "$*"
}

# 成功输出
success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
    log "SUCCESS" "$*"
}

# 警告输出
warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
    log "WARN" "$*"
}

# 错误输出
error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    log "ERROR" "$*"
}

# 调试输出
debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $*"
        log "DEBUG" "$*"
    fi
}

# 进度条
show_progress() {
    local current=$1
    local total=$2
    local desc="$3"
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))
    
    printf "\r${CYAN}[%s]${NC} " "$desc"
    printf "%*s" $filled | tr ' ' '='
    printf "%*s" $empty | tr ' ' '-'
    printf " %d%% (%d/%d)" $percent $current $total
}

# =============================================================================
# 系统检查函数
# =============================================================================

# 检查命令是否存在
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        error "命令 '$cmd' 未找到，请先安装"
        return 1
    fi
    return 0
}

# 检查必要的命令
check_dependencies() {
    info "检查系统依赖..."
    local deps=("docker" "docker-compose" "curl" "jq" "tar" "gzip" "md5sum")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! check_command "$dep"; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "缺少必要依赖: ${missing[*]}"
        error "请安装缺少的依赖后重试"
        return 1
    fi
    
    success "所有依赖检查通过"
    return 0
}

# 检查Docker服务状态
check_docker_services() {
    info "检查Docker服务状态..."
    cd "$PROJECT_ROOT/mem0-deployment" || {
        error "无法进入项目目录: $PROJECT_ROOT/mem0-deployment"
        return 1
    }
    
    local services=("mem0-qdrant" "mem0-postgres" "mem0-api")
    local running_services=()
    local stopped_services=()
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            running_services+=("$service")
        else
            stopped_services+=("$service")
        fi
    done
    
    if [[ ${#stopped_services[@]} -gt 0 ]]; then
        warn "以下服务未运行: ${stopped_services[*]}"
        return 1
    fi
    
    success "所有核心服务正在运行: ${running_services[*]}"
    return 0
}

# =============================================================================
# 备份相关函数
# =============================================================================

# 创建备份目录
create_backup_dir() {
    local backup_name="$1"
    local backup_path="$BACKUP_DIR/$backup_name"

    info "创建备份目录: $backup_path"
    mkdir -p "$backup_path"/{qdrant,postgres,configs,env,logs}

    if [[ ! -d "$backup_path" ]]; then
        error "无法创建备份目录: $backup_path"
        return 1
    fi

    echo "$backup_path"
    return 0
}

# 生成备份元数据
generate_metadata() {
    local backup_path="$1"
    local metadata_file="$backup_path/metadata.json"

    info "生成备份元数据..." >&2

    cat > "$metadata_file" << 'EOF'
{
    "backup_info": {
        "version": "1.0.0",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "hostname": "$(hostname)",
        "user": "$(whoami)",
        "backup_type": "full"
    },
    "system_info": {
        "os": "$(uname -s)",
        "arch": "$(uname -m)",
        "kernel": "$(uname -r)",
        "docker_version": "$(docker --version 2>/dev/null || echo 'unknown')",
        "docker_compose_version": "$(docker-compose --version 2>/dev/null || echo 'unknown')"
    },
    "services": {
        "qdrant_collections": [],
        "postgres_databases": [],
        "config_files": []
    }
}
EOF
    
    success "元数据文件已创建: $metadata_file"
    return 0
}

# 计算文件校验和
calculate_checksums() {
    local backup_path="$1"
    local checksum_file="$backup_path/checksums.md5"
    
    info "计算文件校验和..."
    cd "$backup_path" || return 1
    
    find . -type f -not -name "checksums.md5" -exec md5sum {} \; > "$checksum_file"
    
    success "校验和文件已创建: $checksum_file"
    return 0
}

# 压缩备份
compress_backup() {
    local backup_path="$1"
    local backup_name="$(basename "$backup_path")"
    local archive_path="$BACKUP_DIR/${backup_name}.tar.gz"
    
    info "压缩备份文件..."
    cd "$BACKUP_DIR" || return 1
    
    tar -czf "$archive_path" "$backup_name" 2>/dev/null
    
    if [[ $? -eq 0 && -f "$archive_path" ]]; then
        local size=$(du -h "$archive_path" | cut -f1)
        success "备份已压缩: $archive_path (大小: $size)"
        
        # 删除临时目录
        rm -rf "$backup_path"
        
        echo "$archive_path"
        return 0
    else
        error "备份压缩失败"
        return 1
    fi
}

# =============================================================================
# 服务管理函数
# =============================================================================

# 停止服务
stop_services() {
    info "停止Mem0服务..."
    cd "$PROJECT_ROOT/mem0-deployment" || return 1
    
    docker-compose stop mem0-api mem0-webui 2>/dev/null
    sleep 3
    
    success "服务已停止"
    return 0
}

# 启动服务
start_services() {
    info "启动Mem0服务..."
    cd "$PROJECT_ROOT/mem0-deployment" || return 1
    
    docker-compose up -d mem0-api mem0-webui 2>/dev/null
    sleep 5
    
    success "服务已启动"
    return 0
}

# =============================================================================
# 清理函数
# =============================================================================

# 清理旧备份
cleanup_old_backups() {
    local keep_days="${1:-7}"
    
    info "清理 $keep_days 天前的备份文件..."
    
    find "$BACKUP_DIR" -name "backup-*.tar.gz" -mtime +$keep_days -delete 2>/dev/null
    
    success "旧备份文件清理完成"
    return 0
}

# 错误清理
cleanup_on_error() {
    local backup_path="$1"
    
    warn "检测到错误，正在清理临时文件..."
    
    if [[ -n "$backup_path" && -d "$backup_path" ]]; then
        rm -rf "$backup_path"
    fi
    
    # 重启服务
    start_services
}

# =============================================================================
# 验证函数
# =============================================================================

# 验证备份完整性
verify_backup() {
    local archive_path="$1"
    
    info "验证备份文件完整性..."
    
    if [[ ! -f "$archive_path" ]]; then
        error "备份文件不存在: $archive_path"
        return 1
    fi
    
    # 检查tar文件完整性
    if ! tar -tzf "$archive_path" >/dev/null 2>&1; then
        error "备份文件损坏: $archive_path"
        return 1
    fi
    
    success "备份文件完整性验证通过"
    return 0
}
