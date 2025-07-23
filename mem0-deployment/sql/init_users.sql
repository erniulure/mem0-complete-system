-- Mem0 用户管理系统数据库初始化脚本
-- 创建用户表和相关索引

-- 创建用户表
CREATE TABLE IF NOT EXISTS mem0_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    password_changed_at TIMESTAMP,
    password_reset_at TIMESTAMP,
    password_reset_by VARCHAR(50),
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_mem0_users_username ON mem0_users(username);
CREATE INDEX IF NOT EXISTS idx_mem0_users_user_id ON mem0_users(user_id);
CREATE INDEX IF NOT EXISTS idx_mem0_users_role ON mem0_users(role);
CREATE INDEX IF NOT EXISTS idx_mem0_users_active ON mem0_users(is_active);

-- 创建登录尝试记录表
CREATE TABLE IF NOT EXISTS mem0_login_attempts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_mem0_login_attempts_username ON mem0_login_attempts(username);
CREATE INDEX IF NOT EXISTS idx_mem0_login_attempts_time ON mem0_login_attempts(attempt_time);

-- 插入默认管理员账户（如果不存在）
INSERT INTO mem0_users (username, user_id, password_hash, role, is_active, created_at)
SELECT 
    'admin',
    'admin_default',
    -- 这是 'admin123' 的 SHA-256 哈希值
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
    'admin',
    true,
    CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM mem0_users WHERE username = 'admin'
);

-- 创建用户设置表
CREATE TABLE IF NOT EXISTS mem0_user_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES mem0_users(user_id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, setting_key)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_mem0_user_settings_user_id ON mem0_user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_mem0_user_settings_key ON mem0_user_settings(setting_key);

-- 创建会话表
CREATE TABLE IF NOT EXISTS mem0_user_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES mem0_users(user_id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_mem0_user_sessions_user_id ON mem0_user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_mem0_user_sessions_token ON mem0_user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_mem0_user_sessions_expires ON mem0_user_sessions(expires_at);

-- 清理过期会话的函数
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM mem0_user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 创建定时清理任务（需要pg_cron扩展，可选）
-- SELECT cron.schedule('cleanup-sessions', '0 */6 * * *', 'SELECT cleanup_expired_sessions();');

COMMENT ON TABLE mem0_users IS 'Mem0系统用户表';
COMMENT ON TABLE mem0_login_attempts IS 'Mem0系统登录尝试记录表';
COMMENT ON TABLE mem0_user_settings IS 'Mem0系统用户设置表';
COMMENT ON TABLE mem0_user_sessions IS 'Mem0系统用户会话表';

-- 输出初始化结果
DO $$
DECLARE
    user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM mem0_users;
    RAISE NOTICE '✅ Mem0用户表初始化完成，当前用户数: %', user_count;

    IF EXISTS (SELECT 1 FROM mem0_users WHERE username = 'admin') THEN
        RAISE NOTICE '✅ 默认管理员账户已创建 (用户名: admin, 密码: admin123)';
    END IF;
END $$;
