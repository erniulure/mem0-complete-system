#!/bin/bash

# =============================================================================
# Mem0 记忆管理系统 - 一键管理脚本
# 提供启动、停止、重启、状态查看、备份、恢复等功能
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="mem0"
VENV_PATH="$SCRIPT_DIR/venv"
BACKUP_DIR="/opt/mem0/backups"
LOG_DIR="/opt/mem0/logs"

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此操作需要root权限"
        log_info "请使用: sudo $0 $1"
        exit 1
    fi
}

# 启动服务
start_service() {
    log_info "启动Mem0服务..."

    # 启动Docker服务
    log_info "启动Mem0 API Docker容器..."
    cd $SCRIPT_DIR
    docker-compose up -d

    # 等待API服务启动
    log_info "等待API服务启动..."
    sleep 10

    # 启动Web界面服务
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_warning "Web界面服务已经在运行中"
    else
        systemctl start $SERVICE_NAME
        sleep 3
    fi

    if systemctl is-active --quiet $SERVICE_NAME; then
        log_success "服务启动成功"
        show_status
    else
        log_error "Web界面服务启动失败"
        systemctl status $SERVICE_NAME --no-pager
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止Mem0服务..."

    # 停止Web界面服务
    if systemctl is-active --quiet $SERVICE_NAME; then
        systemctl stop $SERVICE_NAME
        sleep 2
    else
        log_info "Web界面服务已经停止"
    fi

    # 停止Docker服务
    log_info "停止Mem0 API Docker容器..."
    cd $SCRIPT_DIR
    docker-compose down

    if ! systemctl is-active --quiet $SERVICE_NAME; then
        log_success "服务停止成功"
    else
        log_error "Web界面服务停止失败"
        exit 1
    fi
}

# 重启服务
restart_service() {
    log_info "重启Mem0服务..."
    stop_service
    start_service
}

# 显示服务状态
show_status() {
    echo ""
    echo "=============================================="
    echo "🔍 Mem0 服务状态"
    echo "=============================================="
    
    # 系统服务状态
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_success "系统服务: 运行中"
    else
        log_error "系统服务: 已停止"
    fi
    
    # 端口检查
    if netstat -tuln 2>/dev/null | grep -q ":8503 "; then
        log_success "Web界面端口 8503: 正常"
    else
        log_warning "Web界面端口 8503: 未监听"
    fi

    if netstat -tuln 2>/dev/null | grep -q ":8888 "; then
        log_success "API端口 8888: 正常"
    else
        log_warning "API端口 8888: 未监听"
    fi

    # Docker容器状态
    echo ""
    echo "🐳 Docker容器状态:"
    cd $SCRIPT_DIR
    docker-compose ps || echo "   无法获取Docker状态"
    
    # 进程信息
    echo ""
    echo "📊 进程信息:"
    ps aux | grep -E "(streamlit|mem0)" | grep -v grep || echo "   无相关进程运行"
    
    # 最近日志
    echo ""
    echo "📝 最近日志 (最后10行):"
    journalctl -u $SERVICE_NAME --no-pager -n 10 || echo "   无法获取日志"
    
    echo "=============================================="
}

# 查看日志
show_logs() {
    local lines=${2:-50}
    
    echo "=============================================="
    echo "📝 Mem0 服务日志 (最后 $lines 行)"
    echo "=============================================="
    
    if [[ "$1" == "follow" ]] || [[ "$1" == "-f" ]]; then
        log_info "实时查看日志 (Ctrl+C 退出)..."
        journalctl -u $SERVICE_NAME -f
    else
        journalctl -u $SERVICE_NAME --no-pager -n $lines
    fi
}

# 备份系统
backup_system() {
    log_info "开始备份Mem0系统..."
    
    # 创建备份目录
    mkdir -p $BACKUP_DIR
    
    # 生成备份文件名
    local backup_file="$BACKUP_DIR/mem0_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # 停止服务
    local was_running=false
    if systemctl is-active --quiet $SERVICE_NAME; then
        was_running=true
        stop_service
    fi
    
    # 创建备份
    cd $SCRIPT_DIR
    tar -czf "$backup_file" \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='logs' \
        --exclude='scripts_backup' \
        .
    
    # 恢复服务状态
    if [[ "$was_running" == true ]]; then
        start_service
    fi
    
    log_success "备份完成: $backup_file"
    
    # 清理旧备份（保留最近7个）
    find $BACKUP_DIR -name "mem0_backup_*.tar.gz" -type f -mtime +7 -delete 2>/dev/null || true
    
    echo ""
    echo "📦 备份文件列表:"
    ls -lh $BACKUP_DIR/mem0_backup_*.tar.gz 2>/dev/null || echo "   无备份文件"
}

