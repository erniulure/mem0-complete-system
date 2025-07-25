#!/bin/bash

# =============================================================================
# Neo4j 图数据库初始化脚本
# 用于Mem0记忆管理系统的图存储配置
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[NEO4J-INIT]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[NEO4J-INIT]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[NEO4J-INIT]${NC} $1"
}

log_error() {
    echo -e "${RED}[NEO4J-INIT]${NC} $1"
}

# 等待Neo4j启动
wait_for_neo4j() {
    log_info "等待Neo4j启动..."
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker exec mem0-neo4j cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; then
            log_success "Neo4j已启动"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    log_error "Neo4j启动超时"
    return 1
}

# 创建Mem0专用索引和约束
create_mem0_schema() {
    log_info "创建Mem0图数据库模式..."
    
    # 创建节点标签和索引
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    // 创建用户节点索引
    CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.user_id);
    
    // 创建记忆节点索引
    CREATE INDEX memory_id_index IF NOT EXISTS FOR (m:Memory) ON (m.memory_id);
    CREATE INDEX memory_hash_index IF NOT EXISTS FOR (m:Memory) ON (m.hash);
    
    // 创建实体节点索引
    CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
    CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type);
    
    // 创建概念节点索引
    CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name);
    
    // 创建时间索引
    CREATE INDEX memory_created_index IF NOT EXISTS FOR (m:Memory) ON (m.created_at);
    CREATE INDEX memory_updated_index IF NOT EXISTS FOR (m:Memory) ON (m.updated_at);
    "
    
    log_success "Neo4j索引创建完成"
}

# 创建示例数据和查询
create_sample_queries() {
    log_info "创建示例查询..."
    
    # 创建常用查询的存储过程
    docker exec mem0-neo4j cypher-shell -u neo4j -p password "
    // 示例：查找用户的所有记忆
    // MATCH (u:User {user_id: 'admin'})-[:HAS_MEMORY]->(m:Memory)
    // RETURN m.content, m.created_at
    // ORDER BY m.created_at DESC;
    
    // 示例：查找实体的所有关系
    // MATCH (e:Entity {name: '刘昶'})-[r]-(related)
    // RETURN e, r, related;
    
    // 示例：查找相似记忆
    // MATCH (m1:Memory)-[:SIMILAR_TO]-(m2:Memory)
    // WHERE m1.user_id = 'admin'
    // RETURN m1.content, m2.content, m1.similarity_score;
    
    RETURN 'Sample queries ready' as status;
    "
    
    log_success "示例查询创建完成"
}

# 配置Neo4j性能参数
configure_performance() {
    log_info "配置Neo4j性能参数..."
    
    # 这些配置已经在docker-compose.yml中设置
    # - NEO4J_dbms_memory_heap_initial__size=512m
    # - NEO4J_dbms_memory_heap_max__size=2G
    # - NEO4J_dbms_memory_pagecache_size=1G
    
    log_success "性能参数配置完成"
}

# 验证安装
verify_installation() {
    log_info "验证Neo4j安装..."
    
    # 检查版本
    local version=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version" | grep -i neo4j | head -1)
    log_info "Neo4j版本: $version"
    
    # 检查APOC插件
    local apoc_status=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "CALL apoc.help('apoc') YIELD name RETURN count(name) as apoc_procedures" | tail -1)
    log_info "APOC插件状态: $apoc_status 个过程可用"
    
    # 检查索引
    local index_count=$(docker exec mem0-neo4j cypher-shell -u neo4j -p password "SHOW INDEXES YIELD name RETURN count(name) as index_count" | tail -1)
    log_info "索引数量: $index_count"
    
    log_success "Neo4j验证完成"
}

# 显示连接信息
show_connection_info() {
    echo ""
    echo "============================================================================="
    echo "🎯 Neo4j 图数据库连接信息"
    echo "============================================================================="
    echo ""
    echo "📊 Neo4j Browser (Web界面):"
    echo "   URL: http://localhost:7474"
    echo "   用户名: neo4j"
    echo "   密码: password"
    echo ""
    echo "🔗 Bolt连接 (应用程序):"
    echo "   URL: bolt://localhost:7687"
    echo "   用户名: neo4j"
    echo "   密码: password"
    echo ""
    echo "📝 常用Cypher查询示例:"
    echo "   // 查看所有节点类型"
    echo "   CALL db.labels()"
    echo ""
    echo "   // 查看所有关系类型"
    echo "   CALL db.relationshipTypes()"
    echo ""
    echo "   // 查看数据库统计"
    echo "   CALL apoc.meta.stats()"
    echo ""
    echo "============================================================================="
}

# 主函数
main() {
    log_info "开始初始化Neo4j图数据库..."
    
    # 等待Neo4j启动
    if ! wait_for_neo4j; then
        log_error "Neo4j启动失败，初始化中止"
        exit 1
    fi
    
    # 创建数据库模式
    create_mem0_schema
    
    # 创建示例查询
    create_sample_queries
    
    # 配置性能参数
    configure_performance
    
    # 验证安装
    verify_installation
    
    # 显示连接信息
    show_connection_info
    
    log_success "Neo4j图数据库初始化完成！"
}

# 执行主函数
main "$@"
