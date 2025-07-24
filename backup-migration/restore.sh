#!/bin/bash

# =============================================================================
# Mem0 完整系统恢复脚本
# 版本: 1.0.0
# 作者: Mem0 Team
# 描述: 一键恢复Mem0系统的所有数据和配置
# =============================================================================

set -euo pipefail

# 导入工具函数
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/restore-utils.sh"

# 全局变量
BACKUP_FILE=""
FORCE_RESTORE=false
DRY_RUN=false
QUIET=false
SKIP_VERIFICATION=false

# =============================================================================
# 帮助信息
# =============================================================================

show_help() {
    cat << EOF
Mem0 系统恢复脚本

用法: $0 <备份文件> [选项]

参数:
    备份文件              备份文件路径 (.tar.gz格式)

选项:
    -h, --help           显示此帮助信息
    -f, --force          强制恢复，覆盖现有数据
    -d, --dry-run        干运行模式，不执行实际恢复
    -q, --quiet          静默模式，减少输出
    -s, --skip-verify    跳过恢复后的验证步骤
    --debug              启用调试模式

示例:
    $0 backup-20241224-143022.tar.gz           # 恢复指定备份
    $0 backup.tar.gz --force                   # 强制恢复，覆盖现有数据
    $0 backup.tar.gz --dry-run                 # 干运行，查看恢复计划
    $0 backup.tar.gz --skip-verify             # 跳过验证步骤

恢复内容:
    ✓ Qdrant向量数据库数据
    ✓ PostgreSQL用户数据
    ✓ Mem0配置文件
    ✓ Docker配置文件
    ✓ 环境变量和密钥

注意事项:
    1. 请确保已通过一键安装脚本安装了基础环境
    2. 恢复过程会停止现有服务并覆盖数据
    3. 建议在恢复前备份当前数据
    4. 恢复完成后会自动重启所有服务

EOF
}

# =============================================================================
# 参数解析
# =============================================================================