# 恢复系统
restore_system() {
    if [[ -z "$2" ]]; then
        echo "=============================================="
        echo "📦 可用的备份文件:"
        echo "=============================================="
        ls -lh $BACKUP_DIR/mem0_backup_*.tar.gz 2>/dev/null || {
            log_error "未找到备份文件"
            exit 1
        }
        echo ""
        log_info "使用方法: $0 restore <备份文件名>"
        log_info "示例: $0 restore mem0_backup_20240723_120000.tar.gz"
        return 0
    fi
    
    local backup_file="$BACKUP_DIR/$2"
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    log_warning "即将恢复系统，这将覆盖当前配置！"
    read -p "确认继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "恢复操作已取消"
        exit 0
    fi
    
    log_info "开始恢复系统..."
    
    # 停止服务
    stop_service
    
    # 备份当前状态
    local current_backup="$BACKUP_DIR/mem0_before_restore_$(date +%Y%m%d_%H%M%S).tar.gz"
    cd $SCRIPT_DIR
    tar -czf "$current_backup" \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        .
    log_info "当前状态已备份到: $current_backup"
    
    # 恢复文件
    tar -xzf "$backup_file" -C $SCRIPT_DIR
    
    # 重新安装Python依赖
    source $VENV_PATH/bin/activate
    pip install -r requirements.txt
    
    # 启动服务
    start_service
    
    log_success "系统恢复完成"
}

# 更新系统
update_system() {
    log_info "更新Mem0系统..."
    
    # 停止服务
    local was_running=false
    if systemctl is-active --quiet $SERVICE_NAME; then
        was_running=true
        stop_service
    fi
    
    # 更新Python依赖
    cd $SCRIPT_DIR
    source $VENV_PATH/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt --upgrade
    
    # 恢复服务状态
    if [[ "$was_running" == true ]]; then
        start_service
    fi
    
    log_success "系统更新完成"
}

# Docker服务管理
docker_command() {
    local cmd="$2"

    case "$cmd" in
        "up")
            log_info "启动Docker容器..."
            cd $SCRIPT_DIR
            docker-compose up -d
            ;;
        "down")
            log_info "停止Docker容器..."
            cd $SCRIPT_DIR
            docker-compose down
            ;;
        "restart")
            log_info "重启Docker容器..."
            cd $SCRIPT_DIR
            docker-compose restart
            ;;
        "logs")
            log_info "查看Docker日志..."
            cd $SCRIPT_DIR
            docker-compose logs -f
            ;;
        "ps")
            log_info "Docker容器状态..."
            cd $SCRIPT_DIR
            docker-compose ps
            ;;
        "pull")
            log_info "更新Docker镜像..."
            cd $SCRIPT_DIR
            docker-compose pull
            ;;
        *)
            log_error "未知的Docker命令: $cmd"
            echo "可用命令: up, down, restart, logs, ps, pull"
            exit 1
            ;;
    esac
}

# 查看API日志
api_logs() {
    log_info "查看Mem0 API日志..."
    cd $SCRIPT_DIR
    docker-compose logs -f mem0-api
}

# 显示帮助信息
show_help() {
    echo "=============================================="
    echo "🛠️  Mem0 记忆管理系统 - 管理脚本"
    echo "=============================================="
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "可用命令:"
    echo "  start          启动服务"
    echo "  stop           停止服务"
    echo "  restart        重启服务"
    echo "  status         显示服务状态"
    echo "  logs [lines]   查看日志 (默认50行)"
    echo "  logs -f        实时查看日志"
    echo "  backup         备份系统"
    echo "  restore <file> 恢复系统"
    echo "  update         更新系统依赖"
    echo "  docker <cmd>   Docker管理 (up|down|restart|logs|ps|pull)"
    echo "  api-logs       查看API日志"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start                    # 启动服务"
    echo "  $0 logs 100                 # 查看最后100行日志"
    echo "  $0 logs -f                  # 实时查看日志"
    echo "  $0 backup                   # 备份系统"
    echo "  $0 restore backup_file.tar.gz  # 恢复系统"
    echo ""
    echo "=============================================="
}

# 主函数
main() {
    case "${1:-help}" in
        "start")
            check_root
            start_service
            ;;
        "stop")
            check_root
            stop_service
            ;;
        "restart")
            check_root
            restart_service
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs "$2" "$3"
            ;;
        "backup")
            check_root
            backup_system
            ;;
        "restore")
            check_root
            restore_system "$@"
            ;;
        "update")
            check_root
            update_system
            ;;
        "docker")
            check_root
            docker_command "$@"
            ;;
        "api-logs")
            api_logs
            ;;
        "help"|"-h"|"--help")
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
