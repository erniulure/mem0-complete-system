#!/bin/bash

# =============================================================================
# Mem0 配置向导 - 交互式配置生成器
# 版本: v2.0
# 描述: 引导用户完成所有必要的配置设置
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

# 配置文件路径
ENV_FILE=".env"
CONFIG_FILE="configs/mem0-config.yaml"

# 默认配置
declare -A DEFAULT_CONFIG=(
    # 基础配置
    ["DEPLOYMENT_MODE"]="standalone"
    
    # 端口配置
    ["WEBUI_PORT"]="8503"
    ["MEM0_API_PORT"]="8888"
    ["POSTGRES_PORT"]="5432"
    ["QDRANT_PORT"]="6333"
    ["QDRANT_GRPC_PORT"]="6334"
    
    # 数据库配置
    ["POSTGRES_DB"]="mem0"
    ["POSTGRES_USER"]="mem0"
    ["POSTGRES_PASSWORD"]="mem0_secure_password_2024"
    ["POSTGRES_HOST"]="mem0-postgres"
    
    # AI服务配置
    ["GEMINI_BALANCE_MODE"]="external"
    ["EXTERNAL_GEMINI_BALANCE_URL"]="http://gemini-balance:8000/v1"
    ["EXTERNAL_GEMINI_BALANCE_TOKEN"]="q1q2q3q4"
    
    # 安全配置
    ["SESSION_SECRET_KEY"]="mem0-secret-key-change-in-production"
    ["DEFAULT_ADMIN_USERNAME"]="admin"
    ["DEFAULT_ADMIN_PASSWORD"]="admin123"
    
    # 高级配置
    ["LOG_LEVEL"]="INFO"
    ["DATA_PATH"]="./data"
    ["LOGS_PATH"]="./logs"
    ["HEALTH_CHECK_INTERVAL"]="30s"
    ["HEALTH_CHECK_TIMEOUT"]="10s"
    ["HEALTH_CHECK_RETRIES"]="5"
)

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 显示配置向导欢迎信息
show_wizard_welcome() {
    clear
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "                    ⚙️  Mem0 配置向导"
    echo "============================================================================="
    echo -e "${NC}"
    echo "本向导将引导您完成以下配置："
    echo ""
    echo "  🌐 网络和端口设置"
    echo "  🤖 AI服务配置"
    echo "  🗄️  数据库配置"
    echo "  🔐 安全设置"
    echo "  📊 性能和日志配置"
    echo ""
    echo -e "${YELLOW}提示：直接按回车使用默认值，输入值覆盖默认设置${NC}"
    echo ""
    read -p "按回车键开始配置..." -r
}

# 获取用户输入
get_input() {
    local prompt="$1"
    local default="$2"
    local description="$3"
    local value
    
    echo ""
    echo -e "${CYAN}$description${NC}"
    echo -e "${YELLOW}默认值: $default${NC}"
    read -p "$prompt: " value
    
    if [[ -z "$value" ]]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# 配置网络和端口
configure_network() {
    log_step "配置网络和端口设置"
    
    DEFAULT_CONFIG["WEBUI_PORT"]=$(get_input \
        "Web界面端口" \
        "${DEFAULT_CONFIG["WEBUI_PORT"]}" \
        "Web界面访问端口，用户通过此端口访问Mem0界面")
    
    DEFAULT_CONFIG["MEM0_API_PORT"]=$(get_input \
        "API服务端口" \
        "${DEFAULT_CONFIG["MEM0_API_PORT"]}" \
        "Mem0 API服务端口，用于内部API通信")
    
    DEFAULT_CONFIG["POSTGRES_PORT"]=$(get_input \
        "PostgreSQL端口" \
        "${DEFAULT_CONFIG["POSTGRES_PORT"]}" \
        "PostgreSQL数据库端口，存储用户数据和记忆")
    
    DEFAULT_CONFIG["QDRANT_PORT"]=$(get_input \
        "Qdrant端口" \
        "${DEFAULT_CONFIG["QDRANT_PORT"]}" \
        "Qdrant向量数据库端口，用于向量搜索")
}

# 配置AI服务
configure_ai_service() {
    log_step "配置AI服务"
    
    echo ""
    echo -e "${CYAN}选择AI服务模式：${NC}"
    echo "1) external - 使用外部Gemini Balance服务（推荐）"
    echo "2) integrated - 集成部署Gemini Balance"
    echo "3) openai - 使用OpenAI API"
    
    read -p "请选择 (1-3): " ai_choice
    
    case $ai_choice in
        1|"")
            DEFAULT_CONFIG["GEMINI_BALANCE_MODE"]="external"
            configure_external_ai
            ;;
        2)
            DEFAULT_CONFIG["GEMINI_BALANCE_MODE"]="integrated"
            configure_integrated_ai
            ;;
        3)
            DEFAULT_CONFIG["GEMINI_BALANCE_MODE"]="openai"
            configure_openai
            ;;
        *)
            log_warning "无效选择，使用默认外部模式"
            configure_external_ai
            ;;
    esac
}

