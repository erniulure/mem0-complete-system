#!/bin/bash

# MCP-mem0 启动脚本 - 专为Augment优化
# 使用方法: ./start-for-augment.sh [user_id]

set -e

# 默认配置
DEFAULT_USER_ID=${1:-"augment_user"}
MEM0_API_URL=${MEM0_API_URL:-"http://localhost:8888"}
DOCKER_IMAGE=${DOCKER_IMAGE:-"mcp-mem0-stdio"}

echo "🚀 启动MCP-mem0服务 (Augment模式)"
echo "📋 配置信息:"
echo "   - 用户ID: $DEFAULT_USER_ID"
echo "   - Mem0 API: $MEM0_API_URL"
echo "   - Docker镜像: $DOCKER_IMAGE"
echo ""

# 检查Mem0 API是否可用
echo "🔍 检查Mem0 API连接..."
if curl -s --fail "$MEM0_API_URL/memories?user_id=test" > /dev/null 2>&1; then
    echo "✅ Mem0 API连接正常"
else
    echo "❌ 无法连接到Mem0 API: $MEM0_API_URL"
    echo "请确保Mem0服务正在运行"
    exit 1
fi

# 检查Docker镜像是否存在
echo "🔍 检查Docker镜像..."
if docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
    echo "✅ Docker镜像存在: $DOCKER_IMAGE"
else
    echo "❌ Docker镜像不存在: $DOCKER_IMAGE"
    echo "正在构建镜像..."
    docker build -t "$DOCKER_IMAGE" .
fi

echo ""
echo "🎯 MCP-mem0服务已准备就绪！"
echo ""
echo "📝 Augment配置 (复制到你的MCP配置中):"
echo "{"
echo "  \"mcpServers\": {"
echo "    \"mem0-coding-preferences\": {"
echo "      \"command\": \"docker\","
echo "      \"args\": [\"run\", \"--rm\", \"-i\", \"--network\", \"host\", \"$DOCKER_IMAGE\"],"
echo "      \"env\": {"
echo "        \"TRANSPORT\": \"stdio\","
echo "        \"DEFAULT_USER_ID\": \"$DEFAULT_USER_ID\","
echo "        \"MEM0_API_URL\": \"$MEM0_API_URL\""
echo "      }"
echo "    }"
echo "  }"
echo "}"
echo ""
echo "🔧 可用的工具:"
echo "   - add_coding_preference: 添加代码偏好和知识"
echo "   - get_all_coding_preferences: 获取所有存储的偏好"
echo "   - search_coding_preferences: 语义搜索代码偏好"
echo ""
echo "✨ 配置完成后，重启Augment即可使用！"
