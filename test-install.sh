#!/bin/bash

# 测试完整安装流程
echo "🧪 测试Mem0完整安装流程"
echo "=========================="

# 清理环境
echo "🧹 清理现有环境..."
docker ps -q | xargs -r docker stop
docker ps -aq | xargs -r docker rm
docker volume prune -f
docker network prune -f

# 测试自动安装
echo ""
echo "🚀 开始自动安装测试..."
echo "=========================="

# 运行自动安装
./install.sh --auto

echo ""
echo "✅ 安装测试完成！"
