-- WebUI独立数据库初始化脚本
-- 创建WebUI专用的用户表和设置表

-- 创建WebUI用户表
CREATE TABLE IF NOT EXISTS webui_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    mem0_user_id VARCHAR(100),  -- 映射到mem0的user_id
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 创建WebUI用户设置表
CREATE TABLE IF NOT EXISTS webui_user_settings (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL REFERENCES webui_users(username) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, setting_key)
);

-- 创建WebUI会话表
CREATE TABLE IF NOT EXISTS webui_user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) NOT NULL REFERENCES webui_users(username) ON DELETE CASCADE,
    user_info JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建登录尝试记录表
CREATE TABLE IF NOT EXISTS webui_login_attempts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_webui_users_username ON webui_users(username);
CREATE INDEX IF NOT EXISTS idx_webui_users_mem0_user_id ON webui_users(mem0_user_id);
CREATE INDEX IF NOT EXISTS idx_webui_user_settings_username ON webui_user_settings(username);
CREATE INDEX IF NOT EXISTS idx_webui_user_settings_key ON webui_user_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_username ON webui_user_sessions(username);
CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_session_id ON webui_user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_expires ON webui_user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_webui_login_attempts_username ON webui_login_attempts(username);
CREATE INDEX IF NOT EXISTS idx_webui_login_attempts_time ON webui_login_attempts(attempt_time);

-- 插入默认管理员账户（如果不存在）
INSERT INTO webui_users (username, password_hash, role, mem0_user_id, is_active, created_at)
SELECT 
    'admin',
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',  -- admin123的SHA-256哈希值
    'admin',
    'admin_default',  -- 映射到mem0的admin_default用户
    true,
    CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM webui_users WHERE username = 'admin'
);

-- 插入默认管理员设置（如果不存在）
INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'custom_instructions', '请提取并结构化重要信息，保持清晰明了。'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'custom_instructions'
);

INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'include_content_types', '[]'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'include_content_types'
);

INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'exclude_content_types', '[]'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'exclude_content_types'
);

INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'max_results', '10'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'max_results'
);

INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'smart_reasoning', 'true'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'smart_reasoning'
);

INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'ai_api_url', 'http://gemini-balance:8000'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'ai_api_url'
);

INSERT INTO webui_user_settings (username, setting_key, setting_value)
SELECT 'admin', 'ai_api_key', 'q1q2q3q4'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_user_settings WHERE username = 'admin' AND setting_key = 'ai_api_key'
);

-- 清理过期会话的函数
CREATE OR REPLACE FUNCTION cleanup_expired_webui_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM webui_user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 添加表注释
COMMENT ON TABLE webui_users IS 'WebUI系统用户表';
COMMENT ON TABLE webui_user_settings IS 'WebUI系统用户设置表';
COMMENT ON TABLE webui_user_sessions IS 'WebUI系统用户会话表';
COMMENT ON TABLE webui_login_attempts IS 'WebUI系统登录尝试记录表';

-- 输出初始化结果
DO $$
DECLARE
    user_count INTEGER;
    settings_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM webui_users;
    SELECT COUNT(*) INTO settings_count FROM webui_user_settings WHERE username = 'admin';

    RAISE NOTICE '✅ WebUI数据库初始化完成，当前用户数: %', user_count;

    IF EXISTS (SELECT 1 FROM webui_users WHERE username = 'admin') THEN
        RAISE NOTICE '✅ 默认管理员账户已创建 (用户名: admin, 密码: admin123)';
        RAISE NOTICE '✅ 默认管理员配置已创建，配置项数: %', settings_count;
    END IF;
END $$;