parse_args() {
    if [[ $# -eq 0 ]]; then
        error "请指定备份文件"
        echo "使用 $0 --help 查看帮助信息"
        exit 1
    fi
    
    BACKUP_FILE="$1"
    shift
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--force)
                FORCE_RESTORE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -s|--skip-verify)
                SKIP_VERIFICATION=true
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
# 预检查函数
# =============================================================================

pre_restore_checks() {
    info "执行恢复前检查..."
    
    # 检查备份文件
    if [[ ! -f "$BACKUP_FILE" ]]; then
        error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi
    
    # 验证备份文件
    if ! verify_backup "$BACKUP_FILE"; then
        error "备份文件验证失败"
        exit 1
    fi
    
    # 检查目标环境
    if ! check_target_environment; then
        error "目标环境检查失败"
        exit 1
    fi
    
    # 检查是否有现有数据
    if [[ "$FORCE_RESTORE" != "true" ]]; then
        local has_data=false
        
        # 检查Qdrant是否有数据
        if curl -s http://localhost:6333/collections 2>/dev/null | jq -r '.result.collections[]?' 2>/dev/null | grep -q .; then
            has_data=true
        fi
        
        # 检查PostgreSQL是否有数据
        if docker exec mem0-postgres psql -U postgres -l 2>/dev/null | grep -q "mem0_users"; then
            has_data=true
        fi
        
        if [[ "$has_data" == "true" ]]; then
            error "检测到现有数据，使用 --force 参数强制覆盖"
            exit 1
        fi
    fi
    
    success "恢复前检查通过"
    return 0
}

# 确认恢复操作
confirm_restore() {
    if [[ "$DRY_RUN" == "true" || "$QUIET" == "true" ]]; then
        return 0
    fi
    
    echo
    echo -e "${YELLOW}⚠️  警告: 此操作将覆盖现有的Mem0数据！${NC}"
    echo -e "📁 备份文件: ${CYAN}$BACKUP_FILE${NC}"
    echo -e "📊 文件大小: ${YELLOW}$(du -h "$BACKUP_FILE" | cut -f1)${NC}"
    echo
    
    read -p "确认继续恢复吗？(y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "恢复操作已取消"
        exit 0
    fi
}

# =============================================================================
# 主恢复流程
# =============================================================================

execute_restore() {
    local restore_dir="$RESTORE_DIR"
    
    # 创建临时恢复目录
    mkdir -p "$restore_dir"
    
    # 设置错误处理
    trap 'rollback_on_failure' ERR
    
    # 解压备份文件
    if ! extract_backup "$BACKUP_FILE" "$restore_dir"; then
        exit 1
    fi
    
    # 验证备份完整性
    if ! verify_backup_integrity "$restore_dir"; then
        exit 1
    fi
    
    # 读取备份元数据
    if ! read_backup_metadata "$restore_dir"; then
        exit 1
    fi
    
    # 检查版本兼容性
    check_version_compatibility
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY RUN] 恢复计划:"
        echo "  📦 解压备份文件: ✓"
        echo "  🔍 验证文件完整性: ✓"
        echo "  📋 读取备份元数据: ✓"
        echo "  🔄 检查版本兼容性: ✓"
        echo "  🛑 停止现有服务: 计划中"
        echo "  🗃️ 恢复Qdrant数据: 计划中"
        echo "  🗄️ 恢复PostgreSQL数据: 计划中"
        echo "  ⚙️ 恢复配置文件: 计划中"
        echo "  🌍 恢复环境变量: 计划中"
        echo "  🚀 重启服务: 计划中"
        echo "  ✅ 验证恢复结果: 计划中"
        
        cleanup_restore_temp
        info "干运行完成"
        return 0
    fi
    
    # 停止现有服务
    info "停止现有服务..."
    cd "$PROJECT_ROOT/mem0-deployment" || exit 1
    docker-compose down 2>/dev/null || true
    
    # 执行恢复
    restore_configs "$restore_dir"
    restore_environment "$restore_dir"
    
    # 重建并启动服务
    rebuild_and_start_services
    
    # 等待服务启动
    if ! verify_services; then
        error "服务启动失败"
        exit 1
    fi
    
    # 恢复数据
    restore_qdrant "$restore_dir"
    restore_postgres "$restore_dir"
    
    # 验证恢复结果
    if [[ "$SKIP_VERIFICATION" != "true" ]]; then
        verify_restore_result
    fi
    
    # 清理临时文件
    cleanup_restore_temp
    
    success "恢复完成！"
    return 0
}

# =============================================================================
# 主函数
# =============================================================================

main() {
    # 解析参数
    parse_args "$@"
    
    # 初始化
    init_log
    
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${CYAN}"
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║                    Mem0 系统恢复工具                        ║"
        echo "║                     版本: 1.0.0                            ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
    
    info "开始恢复: $(basename "$BACKUP_FILE")"
    
    # 执行预检查
    pre_restore_checks
    
    # 确认恢复操作
    confirm_restore
    
    # 执行恢复
    execute_restore
    
    if [[ "$QUIET" != "true" && "$DRY_RUN" != "true" ]]; then
        echo
        echo -e "${GREEN}🎉 恢复成功完成！${NC}"
        echo
        echo -e "${CYAN}📋 恢复摘要:${NC}"
        echo -e "  📁 备份文件: ${YELLOW}$(basename "$BACKUP_FILE")${NC}"
        echo -e "  🕐 恢复时间: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
        echo -e "  🖥️  目标主机: ${YELLOW}$(hostname)${NC}"
        echo
        echo -e "${BLUE}🔗 访问地址:${NC}"
        echo -e "  🌐 WebUI: ${CYAN}http://localhost:8503${NC}"
        echo -e "  🔌 API: ${CYAN}http://localhost:8888${NC}"
        echo
        echo -e "${GREEN}✅ Mem0系统已成功恢复并运行！${NC}"
    fi
}

# 执行主函数
main "$@"
