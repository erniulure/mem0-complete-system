#!/bin/bash

# =============================================================================
# Mem0 配置管理器 - 运行时配置修改工具
# 版本: v2.0
# 描述: 提供图形化界面管理所有配置参数
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

ENV_FILE=".env"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示主菜单
show_main_menu() {
    clear
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "                    ⚙️  Mem0 配置管理器"
    echo "============================================================================="
    echo -e "${NC}"
    echo "请选择操作："
    echo ""
    echo "  1) 📋 查看当前配置"
    echo "  2) 🌐 修改网络和端口配置"
    echo "  3) 🤖 修改AI服务配置"
    echo "  4) 🗄️  修改数据库配置"
    echo "  5) 🔐 修改安全配置"
    echo "  6) 📊 修改高级配置"
    echo "  7) 🔄 重启服务"
    echo "  8) 📝 查看服务日志"
    echo "  9) 📊 查看服务状态"
    echo "  0) 🚪 退出"
    echo ""
}

# 读取配置值
get_config_value() {
    local key="$1"
    if [[ -f "$ENV_FILE" ]]; then
        grep "^$key=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"'
    else
        echo ""
    fi
}

# 更新配置值
update_config_value() {
    local key="$1"
    local value="$2"
    
    if [[ -f "$ENV_FILE" ]]; then
        # 如果配置项存在，更新它
        if grep -q "^$key=" "$ENV_FILE"; then
            sed -i "s|^$key=.*|$key=$value|" "$ENV_FILE"
        else
            # 如果配置项不存在，添加它
            echo "$key=$value" >> "$ENV_FILE"
        fi
    else
        log_error "配置文件 $ENV_FILE 不存在"
        return 1
    fi
}

# 查看当前配置
view_current_config() {
    clear
    echo -e "${CYAN}当前配置概览${NC}"
    echo "============================================================================="
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "配置文件不存在，请先运行安装脚本"
        return 1
    fi
    
    echo -e "${YELLOW}🌐 网络配置:${NC}"
    echo "  Web界面端口: $(get_config_value 'WEBUI_PORT')"
    echo "  API服务端口: $(get_config_value 'MEM0_API_PORT')"
    echo "  PostgreSQL端口: $(get_config_value 'POSTGRES_PORT')"
    echo "  Qdrant端口: $(get_config_value 'QDRANT_PORT')"
    echo ""
    
    echo -e "${YELLOW}🤖 AI服务配置:${NC}"
    echo "  服务模式: $(get_config_value 'GEMINI_BALANCE_MODE')"
    echo "  外部服务URL: $(get_config_value 'EXTERNAL_GEMINI_BALANCE_URL')"
    echo "  访问令牌: $(get_config_value 'EXTERNAL_GEMINI_BALANCE_TOKEN' | sed 's/./*/g')"
    echo ""
    
    echo -e "${YELLOW}🗄️ 数据库配置:${NC}"
    echo "  数据库名: $(get_config_value 'POSTGRES_DB')"
    echo "  用户名: $(get_config_value 'POSTGRES_USER')"
    echo "  密码: $(get_config_value 'POSTGRES_PASSWORD' | sed 's/./*/g')"
    echo ""
    
    echo -e "${YELLOW}🔐 安全配置:${NC}"
    echo "  管理员用户: $(get_config_value 'DEFAULT_ADMIN_USERNAME')"
    echo "  会话密钥: $(get_config_value 'SESSION_SECRET_KEY' | sed 's/./*/g')"
    echo ""
    
    echo -e "${YELLOW}📊 高级配置:${NC}"
    echo "  日志级别: $(get_config_value 'LOG_LEVEL')"
    echo "  数据路径: $(get_config_value 'DATA_PATH')"
    echo "  日志路径: $(get_config_value 'LOGS_PATH')"
    echo ""
    
    read -p "按回车键返回主菜单..." -r
}

# 修改网络配置
modify_network_config() {
    clear
    echo -e "${CYAN}修改网络和端口配置${NC}"
    echo "============================================================================="
    
    local current_webui_port=$(get_config_value 'WEBUI_PORT')
    local current_api_port=$(get_config_value 'MEM0_API_PORT')
    local current_pg_port=$(get_config_value 'POSTGRES_PORT')
    local current_qdrant_port=$(get_config_value 'QDRANT_PORT')
    
    echo "当前配置："
    echo "  Web界面端口: $current_webui_port"
    echo "  API服务端口: $current_api_port"
    echo "  PostgreSQL端口: $current_pg_port"
    echo "  Qdrant端口: $current_qdrant_port"
    echo ""
    
    read -p "新的Web界面端口 [$current_webui_port]: " new_webui_port
    read -p "新的API服务端口 [$current_api_port]: " new_api_port
    read -p "新的PostgreSQL端口 [$current_pg_port]: " new_pg_port
    read -p "新的Qdrant端口 [$current_qdrant_port]: " new_qdrant_port
    
    # 更新配置
    [[ -n "$new_webui_port" ]] && update_config_value "WEBUI_PORT" "$new_webui_port"
    [[ -n "$new_api_port" ]] && update_config_value "MEM0_API_PORT" "$new_api_port"
    [[ -n "$new_pg_port" ]] && update_config_value "POSTGRES_PORT" "$new_pg_port"
    [[ -n "$new_qdrant_port" ]] && update_config_value "QDRANT_PORT" "$new_qdrant_port"
    
    log_success "网络配置已更新"
    echo ""
    log_warning "配置更改需要重启服务才能生效"
    read -p "是否现在重启服务？(y/N): " restart_choice
    
    if [[ "$restart_choice" =~ ^[Yy]$ ]]; then
        restart_services
    fi
}

