"""
WebUI独立数据库配置
"""
import os
import psycopg2
import psycopg2.extras
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class WebUIDatabase:
    """WebUI独立数据库管理器"""
    
    def __init__(self):
        """初始化WebUI数据库连接"""
        # 使用同一个PostgreSQL实例和数据库，但使用独立的表前缀
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),  # 使用同一个PostgreSQL实例
            'port': os.getenv('POSTGRES_PORT', '5432'),  # 使用同一个端口
            'database': os.getenv('POSTGRES_DB', 'mem0'),  # 使用同一个数据库
            'user': os.getenv('POSTGRES_USER', 'mem0'),  # 使用同一个用户
            'password': os.getenv('POSTGRES_PASSWORD', 'mem0_password')  # 使用同一个密码
        }
        
        # 初始化数据库表
        self._init_tables()
    
    def _get_connection(self):
        """获取数据库连接"""
        try:
            return psycopg2.connect(**self.db_config)
        except psycopg2.OperationalError as e:
            logger.warning(f"无法连接到WebUI独立数据库: {e}")
            logger.info("回退到兼容模式，WebUI将使用mem0数据库")
            raise ConnectionError("WebUI独立数据库不可用")
    
    def _init_tables(self):
        """初始化WebUI数据库表"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 创建用户表
                    cursor.execute("""
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
                        )
                    """)
                    
                    # 创建用户设置表
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS webui_user_settings (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(50) NOT NULL REFERENCES webui_users(username) ON DELETE CASCADE,
                            setting_key VARCHAR(100) NOT NULL,
                            setting_value TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(username, setting_key)
                        )
                    """)
                    
                    # 创建会话表
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS webui_user_sessions (
                            id SERIAL PRIMARY KEY,
                            session_id VARCHAR(255) UNIQUE NOT NULL,
                            username VARCHAR(50) NOT NULL REFERENCES webui_users(username) ON DELETE CASCADE,
                            user_info JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP NOT NULL,
                            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            is_active BOOLEAN DEFAULT TRUE
                        )
                    """)
                    
                    # 创建索引
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_webui_users_username ON webui_users(username)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_webui_user_settings_username ON webui_user_settings(username)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_username ON webui_user_sessions(username)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_webui_user_sessions_expires ON webui_user_sessions(expires_at)")
                    
                    # 插入默认管理员账户（如果不存在）
                    cursor.execute("""
                        INSERT INTO webui_users (username, password_hash, role, mem0_user_id, is_active, created_at)
                        SELECT 
                            'admin',
                            '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',  -- admin123的SHA-256
                            'admin',
                            'admin_default',  -- 映射到mem0的admin_default用户
                            true,
                            CURRENT_TIMESTAMP
                        WHERE NOT EXISTS (
                            SELECT 1 FROM webui_users WHERE username = 'admin'
                        )
                    """)
                    
                    # 插入默认管理员设置
                    default_settings = [
                        ('custom_instructions', '请提取并结构化重要信息，保持清晰明了。'),
                        ('include_content_types', '[]'),
                        ('exclude_content_types', '[]'),
                        ('max_results', '10'),
                        ('smart_reasoning', 'true'),
                        ('ai_api_url', 'http://gemini-balance:8000'),
                        ('ai_api_key', 'q1q2q3q4')
                    ]
                    
                    for setting_key, setting_value in default_settings:
                        cursor.execute("""
                            INSERT INTO webui_user_settings (username, setting_key, setting_value)
                            SELECT 'admin', %s, %s
                            WHERE NOT EXISTS (
                                SELECT 1 FROM webui_user_settings 
                                WHERE username = 'admin' AND setting_key = %s
                            )
                        """, (setting_key, setting_value, setting_key))
                    
                    conn.commit()
                    logger.info("WebUI数据库表初始化完成")
                    
        except Exception as e:
            logger.error(f"初始化WebUI数据库表失败: {e}")
            raise
    
    def get_user_settings(self, username: str) -> Dict[str, Any]:
        """获取用户设置"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT setting_key, setting_value
                        FROM webui_user_settings
                        WHERE username = %s
                    """, (username,))
                    
                    settings = {}
                    for row in cursor.fetchall():
                        settings[row['setting_key']] = row['setting_value']
                    
                    return settings
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return {}
    
    def save_user_setting(self, username: str, setting_key: str, setting_value: str) -> bool:
        """保存用户设置"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO webui_user_settings (username, setting_key, setting_value, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (username, setting_key)
                        DO UPDATE SET
                            setting_value = EXCLUDED.setting_value,
                            updated_at = CURRENT_TIMESTAMP
                    """, (username, setting_key, setting_value))
                    
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"保存用户设置失败: {e}")
            return False
    
    def get_mem0_user_id(self, username: str) -> Optional[str]:
        """获取用户对应的mem0 user_id"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT mem0_user_id FROM webui_users WHERE username = %s
                    """, (username,))
                    
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"获取mem0用户ID失败: {e}")
            return None

# 全局WebUI数据库实例
webui_db = WebUIDatabase()