# 配置外部AI服务
configure_external_ai() {
    DEFAULT_CONFIG["EXTERNAL_GEMINI_BALANCE_URL"]=$(get_input \
        "外部Gemini Balance URL" \
        "${DEFAULT_CONFIG["EXTERNAL_GEMINI_BALANCE_URL"]}" \
        "外部Gemini Balance服务的完整URL地址")
    
    DEFAULT_CONFIG["EXTERNAL_GEMINI_BALANCE_TOKEN"]=$(get_input \
        "访问令牌" \
        "${DEFAULT_CONFIG["EXTERNAL_GEMINI_BALANCE_TOKEN"]}" \
        "访问Gemini Balance服务的API令牌")
}

# 配置集成AI服务
configure_integrated_ai() {
    DEFAULT_CONFIG["GEMINI_BALANCE_PORT"]=$(get_input \
        "Gemini Balance端口" \
        "8000" \
        "集成部署的Gemini Balance服务端口")
    
    DEFAULT_CONFIG["MYSQL_ROOT_PASSWORD"]=$(get_input \
        "MySQL root密码" \
        "123456" \
        "Gemini Balance使用的MySQL数据库root密码")
}

# 配置OpenAI
configure_openai() {
    DEFAULT_CONFIG["OPENAI_API_KEY"]=$(get_input \
        "OpenAI API Key" \
        "your-openai-api-key-here" \
        "您的OpenAI API密钥")
    
    DEFAULT_CONFIG["OPENAI_BASE_URL"]=$(get_input \
        "OpenAI Base URL" \
        "https://api.openai.com/v1" \
        "OpenAI API基础URL，可使用代理服务")
}

# 配置数据库
configure_database() {
    log_step "配置数据库设置"
    
    DEFAULT_CONFIG["POSTGRES_DB"]=$(get_input \
        "数据库名称" \
        "${DEFAULT_CONFIG["POSTGRES_DB"]}" \
        "PostgreSQL数据库名称")
    
    DEFAULT_CONFIG["POSTGRES_USER"]=$(get_input \
        "数据库用户名" \
        "${DEFAULT_CONFIG["POSTGRES_USER"]}" \
        "PostgreSQL数据库用户名")
    
    DEFAULT_CONFIG["POSTGRES_PASSWORD"]=$(get_input \
        "数据库密码" \
        "${DEFAULT_CONFIG["POSTGRES_PASSWORD"]}" \
        "PostgreSQL数据库密码（建议使用强密码）")
}

# 配置安全设置
configure_security() {
    log_step "配置安全设置"
    
    DEFAULT_CONFIG["SESSION_SECRET_KEY"]=$(get_input \
        "会话密钥" \
        "${DEFAULT_CONFIG["SESSION_SECRET_KEY"]}" \
        "用于加密用户会话的密钥（生产环境必须更改）")
    
    DEFAULT_CONFIG["DEFAULT_ADMIN_USERNAME"]=$(get_input \
        "管理员用户名" \
        "${DEFAULT_CONFIG["DEFAULT_ADMIN_USERNAME"]}" \
        "系统默认管理员用户名")
    
    DEFAULT_CONFIG["DEFAULT_ADMIN_PASSWORD"]=$(get_input \
        "管理员密码" \
        "${DEFAULT_CONFIG["DEFAULT_ADMIN_PASSWORD"]}" \
        "系统默认管理员密码（建议首次登录后修改）")
}

