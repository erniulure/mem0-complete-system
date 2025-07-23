"""
数据库用户管理器 - 基于PostgreSQL的用户管理
"""

import os
import hashlib
import hmac
import time
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DatabaseUserManager:
    """基于PostgreSQL的用户管理器"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'mem0-postgres'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'mem0'),
            'user': os.getenv('POSTGRES_USER', 'mem0'),
            'password': os.getenv('POSTGRES_PASSWORD', 'mem0_secure_password_2024')
        }
    
    def _get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return hmac.compare_digest(self._hash_password(password), password_hash)
    
    def register_user(self, username: str, password: str, role: str = 'user') -> Tuple[bool, str]:
        """注册新用户"""
        if len(password) < 6:
            return False, "密码长度至少6位"
        
        # 生成唯一的user_id
        user_id = f"user_{int(time.time())}_{hash(username) % 10000}"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO mem0_users (username, user_id, password_hash, role, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (username, user_id, self._hash_password(password), role))
                    conn.commit()
                    return True, f"用户 {username} 注册成功"
        except psycopg2.IntegrityError:
            return False, "用户名已存在"
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            return False, f"注册失败: {str(e)}"
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """用户认证"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # 获取用户信息
                    cur.execute("""
                        SELECT * FROM mem0_users 
                        WHERE username = %s AND is_active = true
                    """, (username,))
                    
                    user = cur.fetchone()
                    if not user:
                        return False, "用户不存在或已被禁用", None
                    
                    # 检查是否被锁定
                    if user['locked_until'] and user['locked_until'] > datetime.now():
                        return False, "账户已被锁定，请稍后再试", None
                    
                    # 验证密码
                    if self._verify_password(password, user['password_hash']):
                        # 登录成功，更新最后登录时间
                        cur.execute("""
                            UPDATE mem0_users 
                            SET last_login = CURRENT_TIMESTAMP, login_attempts = 0, locked_until = NULL
                            WHERE username = %s
                        """, (username,))
                        conn.commit()
                        
                        return True, "登录成功", {
                            'username': user['username'],
                            'user_id': user['user_id'],
                            'role': user['role'],
                            'last_login': user['last_login'].isoformat() if user['last_login'] else None
                        }
                    else:
                        # 登录失败，增加尝试次数
                        new_attempts = user['login_attempts'] + 1
                        locked_until = None
                        
                        # 如果尝试次数过多，锁定账户
                        if new_attempts >= 5:
                            locked_until = datetime.now() + timedelta(minutes=30)
                        
                        cur.execute("""
                            UPDATE mem0_users 
                            SET login_attempts = %s, locked_until = %s
                            WHERE username = %s
                        """, (new_attempts, locked_until, username))
                        conn.commit()
                        
                        if locked_until:
                            return False, "登录失败次数过多，账户已被锁定30分钟", None
                        else:
                            return False, f"密码错误，剩余尝试次数: {5 - new_attempts}", None
                            
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            return False, f"认证失败: {str(e)}", None
    
    def get_user_list(self) -> List[Dict]:
        """获取用户列表"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT username, user_id, role, is_active, created_at, last_login
                        FROM mem0_users ORDER BY created_at DESC
                    """)
                    
                    users = []
                    for row in cur.fetchall():
                        users.append({
                            'username': row['username'],
                            'user_id': row['user_id'],
                            'role': row['role'],
                            'is_active': row['is_active'],
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'last_login': row['last_login'].isoformat() if row['last_login'] else None
                        })
                    return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改用户密码"""
        if len(new_password) < 6:
            return False, "新密码长度至少6位"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 验证旧密码
                    cur.execute("SELECT password_hash FROM mem0_users WHERE username = %s", (username,))
                    result = cur.fetchone()
                    
                    if not result or not self._verify_password(old_password, result[0]):
                        return False, "原密码错误"
                    
                    # 更新密码
                    cur.execute("""
                        UPDATE mem0_users 
                        SET password_hash = %s, password_changed_at = CURRENT_TIMESTAMP
                        WHERE username = %s
                    """, (self._hash_password(new_password), username))
                    conn.commit()
                    
                    return True, "密码修改成功"
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            return False, f"修改失败: {str(e)}"
    
    def reset_user_password(self, username: str, new_password: str) -> Tuple[bool, str]:
        """重置用户密码（管理员功能）"""
        if len(new_password) < 6:
            return False, "密码长度至少6位"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE mem0_users 
                        SET password_hash = %s, password_changed_at = CURRENT_TIMESTAMP,
                            login_attempts = 0, locked_until = NULL
                        WHERE username = %s
                    """, (self._hash_password(new_password), username))
                    
                    if cur.rowcount == 0:
                        return False, "用户不存在"
                    
                    conn.commit()
                    return True, f"用户 {username} 的密码已重置"
        except Exception as e:
            logger.error(f"重置密码失败: {e}")
            return False, f"重置失败: {str(e)}"
    
    def set_user_active(self, username: str, is_active: bool) -> bool:
        """设置用户状态"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE mem0_users SET is_active = %s WHERE username = %s
                    """, (is_active, username))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"设置用户状态失败: {e}")
            return False
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """删除用户"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 检查是否为管理员
                    cur.execute("SELECT role FROM mem0_users WHERE username = %s", (username,))
                    result = cur.fetchone()
                    
                    if not result:
                        return False, "用户不存在"
                    
                    if result[0] == 'admin':
                        return False, "不能删除管理员账户"
                    
                    cur.execute("DELETE FROM mem0_users WHERE username = %s", (username,))
                    conn.commit()
                    
                    return True, f"用户 {username} 已删除"
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            return False, f"删除失败: {str(e)}"