# 修改AI服务配置
modify_ai_config() {
    clear
    echo -e "${CYAN}修改AI服务配置${NC}"
    echo "============================================================================="
    
    local current_mode=$(get_config_value 'GEMINI_BALANCE_MODE')
    local current_url=$(get_config_value 'EXTERNAL_GEMINI_BALANCE_URL')
    local current_token=$(get_config_value 'EXTERNAL_GEMINI_BALANCE_TOKEN')
    
    echo "当前配置："
    echo "  服务模式: $current_mode"
    echo "  外部服务URL: $current_url"
    echo "  访问令牌: ${current_token:0:8}..."
    echo ""
    
    echo "选择AI服务模式："
    echo "1) external - 外部Gemini Balance服务"
    echo "2) integrated - 集成部署"
    echo "3) openai - OpenAI API"
    
    read -p "选择模式 (1-3) [$current_mode]: " mode_choice
    
    case $mode_choice in
        1|external)
            update_config_value "GEMINI_BALANCE_MODE" "external"
            read -p "外部服务URL [$current_url]: " new_url
            read -p "访问令牌 [当前已设置]: " new_token
            [[ -n "$new_url" ]] && update_config_value "EXTERNAL_GEMINI_BALANCE_URL" "$new_url"
            [[ -n "$new_token" ]] && update_config_value "EXTERNAL_GEMINI_BALANCE_TOKEN" "$new_token"
            ;;
        2|integrated)
            update_config_value "GEMINI_BALANCE_MODE" "integrated"
            ;;
        3|openai)
            update_config_value "GEMINI_BALANCE_MODE" "openai"
            read -p "OpenAI API Key: " openai_key
            read -p "OpenAI Base URL [https://api.openai.com/v1]: " openai_url
            [[ -n "$openai_key" ]] && update_config_value "OPENAI_API_KEY" "$openai_key"
            [[ -n "$openai_url" ]] && update_config_value "OPENAI_BASE_URL" "$openai_url"
            ;;
    esac
    
    log_success "AI服务配置已更新"
    read -p "按回车键返回主菜单..." -r
}

# 修改数据库配置
modify_database_config() {
    clear
    echo -e "${CYAN}修改数据库配置${NC}"
    echo "============================================================================="

    local current_db=$(get_config_value 'POSTGRES_DB')
    local current_user=$(get_config_value 'POSTGRES_USER')
    local current_password=$(get_config_value 'POSTGRES_PASSWORD')

    echo "当前配置："
    echo "  数据库名: $current_db"
    echo "  用户名: $current_user"
    echo "  密码: ${current_password:0:8}..."
    echo ""

    read -p "新的数据库名 [$current_db]: " new_db
    read -p "新的用户名 [$current_user]: " new_user
    read -p "新的密码 [当前已设置]: " new_password

    # 更新配置
    [[ -n "$new_db" ]] && update_config_value "POSTGRES_DB" "$new_db"
    [[ -n "$new_user" ]] && update_config_value "POSTGRES_USER" "$new_user"
    [[ -n "$new_password" ]] && update_config_value "POSTGRES_PASSWORD" "$new_password"

    log_success "数据库配置已更新"
    echo ""
    log_warning "数据库配置更改需要重新初始化数据库"
    read -p "是否现在重启服务？(y/N): " restart_choice

    if [[ "$restart_choice" =~ ^[Yy]$ ]]; then
        restart_services
    fi

    read -p "按回车键返回主菜单..." -r
}