# 配置高级设置
configure_advanced() {
    log_step "配置高级设置"
    
    echo ""
    echo -e "${CYAN}是否配置高级设置？(y/N)${NC}"
    read -p "选择: " advanced_choice
    
    if [[ "$advanced_choice" =~ ^[Yy]$ ]]; then
        DEFAULT_CONFIG["LOG_LEVEL"]=$(get_input \
            "日志级别" \
            "${DEFAULT_CONFIG["LOG_LEVEL"]}" \
            "系统日志级别：DEBUG(详细) | INFO(一般) | WARNING(警告) | ERROR(错误)")
        
        DEFAULT_CONFIG["DATA_PATH"]=$(get_input \
            "数据存储路径" \
            "${DEFAULT_CONFIG["DATA_PATH"]}" \
            "系统数据文件存储路径")
        
        DEFAULT_CONFIG["LOGS_PATH"]=$(get_input \
            "日志存储路径" \
            "${DEFAULT_CONFIG["LOGS_PATH"]}" \
            "系统日志文件存储路径")
    fi
}

# 生成.env文件
generate_env_file() {
    log_step "生成环境配置文件..."
    
    cat > "$ENV_FILE" << EOF
# ===========================================
# Mem0 记忆管理系统 - 环境配置文件
# 生成时间: $(date)
# ===========================================

# 基础配置
DEPLOYMENT_MODE=${DEFAULT_CONFIG["DEPLOYMENT_MODE"]}

# 端口配置
WEBUI_PORT=${DEFAULT_CONFIG["WEBUI_PORT"]}
MEM0_API_PORT=${DEFAULT_CONFIG["MEM0_API_PORT"]}
POSTGRES_PORT=${DEFAULT_CONFIG["POSTGRES_PORT"]}
QDRANT_PORT=${DEFAULT_CONFIG["QDRANT_PORT"]}
QDRANT_GRPC_PORT=${DEFAULT_CONFIG["QDRANT_GRPC_PORT"]}

# AI服务配置
GEMINI_BALANCE_MODE=${DEFAULT_CONFIG["GEMINI_BALANCE_MODE"]}
EXTERNAL_GEMINI_BALANCE_URL=${DEFAULT_CONFIG["EXTERNAL_GEMINI_BALANCE_URL"]}
EXTERNAL_GEMINI_BALANCE_TOKEN=${DEFAULT_CONFIG["EXTERNAL_GEMINI_BALANCE_TOKEN"]}
OPENAI_API_KEY=${DEFAULT_CONFIG["OPENAI_API_KEY"]:-}
OPENAI_BASE_URL=${DEFAULT_CONFIG["OPENAI_BASE_URL"]:-}

# 数据库配置
POSTGRES_DB=${DEFAULT_CONFIG["POSTGRES_DB"]}
POSTGRES_USER=${DEFAULT_CONFIG["POSTGRES_USER"]}
POSTGRES_PASSWORD=${DEFAULT_CONFIG["POSTGRES_PASSWORD"]}
POSTGRES_HOST=${DEFAULT_CONFIG["POSTGRES_HOST"]}

# 安全配置
SESSION_SECRET_KEY=${DEFAULT_CONFIG["SESSION_SECRET_KEY"]}
DEFAULT_ADMIN_USERNAME=${DEFAULT_CONFIG["DEFAULT_ADMIN_USERNAME"]}
DEFAULT_ADMIN_PASSWORD=${DEFAULT_CONFIG["DEFAULT_ADMIN_PASSWORD"]}

# 高级配置
LOG_LEVEL=${DEFAULT_CONFIG["LOG_LEVEL"]}
DATA_PATH=${DEFAULT_CONFIG["DATA_PATH"]}
LOGS_PATH=${DEFAULT_CONFIG["LOGS_PATH"]}
HEALTH_CHECK_INTERVAL=${DEFAULT_CONFIG["HEALTH_CHECK_INTERVAL"]}
HEALTH_CHECK_TIMEOUT=${DEFAULT_CONFIG["HEALTH_CHECK_TIMEOUT"]}
HEALTH_CHECK_RETRIES=${DEFAULT_CONFIG["HEALTH_CHECK_RETRIES"]}
EOF
    
    log_success "环境配置文件已生成: $ENV_FILE"
}

# 主函数
main() {
    show_wizard_welcome
    configure_network
    configure_ai_service
    configure_database
    configure_security
    configure_advanced
    generate_env_file
    
    log_success "配置向导完成！"
    echo ""
    echo -e "${YELLOW}配置文件已生成，您可以随时使用 ./config-manager.sh 进行修改${NC}"
}

# 运行主函数
main "$@"
