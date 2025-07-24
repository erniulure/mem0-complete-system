# Mem0 备份迁移工具

一套完整的Mem0系统备份和恢复解决方案，支持一键备份、跨服务器迁移和完整恢复。

## 🎯 功能特性

- ✅ **完整备份**: 包含所有数据、配置和环境设置
- ✅ **一键恢复**: 在新服务器上快速恢复完整系统
- ✅ **数据验证**: 自动验证备份和恢复的完整性
- ✅ **版本兼容**: 支持跨版本迁移和兼容性检查
- ✅ **错误处理**: 完善的错误处理和回滚机制
- ✅ **进度显示**: 实时显示备份和恢复进度
- ✅ **安全可靠**: 包含校验和验证和数据完整性检查

## 📦 备份内容

### 核心数据
- 🗃️ **Qdrant向量数据库**: 所有collections和向量数据
- 🗄️ **PostgreSQL数据库**: 用户数据、权限和配置
- ⚙️ **配置文件**: mem0-config.yaml、docker-compose.yml等
- 🌍 **环境变量**: Docker环境变量和系统配置

### 元数据
- 📋 **备份信息**: 时间戳、版本、主机信息
- 🔍 **校验和**: 文件完整性验证
- 📊 **系统信息**: 操作系统、Docker版本等

## 🚀 快速开始

### 1. 备份当前系统

```bash
# 基本备份
./backup.sh

# 自定义备份名称
./backup.sh -n my-backup-20241224

# 包含日志文件的完整备份
./backup.sh -l

# 干运行（查看备份计划）
./backup.sh --dry-run
```

### 2. 在新服务器上恢复

```bash
# 1. 首先在新服务器上运行一键安装脚本
curl -sSL https://your-domain.com/install.sh | bash

# 2. 传输备份文件到新服务器
scp backup-20241224-143022.tar.gz user@new-server:/opt/mem0-complete-system/

# 3. 恢复系统
./restore.sh backup-20241224-143022.tar.gz

# 强制恢复（覆盖现有数据）
./restore.sh backup-20241224-143022.tar.gz --force
```

### 3. 验证系统

```bash
# 完整系统验证
./validate.sh

# 仅验证API功能
./validate.sh --api-only

# 仅验证数据完整性
./validate.sh --data-only
```

## 📖 详细使用说明

### 备份脚本 (backup.sh)

```bash
用法: ./backup.sh [选项]

选项:
    -h, --help          显示帮助信息
    -n, --name NAME     指定备份名称
    -d, --dry-run       干运行模式
    -q, --quiet         静默模式
    -l, --include-logs  包含日志文件
    --debug             启用调试模式

示例:
    ./backup.sh                     # 默认备份
    ./backup.sh -n prod-backup     # 生产环境备份
    ./backup.sh --dry-run          # 查看备份计划
```

### 恢复脚本 (restore.sh)

```bash
用法: ./restore.sh <备份文件> [选项]

选项:
    -h, --help           显示帮助信息
    -f, --force          强制恢复，覆盖现有数据
    -d, --dry-run        干运行模式
    -q, --quiet          静默模式
    -s, --skip-verify    跳过验证步骤
    --debug              启用调试模式

示例:
    ./restore.sh backup.tar.gz              # 基本恢复
    ./restore.sh backup.tar.gz --force      # 强制覆盖
    ./restore.sh backup.tar.gz --dry-run    # 查看恢复计划
```

### 验证脚本 (validate.sh)

```bash
用法: ./validate.sh [选项]

选项:
    -h, --help          显示帮助信息
    -q, --quiet         静默模式
    -v, --verbose       详细模式
    --api-only          仅验证API功能
    --data-only         仅验证数据完整性
    --config-only       仅验证配置文件
    --debug             启用调试模式
```

## 🔧 高级功能

### 自动化备份

创建定时备份任务：

```bash
# 添加到crontab
# 每天凌晨2点自动备份
0 2 * * * cd /opt/mem0-complete-system/backup-migration && ./backup.sh -q

# 每周日凌晨3点备份并包含日志
0 3 * * 0 cd /opt/mem0-complete-system/backup-migration && ./backup.sh -l -q
```

### 远程备份

```bash
# 备份并传输到远程服务器
./backup.sh -n remote-backup && \
scp backups/remote-backup-*.tar.gz user@backup-server:/backups/

# 从远程服务器恢复
scp user@backup-server:/backups/backup-20241224-143022.tar.gz . && \
./restore.sh backup-20241224-143022.tar.gz
```

### 批量操作

```bash
# 批量验证多个备份文件
for backup in backups/*.tar.gz; do
    echo "验证: $backup"
    if tar -tzf "$backup" >/dev/null 2>&1; then
        echo "✅ $backup 完整"
    else
        echo "❌ $backup 损坏"
    fi
done
```

## 📁 文件结构

```
backup-migration/
├── backup.sh              # 主备份脚本
├── restore.sh             # 主恢复脚本
├── validate.sh            # 系统验证脚本
├── backup-utils.sh        # 备份工具函数
├── restore-utils.sh       # 恢复工具函数
├── README.md              # 使用说明
└── backups/               # 备份文件目录
    ├── backup-20241224-143022.tar.gz
    ├── backup.log
    └── ...
```

### 备份文件内容

```
backup-YYYYMMDD-HHMMSS.tar.gz
├── metadata.json          # 备份元数据
├── checksums.md5          # 文件校验和
├── qdrant/                # Qdrant数据
│   ├── collection1.snapshot
│   └── collection2.snapshot
├── postgres/              # PostgreSQL数据
│   ├── mem0_users.sql
│   └── roles.sql
├── configs/               # 配置文件
│   ├── configs_mem0-config.yaml
│   ├── mem0-deployment_docker-compose.yml
│   └── mem0-deployment_.env
├── env/                   # 环境变量
│   ├── docker.env
│   └── system.env
└── logs/                  # 日志文件（可选）
    ├── mem0-api.log
    ├── mem0-qdrant.log
    └── backup.log
```

## ⚠️ 注意事项

### 备份前
1. 确保所有Mem0服务正在运行
2. 检查磁盘空间是否充足
3. 建议在低峰期执行备份

### 恢复前
1. 确保目标服务器已安装基础环境
2. 备份现有数据（如果需要）
3. 确认网络连接正常

### 安全建议
1. 定期验证备份文件完整性
2. 将备份文件存储在安全位置
3. 定期清理过期备份文件
4. 测试恢复流程的有效性

## 🐛 故障排除

### 常见问题

**Q: 备份失败，提示"服务未运行"**
A: 确保所有Mem0服务正在运行：`docker-compose ps`

**Q: 恢复时提示"目标环境检查失败"**
A: 确保已在目标服务器上运行一键安装脚本

**Q: 验证失败，显示"连接超时"**
A: 检查防火墙设置和端口开放情况

**Q: 备份文件过大**
A: 考虑不包含日志文件，或定期清理数据

### 日志查看

```bash
# 查看备份日志
tail -f backups/backup.log

# 查看Docker容器日志
docker logs mem0-api
docker logs mem0-qdrant
docker logs mem0-postgres
```

### 手动清理

```bash
# 清理旧备份（保留7天）
find backups/ -name "backup-*.tar.gz" -mtime +7 -delete

# 清理临时文件
rm -rf restore-temp/
```

## 📞 技术支持

如果遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 运行验证脚本检查系统状态
3. 确认系统依赖是否完整安装
4. 联系技术支持团队

---

**版本**: 1.0.0  
**更新时间**: 2024-12-24  
**兼容性**: Mem0 v1.0+, Docker 20.0+, Docker Compose 2.0+