# 修改安全配置
modify_security_config() {
    clear
    echo -e "${CYAN}修改安全配置${NC}"
    echo "============================================================================="

    local current_secret=$(get_config_value 'SESSION_SECRET_KEY')
    local current_admin_user=$(get_config_value 'DEFAULT_ADMIN_USERNAME')
    local current_admin_pass=$(get_config_value 'DEFAULT_ADMIN_PASSWORD')

    echo "当前配置："
    echo "  会话密钥: ${current_secret:0:16}..."
    echo "  管理员用户: $current_admin_user"
    echo "  管理员密码: ${current_admin_pass:0:4}..."
    echo ""

    read -p "新的会话密钥 [当前已设置]: " new_secret
    read -p "新的管理员用户名 [$current_admin_user]: " new_admin_user
    read -p "新的管理员密码 [当前已设置]: " new_admin_pass

    # 更新配置
    [[ -n "$new_secret" ]] && update_config_value "SESSION_SECRET_KEY" "$new_secret"
    [[ -n "$new_admin_user" ]] && update_config_value "DEFAULT_ADMIN_USERNAME" "$new_admin_user"
    [[ -n "$new_admin_pass" ]] && update_config_value "DEFAULT_ADMIN_PASSWORD" "$new_admin_pass"

    log_success "安全配置已更新"
    read -p "按回车键返回主菜单..." -r
}

# 修改高级配置
modify_advanced_config() {
    clear
    echo -e "${CYAN}修改高级配置${NC}"
    echo "============================================================================="

    local current_log_level=$(get_config_value 'LOG_LEVEL')
    local current_data_path=$(get_config_value 'DATA_PATH')
    local current_logs_path=$(get_config_value 'LOGS_PATH')

    echo "当前配置："
    echo "  日志级别: $current_log_level"
    echo "  数据路径: $current_data_path"
    echo "  日志路径: $current_logs_path"
    echo ""

    echo "日志级别选项："
    echo "1) DEBUG - 详细调试信息"
    echo "2) INFO - 一般信息（推荐）"
    echo "3) WARNING - 警告信息"
    echo "4) ERROR - 仅错误信息"

    read -p "选择日志级别 (1-4) [$current_log_level]: " log_choice

    case $log_choice in
        1) update_config_value "LOG_LEVEL" "DEBUG" ;;
        2) update_config_value "LOG_LEVEL" "INFO" ;;
        3) update_config_value "LOG_LEVEL" "WARNING" ;;
        4) update_config_value "LOG_LEVEL" "ERROR" ;;
    esac

    read -p "新的数据路径 [$current_data_path]: " new_data_path
    read -p "新的日志路径 [$current_logs_path]: " new_logs_path

    [[ -n "$new_data_path" ]] && update_config_value "DATA_PATH" "$new_data_path"
    [[ -n "$new_logs_path" ]] && update_config_value "LOGS_PATH" "$new_logs_path"

    log_success "高级配置已更新"
    read -p "按回车键返回主菜单..." -r
}

# 重启服务
restart_services() {
    log_info "重启Mem0服务..."
    
    if docker-compose ps | grep -q "mem0"; then
        docker-compose down
        sleep 5
        docker-compose up -d
        log_success "服务重启完成"
    else
        log_warning "服务未运行，正在启动..."
        docker-compose up -d
    fi
    
    sleep 10
    check_service_status
}

# 查看服务状态
check_service_status() {
    clear
    echo -e "${CYAN}服务状态检查${NC}"
    echo "============================================================================="
    
    local services=("mem0-postgres" "mem0-qdrant" "mem0-api" "mem0-webui-persistent")
    
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$service.*Up"; then
            echo -e "  ✅ $service: ${GREEN}运行中${NC}"
        else
            echo -e "  ❌ $service: ${RED}未运行${NC}"
        fi
    done
    
    echo ""
    echo "访问地址："
    echo "  🌐 Web界面: http://localhost:$(get_config_value 'WEBUI_PORT')"
    echo "  🔌 API服务: http://localhost:$(get_config_value 'MEM0_API_PORT')"
    echo ""
    
    read -p "按回车键返回主菜单..." -r
}

# 查看服务日志
view_service_logs() {
    clear
    echo -e "${CYAN}选择要查看日志的服务${NC}"
    echo "============================================================================="
    echo "1) mem0-api - API服务日志"
    echo "2) mem0-webui - Web界面日志"
    echo "3) mem0-postgres - 数据库日志"
    echo "4) mem0-qdrant - 向量数据库日志"
    echo "5) 所有服务日志"
    echo ""
    
    read -p "选择服务 (1-5): " log_choice
    
    case $log_choice in
        1) docker-compose logs -f mem0-api ;;
        2) docker-compose logs -f mem0-webui-persistent ;;
        3) docker-compose logs -f mem0-postgres ;;
        4) docker-compose logs -f mem0-qdrant ;;
        5) docker-compose logs -f ;;
        *) log_error "无效选择" ;;
    esac
}

# 主循环
main() {
    while true; do
        show_main_menu
        read -p "请选择操作 (0-9): " choice
        
        case $choice in
            1) view_current_config ;;
            2) modify_network_config ;;
            3) modify_ai_config ;;
            4) modify_database_config ;;
            5) modify_security_config ;;
            6) modify_advanced_config ;;
            7) restart_services ;;
            8) view_service_logs ;;
            9) check_service_status ;;
            0) log_info "退出配置管理器"; exit 0 ;;
            *) log_error "无效选择，请重试" && sleep 2 ;;
        esac
    done
}

# 运行主函数
main "$@"
