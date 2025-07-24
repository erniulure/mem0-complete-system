#!/bin/bash

# =============================================================================
# Mem0 完整系统自动安装测试脚本
# 用于验证一键安装脚本的自动化配置功能
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# 清理现有环境
cleanup_environment() {
    log_step "清理现有环境..."
    
    # 停止所有相关容器
    docker stop $(docker ps -q --filter "name=mem0") 2>/dev/null || true
    docker stop $(docker ps -q --filter "name=gemini") 2>/dev/null || true
    
    # 删除容器
    docker rm $(docker ps -aq --filter "name=mem0") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=gemini") 2>/dev/null || true
    
    # 删除网络
    docker network rm mem0-deployment_mem0-network 2>/dev/null || true
    docker network rm mem0-shared-network 2>/dev/null || true
    docker network rm gemini-balance_default 2>/dev/null || true
    
    log_success "环境清理完成"
}

# 测试完整安装流程
test_full_installation() {
    log_step "测试完整安装流程..."
    
    # 运行一键安装
    ./install.sh --auto
    
    # 等待服务完全启动
    log_info "等待服务完全启动..."
    sleep 30
}

# 验证服务状态
verify_services() {
    log_step "验证服务状态..."
    
    local all_ok=true
    
    # 检查Gemini Balance
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_success "Gemini Balance: 运行正常"
    else
        log_error "Gemini Balance: 服务异常"
        all_ok=false
    fi
    
    # 检查Mem0 API
    if curl -s http://localhost:8888/ | grep -q "Mem0 API"; then
        log_success "Mem0 API: 运行正常"
    else
        log_error "Mem0 API: 服务异常"
        all_ok=false
    fi
    
    # 检查Web界面
    if curl -s http://localhost:8503/ | grep -q "Streamlit"; then
        log_success "Web界面: 运行正常"
    else
        log_error "Web界面: 服务异常"
        all_ok=false
    fi
    
    if $all_ok; then
        return 0
    else
        return 1
    fi
}

# 测试API功能
test_api_functionality() {
    log_step "测试API功能..."
    
    # 测试添加记忆
    local add_result=$(curl -s -X POST http://localhost:8888/memories \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [
                {"role": "user", "content": "我喜欢喝绿茶"}
            ],
            "user_id": "test_user_auto"
        }')
    
    if echo "$add_result" | grep -q "results"; then
        log_success "记忆添加: 测试通过"
        
        # 测试搜索记忆
        local search_result=$(curl -s -X POST http://localhost:8888/search \
            -H "Content-Type: application/json" \
            -d '{
                "query": "绿茶",
                "user_id": "test_user_auto",
                "limit": 5
            }')
        
        if echo "$search_result" | grep -q "绿茶"; then
            log_success "记忆搜索: 测试通过"
            return 0
        else
            log_error "记忆搜索: 测试失败"
            return 1
        fi
    else
        log_error "记忆添加: 测试失败"
        echo "响应: $add_result"
        return 1
    fi
}

# 测试配置自动修复
test_auto_configuration() {
    log_step "测试配置自动修复..."
    
    # 检查环境变量是否正确设置
    local openai_key=$(docker exec mem0-api env | grep OPENAI_API_KEY | cut -d'=' -f2)
    local openai_url=$(docker exec mem0-api env | grep OPENAI_BASE_URL | cut -d'=' -f2)
    
    if [ "$openai_key" = "q1q2q3q4" ] && [ "$openai_url" = "http://gemini-balance:8000/v1" ]; then
        log_success "环境变量配置: 正确"
    else
        log_error "环境变量配置: 错误"
        echo "OPENAI_API_KEY: $openai_key"
        echo "OPENAI_BASE_URL: $openai_url"
        return 1
    fi
    
    # 检查配置文件是否使用Gemini配置
    if docker exec mem0-api cat /app/configs/mem0-config.yaml | grep -q "gemini-2.0-flash-exp"; then
        log_success "配置文件: 使用Gemini配置"
    else
        log_error "配置文件: 未使用Gemini配置"
        return 1
    fi
    
    return 0
}

# 生成测试报告
generate_report() {
    log_step "生成测试报告..."
    
    echo ""
    echo "============================================================================="
    echo "                    📊 自动安装测试报告"
    echo "============================================================================="
    echo ""
    
    # 显示容器状态
    echo "🐳 Docker容器状态："
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(mem0|gemini|postgres|qdrant)"
    
    echo ""
    echo "🌐 服务访问地址："
    echo "  📱 Web界面: http://localhost:8503"
    echo "  🔌 API服务: http://localhost:8888"
    echo "  📚 API文档: http://localhost:8888/docs"
    echo "  🤖 Gemini-Balance: http://localhost:8000"
    echo "  📊 Qdrant管理: http://localhost:6333/dashboard"
    echo ""
    
    echo "🔐 默认账户："
    echo "  👤 用户名: admin"
    echo "  🔑 密码: admin123"
    echo ""
}

# 主测试流程
main() {
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "              🧪 Mem0 完整系统自动安装测试"
    echo "============================================================================="
    echo -e "${NC}"
    
    cleanup_environment
    test_full_installation
    
    if verify_services; then
        log_success "服务验证通过"
        
        if test_auto_configuration; then
            log_success "配置验证通过"
            
            if test_api_functionality; then
                log_success "API功能测试通过"
                echo ""
                echo -e "${GREEN}🎉 所有测试通过！自动安装功能正常工作！${NC}"
            else
                log_error "API功能测试失败"
                exit 1
            fi
        else
            log_error "配置验证失败"
            exit 1
        fi
    else
        log_error "服务验证失败"
        exit 1
    fi
    
    generate_report
}

# 运行测试
main "$@"
