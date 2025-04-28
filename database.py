import pymysql
import hashlib
from datetime import datetime

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
        self.create_tables()
        self.add_default_admin()
    
    def connect(self):
        try:
            self.connection = pymysql.connect(
                host='localhost',
                user='root',
                password='Why131415926',
                database='uav_detection',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print("数据库连接成功")
        except pymysql.MySQLError as e:
            print(f"数据库连接错误: {e}")
            # 如果数据库不存在，尝试创建
            if "Unknown database" in str(e):
                try:
                    temp_conn = pymysql.connect(
                        host='localhost',
                        user='root',
                        password='Why131415926',
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor
                    )
                    with temp_conn.cursor() as cursor:
                        cursor.execute("CREATE DATABASE uav_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
                    temp_conn.close()
                    
                    # 再次尝试连接
                    self.connection = pymysql.connect(
                        host='localhost',
                        user='root',
                        password='Why131415926',
                        database='uav_detection',
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor
                    )
                    print("数据库创建并连接成功")
                except pymysql.MySQLError as e:
                    print(f"创建数据库失败: {e}")
    
    def _hash_password(self, password):
        """使用SHA-256加盐哈希密码"""
        salt = "uav_detection_salt"  # 固定盐值，实际应用中应该每个用户使用不同的盐
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash
    
    def create_tables(self):
        if not self.connection:
            print("数据库未连接，无法创建表")
            return
        
        try:
            with self.connection.cursor() as cursor:
                # 创建用户表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                
                # 创建检测记录表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS detect (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    detection_type VARCHAR(20) NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'completed',
                    result TEXT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                
                self.connection.commit()
                print("数据库表创建成功")
        except pymysql.MySQLError as e:
            print(f"创建表失败: {e}")
    
    def add_default_admin(self):
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                # 检查是否已有admin用户
                cursor.execute("SELECT id FROM users WHERE username = 'admin'")
                if cursor.fetchone() is None:
                    # 加密密码
                    password = 'admin123'
                    hashed_password = self._hash_password(password)
                    
                    # 创建管理员用户
                    cursor.execute("""
                    INSERT INTO users (username, password, email, role, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """, ('admin', hashed_password, 'admin@example.com', 'admin', datetime.now()))
                    
                    self.connection.commit()
                    print("默认管理员用户创建成功")
        except pymysql.MySQLError as e:
            print(f"创建默认管理员失败: {e}")
    
    def verify_user(self, username, password):
        """验证用户登录"""
        if not self.connection:
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                
                hashed_password = self._hash_password(password)
                if user and user['password'] == hashed_password:
                    # 更新最后登录时间
                    cursor.execute("UPDATE users SET last_login = %s WHERE id = %s", 
                                 (datetime.now(), user['id']))
                    self.connection.commit()
                    return user
                return None
        except pymysql.MySQLError as e:
            print(f"用户验证错误: {e}")
            return None
    
    def register_user(self, username, password, email, role='user'):
        """注册新用户"""
        if not self.connection:
            return False, "数据库连接失败"
        
        try:
            with self.connection.cursor() as cursor:
                # 检查用户名是否已存在
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    return False, "用户名已存在"
                
                # 检查邮箱是否已存在
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    return False, "邮箱已注册"
                
                # 加密密码
                hashed_password = self._hash_password(password)
                
                # 创建用户
                cursor.execute("""
                INSERT INTO users (username, password, email, role, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """, (username, hashed_password, email, role, datetime.now()))
                
                self.connection.commit()
                return True, "注册成功"
        except pymysql.MySQLError as e:
            print(f"用户注册错误: {e}")
            return False, f"注册失败: {e}"
    
    def get_users(self):
        """获取所有用户"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id, username, email, role, created_at, last_login FROM users")
                return cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"获取用户列表错误: {e}")
            return []
    
    def get_user_by_id(self, user_id):
        """通过ID获取用户信息"""
        if not self.connection:
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT id, username, email, role, created_at, last_login FROM users WHERE id = %s", (user_id,))
                return cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"获取用户信息错误: {e}")
            return None
    
    def update_user(self, user_id, username, email, role=None, password=None):
        """更新用户信息"""
        if not self.connection:
            return False, "数据库连接失败"
        
        try:
            with self.connection.cursor() as cursor:
                # 检查用户名是否已存在（排除当前用户）
                cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
                if cursor.fetchone():
                    return False, "用户名已存在"
                
                # 检查邮箱是否已存在（排除当前用户）
                cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, user_id))
                if cursor.fetchone():
                    return False, "邮箱已注册"
                
                if password:
                    # 更新密码
                    hashed_password = self._hash_password(password)
                    
                    if role:
                        # 更新所有字段
                        cursor.execute("""
                        UPDATE users SET username = %s, password = %s, email = %s, role = %s
                        WHERE id = %s
                        """, (username, hashed_password, email, role, user_id))
                    else:
                        # 不更新角色
                        cursor.execute("""
                        UPDATE users SET username = %s, password = %s, email = %s
                        WHERE id = %s
                        """, (username, hashed_password, email, user_id))
                else:
                    if role:
                        # 不更新密码，但更新角色
                        cursor.execute("""
                        UPDATE users SET username = %s, email = %s, role = %s
                        WHERE id = %s
                        """, (username, email, role, user_id))
                    else:
                        # 只更新用户名和邮箱
                        cursor.execute("""
                        UPDATE users SET username = %s, email = %s
                        WHERE id = %s
                        """, (username, email, user_id))
                
                self.connection.commit()
                return True, "用户信息更新成功"
        except pymysql.MySQLError as e:
            print(f"更新用户信息错误: {e}")
            return False, f"更新失败: {e}"
    
    def delete_user(self, user_id):
        """删除用户"""
        if not self.connection:
            return False, "数据库连接失败"
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                self.connection.commit()
                return True, "用户删除成功"
        except pymysql.MySQLError as e:
            print(f"删除用户错误: {e}")
            return False, f"删除失败: {e}"
    
    def add_detection_record(self, user_id, detection_type, file_path, status='completed', result=None):
        """添加检测记录"""
        if not self.connection:
            return False, "数据库连接失败"
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO detect (user_id, detection_type, file_path, created_at, status, result)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, detection_type, file_path, datetime.now(), status, result))
                
                self.connection.commit()
                return True, "检测记录添加成功"
        except pymysql.MySQLError as e:
            print(f"添加检测记录错误: {e}")
            return False, f"添加记录失败: {e}"
    
    def get_detection_records(self, user_id=None):
        """获取检测记录
        如果提供user_id，则只获取该用户的记录
        否则获取所有记录
        """
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                if user_id:
                    cursor.execute("""
                    SELECT d.*, u.username 
                    FROM detect d
                    JOIN users u ON d.user_id = u.id
                    WHERE d.user_id = %s
                    ORDER BY d.created_at DESC
                    """, (user_id,))
                else:
                    cursor.execute("""
                    SELECT d.*, u.username 
                    FROM detect d
                    JOIN users u ON d.user_id = u.id
                    ORDER BY d.created_at DESC
                    """)
                return cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"获取检测记录错误: {e}")
            return []
    
    def delete_detection_record(self, record_id, user_id=None):
        """删除检测记录
        如果提供user_id，则只删除该用户的记录
        否则可以删除任何记录（管理员功能）
        """
        if not self.connection:
            return False, "数据库连接失败"
        
        try:
            with self.connection.cursor() as cursor:
                if user_id:
                    # 普通用户只能删除自己的记录
                    cursor.execute("DELETE FROM detect WHERE id = %s AND user_id = %s", (record_id, user_id))
                else:
                    # 管理员可以删除任何记录
                    cursor.execute("DELETE FROM detect WHERE id = %s", (record_id,))
                
                if cursor.rowcount > 0:
                    self.connection.commit()
                    return True, "检测记录删除成功"
                else:
                    return False, "检测记录不存在或无权删除"
        except pymysql.MySQLError as e:
            print(f"删除检测记录错误: {e}")
            return False, f"删除失败: {e}"
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("数据库连接已关闭") 