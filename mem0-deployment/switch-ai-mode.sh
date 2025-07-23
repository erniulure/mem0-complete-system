#!/bin/bash

# =============================================================================
# Mem0 AI模式切换脚本
# 用于在Gemini Balance和OpenAI之间快速切换
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

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 显示当前模式
show_current_mode() {
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "                    🔄 Mem0 AI模式切换器"
    echo "============================================================================="
    echo -e "${NC}"
    
    if [ -f ".env" ]; then
        local current_mode=$(grep "GEMINI_BALANCE_MODE=" .env | cut -d'=' -f2)
        echo "当前AI模式: ${current_mode:-未设置}"
    else
        echo "当前AI模式: 未配置"
    fi
    
    echo ""
    echo "可用模式："
    echo "  1) 🤖 Gemini Balance模式 - 使用Gemini Balance服务"
    echo "  2) 🔗 OpenAI模式 - 使用OpenAI API（备用方案）"
    echo "  3) 📊 查看当前配置"
    echo "  4) 🔄 重启服务"
    echo "  5) ❌ 退出"
    echo ""
}

# 切换到Gemini模式
switch_to_gemini() {
    log_step "切换到Gemini Balance模式..."
    
    # 更新.env文件
    sed -i 's/GEMINI_BALANCE_MODE=.*/GEMINI_BALANCE_MODE=external/' .env
    
    # 复制Gemini配置
    cp configs/mem0-config-gemini.yaml configs/mem0-config.yaml
    
    # 更新API URL
    local gemini_url=$(grep "EXTERNAL_GEMINI_BALANCE_URL=" .env | cut -d'=' -f2)
    if [ -n "$gemini_url" ]; then
        sed -i "s|OPENAI_BASE_URL=.*|OPENAI_BASE_URL=${gemini_url}|" .env
    fi
    
    log_success "已切换到Gemini Balance模式"
    log_info "配置文件已更新，请重启服务使配置生效"
}

# 切换到OpenAI模式
switch_to_openai() {
    log_step "切换到OpenAI模式..."
    
    # 检查OpenAI API Key
    local openai_key=$(grep "OPENAI_API_KEY=" .env | cut -d'=' -f2)
    if [ -z "$openai_key" ] || [ "$openai_key" = "your-openai-api-key-here" ]; then
        log_warning "未配置OpenAI API Key"
        read -p "请输入您的OpenAI API Key: " new_key
        if [ -n "$new_key" ]; then
            sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=${new_key}/" .env
        else
            log_error "未提供API Key，切换失败"
            return 1
        fi
    fi
    
    # 更新.env文件
    sed -i 's/GEMINI_BALANCE_MODE=.*/GEMINI_BALANCE_MODE=openai/' .env
    sed -i 's|OPENAI_BASE_URL=.*|OPENAI_BASE_URL=https://api.openai.com/v1|' .env
    
    # 复制OpenAI配置
    cp configs/mem0-config-openai.yaml configs/mem0-config.yaml
    
    log_success "已切换到OpenAI模式"
    log_info "配置文件已更新，请重启服务使配置生效"
}

# 显示当前配置
show_config() {
    log_step "当前配置信息："
    echo ""
    
    if [ -f ".env" ]; then
        echo "环境变量配置："
        echo "  AI模式: $(grep "GEMINI_BALANCE_MODE=" .env | cut -d'=' -f2)"
        echo "  API URL: $(grep "OPENAI_BASE_URL=" .env | cut -d'=' -f2)"
        echo "  API Key: $(grep "OPENAI_API_KEY=" .env | cut -d'=' -f2 | sed 's/\(.\{8\}\).*/\1.../')"
    fi
    
    echo ""
    if [ -f "configs/mem0-config.yaml" ]; then
        echo "Mem0配置文件："
        echo "  LLM Provider: $(grep -A2 "llm:" configs/mem0-config.yaml | grep "provider:" | awk '{print $2}')"
        echo "  LLM Model: $(grep -A4 "llm:" configs/mem0-config.yaml | grep "model:" | awk '{print $2}')"
        echo "  Embedder Model: $(grep -A2 "embedder:" configs/mem0-config.yaml | grep "model:" | awk '{print $2}')"
    fi
}

# 重启服务
restart_services() {
    log_step "重启Mem0服务..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose restart mem0-api mem0-webui
        log_success "服务重启完成"
        
        # 等待服务启动
        log_info "等待服务启动..."
        sleep 5
        
        # 检查服务状态
        if curl -s http://localhost:8888/ > /dev/null; then
            log_success "API服务运行正常"
        else
            log_warning "API服务可能未正常启动，请检查日志"
        fi
    else
        log_error "未找到docker-compose命令"
    fi
}

# 主函数
main() {
    while true; do
        show_current_mode
        read -p "请选择操作 (1-5): " choice
        
        case $choice in
            1)
                switch_to_gemini
                ;;
            2)
                switch_to_openai
                ;;
            3)
                show_config
                ;;
            4)
                restart_services
                ;;
            5)
                log_info "退出模式切换器"
                exit 0
                ;;
            *)
                log_error "无效选择，请重新输入"
                ;;
        esac
        
        echo ""
        read -p "按回车键继续..."
        clear
    done
}

# 运行主函数
main "$@"
