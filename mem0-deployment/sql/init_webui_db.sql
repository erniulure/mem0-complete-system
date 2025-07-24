-- WebUI数据库初始化脚本
-- 在同一个PostgreSQL实例中创建独立的webui数据库

-- 创建webui数据库（如果不存在）
SELECT 'CREATE DATABASE webui'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'webui')\gexec

-- 连接到webui数据库
\c webui

-- 创建WebUI用户设置表
CREATE TABLE IF NOT EXISTS webui_user_settings (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username, setting_key)
);

-- 创建WebUI会话表
CREATE TABLE IF NOT EXISTS webui_user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) NOT NULL,
    user_info JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建WebUI配置表
CREATE TABLE IF NOT EXISTS webui_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_webui_user_settings_username ON webui_user_settings(username);
CREATE INDEX IF NOT EXISTS idx_webui_user_settings_key ON webui_user_settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_username ON webui_user_sessions(username);
CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_session_id ON webui_user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_expires ON webui_user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_webui_config_key ON webui_config(config_key);

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

-- 插入默认WebUI配置
INSERT INTO webui_config (config_key, config_value, description)
SELECT 'webui_version', '2.0', 'WebUI版本号'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_config WHERE config_key = 'webui_version'
);

INSERT INTO webui_config (config_key, config_value, description)
SELECT 'database_initialized', 'true', 'WebUI数据库是否已初始化'
WHERE NOT EXISTS (
    SELECT 1 FROM webui_config WHERE config_key = 'database_initialized'
);

-- 清理过期会话的函数
CREATE OR REPLACE FUNCTION cleanup_expired_webui_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM webui_user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 添加表注释
COMMENT ON TABLE webui_user_settings IS 'WebUI用户设置表';
COMMENT ON TABLE webui_user_sessions IS 'WebUI用户会话表';
COMMENT ON TABLE webui_config IS 'WebUI系统配置表';

-- 输出初始化结果
DO $$
DECLARE
    settings_count INTEGER;
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO settings_count FROM webui_user_settings WHERE username = 'admin';
    SELECT COUNT(*) INTO config_count FROM webui_config;

    RAISE NOTICE '✅ WebUI数据库初始化完成';
    RAISE NOTICE '✅ 默认管理员WebUI设置已创建，配置项数: %', settings_count;
    RAISE NOTICE '✅ WebUI系统配置已创建，配置项数: %', config_count;
END $$;
