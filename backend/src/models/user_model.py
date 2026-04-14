"""
用户数据模型
"""
from datetime import datetime
import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import secrets
from datetime import datetime, timedelta

# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'piying.db'

# JWT密钥（生产环境应从环境变量读取）
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7天


class UserModel:
    """用户模型类"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                account_type TEXT DEFAULT 'student',
                avatar_url TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # 创建用户资源表（个人资源库）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL,
                resource_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # 创建用户统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                videos_count INTEGER DEFAULT 0,
                characters_count INTEGER DEFAULT 0,
                scenes_count INTEGER DEFAULT 0,
                motions_count INTEGER DEFAULT 0,
                total_resources INTEGER DEFAULT 0,
                usage_hours REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, username, email, password, account_type='student'):
        """创建新用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户名和邮箱是否已存在
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                conn.close()
                return None, '用户名或邮箱已存在'
            
            # 生成密码哈希
            password_hash = generate_password_hash(password)
            
            # 插入用户
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, account_type)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, account_type))
            
            user_id = cursor.lastrowid
            
            # 初始化用户统计
            cursor.execute('''
                INSERT INTO user_stats (user_id)
                VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            return user_id, None
        except sqlite3.Error as e:
            return None, str(e)
    
    def authenticate_user(self, username, password):
        """验证用户登录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, password_hash, account_type, avatar_url
                FROM users
                WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username, username))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return None, '用户不存在或已被禁用'
            
            user_id, db_username, db_email, password_hash, account_type, avatar_url = user
            
            # 验证密码
            if not check_password_hash(password_hash, password):
                return None, '密码错误'
            
            user_data = {
                'id': user_id,
                'username': db_username,
                'email': db_email,
                'account_type': account_type,
                'avatar_url': avatar_url
            }
            
            return user_data, None
        except sqlite3.Error as e:
            return None, str(e)
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, account_type, avatar_url, created_at
                FROM users
                WHERE id = ? AND is_active = 1
            ''', (user_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return None
            
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'account_type': user[3],
                'avatar_url': user[4],
                'created_at': user[5]
            }
        except sqlite3.Error:
            return None
    
    def get_user_stats(self, user_id):
        """获取用户统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT videos_count, characters_count, scenes_count, 
                       motions_count, total_resources, usage_hours
                FROM user_stats
                WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            conn.close()
            
            if not stats:
                return {
                    'videos_count': 0,
                    'characters_count': 0,
                    'scenes_count': 0,
                    'motions_count': 0,
                    'total_resources': 0,
                    'usage_hours': 0
                }
            
            return {
                'videos_count': stats[0],
                'characters_count': stats[1],
                'scenes_count': stats[2],
                'motions_count': stats[3],
                'total_resources': stats[4],
                'usage_hours': stats[5]
            }
        except sqlite3.Error:
            return {
                'videos_count': 0,
                'characters_count': 0,
                'scenes_count': 0,
                'motions_count': 0,
                'total_resources': 0,
                'usage_hours': 0
            }
    
    def update_user_stats(self, user_id, stats_dict):
        """更新用户统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            values = []
            for key, value in stats_dict.items():
                updates.append(f'{key} = ?')
                values.append(value)
            
            values.append(user_id)
            
            cursor.execute(f'''
                UPDATE user_stats
                SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', values)
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            return False
    
    def update_user_info(self, user_id, username=None, email=None, avatar_url=None):
        """更新用户基本信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            values = []
            
            if username is not None:
                # 检查用户名是否已被其他用户使用
                cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id))
                if cursor.fetchone():
                    conn.close()
                    return False, '用户名已被使用'
                updates.append('username = ?')
                values.append(username)
            
            if email is not None:
                # 检查邮箱是否已被其他用户使用
                cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, user_id))
                if cursor.fetchone():
                    conn.close()
                    return False, '邮箱已被使用'
                updates.append('email = ?')
                values.append(email)
            
            if avatar_url is not None:
                updates.append('avatar_url = ?')
                values.append(avatar_url)
            
            if not updates:
                conn.close()
                return False, '没有要更新的字段'
            
            updates.append('updated_at = CURRENT_TIMESTAMP')
            values.append(user_id)
            
            cursor.execute(f'''
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = ?
            ''', values)
            
            conn.commit()
            conn.close()
            return True, None
        except sqlite3.Error as e:
            return False, str(e)


def generate_jwt_token(user_data):
    """生成JWT token（教学后端需 user_id/username/email/role）"""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'email': user_data.get('email', ''),
        'role': user_data.get('account_type', 'student'),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token.decode('utf-8') if isinstance(token, bytes) else token


def verify_jwt_token(token):
    """验证JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, 'Token已过期'
    except jwt.InvalidTokenError:
        return None, 'Token无效'
