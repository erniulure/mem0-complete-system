#!/bin/bash

# ===========================================
# Mem0 记忆管理系统 - 一键部署脚本
# ===========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "Mem0 记忆管理系统 - 一键部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --mode=MODE           部署模式: standalone(默认) | with-ai | external"
    echo "  --port=PORT           Web界面端口 (默认: 8503)"
    echo "  --ai-port=PORT        AI服务端口 (默认: 8000)"
    echo "  --config=FILE         自定义环境配置文件"
    echo "  --help                显示此帮助信息"
    echo ""
    echo "部署模式说明:"
    echo "  standalone            仅部署Mem0核心服务，使用外部AI服务"
    echo "  with-ai              同时部署Gemini Balance AI服务"
    echo "  external             使用完全外部的服务"
    echo ""
    echo "示例:"
    echo "  $0                                    # 默认部署"
    echo "  $0 --mode=with-ai                    # 包含AI服务的完整部署"
    echo "  $0 --port=8080 --ai-port=8001       # 自定义端口"
    echo "  $0 --config=.env.production          # 使用自定义配置"
}

# 默认参数
DEPLOY_MODE="standalone"
WEBUI_PORT="8503"
AI_PORT="8000"
CONFIG_FILE=""

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --mode=*)
            DEPLOY_MODE="${arg#*=}"
            shift
            ;;
        --port=*)
            WEBUI_PORT="${arg#*=}"
            shift
            ;;
        --ai-port=*)
            AI_PORT="${arg#*=}"
            shift
            ;;
        --config=*)
            CONFIG_FILE="${arg#*=}"
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知参数: $arg"
            show_help
            exit 1
            ;;
    esac
done

print_info "开始部署 Mem0 记忆管理系统..."
print_info "部署模式: $DEPLOY_MODE"
print_info "Web端口: $WEBUI_PORT"
print_info "AI端口: $AI_PORT"

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    print_error "Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建环境配置文件
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    print_info "使用自定义配置文件: $CONFIG_FILE"
    cp "$CONFIG_FILE" .env
elif [ ! -f ".env" ]; then
    print_info "创建默认环境配置文件..."
    cp .env.example .env
    
    # 更新端口配置
    sed -i "s/WEBUI_PORT=8503/WEBUI_PORT=$WEBUI_PORT/" .env
    sed -i "s/GEMINI_BALANCE_PORT=8000/GEMINI_BALANCE_PORT=$AI_PORT/" .env
    
    # 根据部署模式更新配置
    if [ "$DEPLOY_MODE" = "with-ai" ]; then
        sed -i "s/GEMINI_BALANCE_MODE=external/GEMINI_BALANCE_MODE=integrated/" .env
    fi
fi

# 构建和启动服务
case $DEPLOY_MODE in
    "standalone")
        print_info "启动核心服务 (不包含AI服务)..."
        docker-compose up -d --build
        ;;
    "with-ai")
        print_info "启动完整服务 (包含AI服务)..."
        docker-compose -f docker-compose.yml -f docker-compose.ai-services.yml --profile ai-integrated up -d --build
        ;;
    "external")
        print_info "启动核心服务 (使用外部AI服务)..."
        docker-compose up -d --build
        ;;
    *)
        print_error "不支持的部署模式: $DEPLOY_MODE"
        exit 1
        ;;
esac

# 等待服务启动
print_info "等待服务启动..."
sleep 10

# 检查服务状态
print_info "检查服务状态..."
docker-compose ps

print_success "部署完成！"
print_info "访问地址: http://localhost:$WEBUI_PORT"
print_info "默认账户: admin / admin123"

if [ "$DEPLOY_MODE" = "with-ai" ]; then
    print_info "AI服务地址: http://localhost:$AI_PORT"
fi

print_warning "首次启动可能需要几分钟时间来初始化数据库和下载模型"
print_info "查看日志: docker-compose logs -f"
