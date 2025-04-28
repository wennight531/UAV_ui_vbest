from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                          QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                          QHeaderView, QMessageBox, QFormLayout, QLineEdit, 
                          QDialog, QTabWidget, QComboBox, QGroupBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from datetime import datetime

class UserDialog(QDialog):
    """用户信息编辑/添加对话框"""
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.user_data = user_data or {}  # 如果为None则是添加新用户
        
        if user_data:
            self.setWindowTitle("编辑用户")
        else:
            self.setWindowTitle("添加用户")
            
        self.setFixedSize(400, 350)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 用户名
        self.username_edit = QLineEdit(self.user_data.get('username', ''))
        form_layout.addRow("用户名:", self.username_edit)
        
        # 邮箱
        self.email_edit = QLineEdit(self.user_data.get('email', ''))
        form_layout.addRow("邮箱:", self.email_edit)
        
        # 角色
        self.role_combo = QComboBox()
        self.role_combo.addItems(["user", "admin"])
        current_role = self.user_data.get('role', 'user')
        self.role_combo.setCurrentText(current_role)
        form_layout.addRow("角色:", self.role_combo)
        
        # 密码（新密码）
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        if not self.user_data:
            self.password_edit.setPlaceholderText("请输入密码")
        else:
            self.password_edit.setPlaceholderText("留空表示不修改密码")
        form_layout.addRow("密码:", self.password_edit)
        
        # 确认密码
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        if not self.user_data:
            self.confirm_password_edit.setPlaceholderText("请再次输入密码")
        else:
            self.confirm_password_edit.setPlaceholderText("留空表示不修改密码")
        form_layout.addRow("确认密码:", self.confirm_password_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def validate(self):
        """验证表单数据"""
        username = self.username_edit.text().strip()
        email = self.email_edit.text().strip()
        password = self.password_edit.text().strip()
        confirm_password = self.confirm_password_edit.text().strip()
        
        # 基本验证
        if not username:
            QMessageBox.warning(self, "错误", "用户名不能为空")
            return False
        
        if not email:
            QMessageBox.warning(self, "错误", "邮箱不能为空")
            return False
        
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "错误", "请输入有效的邮箱地址")
            return False
        
        # 如果是新用户或者修改了密码，则验证密码
        if not self.user_data or password:
            if not self.user_data and not password:
                QMessageBox.warning(self, "错误", "新用户必须设置密码")
                return False
                
            if password != confirm_password:
                QMessageBox.warning(self, "错误", "两次输入的密码不一致")
                return False
        
        return True
    
    def get_user_data(self):
        """获取用户输入的数据"""
        if not self.validate():
            return None
            
        data = {
            "username": self.username_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "role": self.role_combo.currentText()
        }
        
        password = self.password_edit.text().strip()
        if password:
            data["password"] = password
        
        return data


class AdminWindow(QMainWindow):
    """管理员主窗口"""
    logout_signal = Signal()  # 注销信号
    back_to_detection_signal = Signal()  # 返回检测窗口信号
    
    def __init__(self, user_data, database):
        super().__init__()
        self.user_data = user_data
        self.db = database
        
        self.setWindowTitle(f"无人机目标检测系统 - 管理员: {user_data['username']}")
        self.resize(1000, 700)
        self.setup_ui()
    
    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 管理员信息
        admin_info_layout = QHBoxLayout()
        
        info_label = QLabel(f"当前管理员: {self.user_data['username']} | 角色: {self.user_data['role']}")
        
        # 返回检测窗口按钮
        back_btn = QPushButton("返回检测界面")
        back_btn.clicked.connect(self.back_to_detection)
        
        logout_btn = QPushButton("注销")
        logout_btn.clicked.connect(self.logout)
        
        admin_info_layout.addWidget(info_label)
        admin_info_layout.addStretch()
        admin_info_layout.addWidget(back_btn)
        admin_info_layout.addWidget(logout_btn)
        
        main_layout.addLayout(admin_info_layout)
        
        # 选项卡
        tab_widget = QTabWidget()
        
        # 用户管理选项卡
        user_tab = QWidget()
        user_layout = QVBoxLayout(user_tab)
        
        # 用户管理的操作按钮
        user_actions = QHBoxLayout()
        add_user_btn = QPushButton("添加用户")
        add_user_btn.clicked.connect(self.add_user)
        refresh_users_btn = QPushButton("刷新列表")
        refresh_users_btn.clicked.connect(self.load_users)
        
        user_actions.addWidget(add_user_btn)
        user_actions.addWidget(refresh_users_btn)
        user_actions.addStretch()
        
        user_layout.addLayout(user_actions)
        
        # 用户表格
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels(["ID", "用户名", "邮箱", "角色", "注册时间", "上次登录", "操作"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        user_layout.addWidget(self.users_table)
        
        # 检测记录选项卡
        detection_tab = QWidget()
        detection_layout = QVBoxLayout(detection_tab)
        
        # 检测记录操作按钮
        detect_actions = QHBoxLayout()
        refresh_detections_btn = QPushButton("刷新列表")
        refresh_detections_btn.clicked.connect(self.load_detections)
        
        detect_actions.addWidget(refresh_detections_btn)
        detect_actions.addStretch()
        
        detection_layout.addLayout(detect_actions)
        
        # 检测记录表格
        self.detections_table = QTableWidget()
        self.detections_table.setColumnCount(7)
        self.detections_table.setHorizontalHeaderLabels(["ID", "用户", "类型", "文件路径", "状态", "创建时间", "操作"])
        self.detections_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detections_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detections_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        detection_layout.addWidget(self.detections_table)
        
        # 添加选项卡
        tab_widget.addTab(user_tab, "用户管理")
        tab_widget.addTab(detection_tab, "检测记录管理")
        
        main_layout.addWidget(tab_widget)
        
        # 加载数据
        self.load_users()
        self.load_detections()
    
    def load_users(self):
        """加载所有用户信息"""
        users = self.db.get_users()
        
        # 清空表格
        self.users_table.setRowCount(0)
        
        # 填充数据
        for row_index, user in enumerate(users):
            self.users_table.insertRow(row_index)
            
            # ID
            id_item = QTableWidgetItem(str(user['id']))
            self.users_table.setItem(row_index, 0, id_item)
            
            # 用户名
            username_item = QTableWidgetItem(user['username'])
            self.users_table.setItem(row_index, 1, username_item)
            
            # 邮箱
            email_item = QTableWidgetItem(user['email'])
            self.users_table.setItem(row_index, 2, email_item)
            
            # 角色
            role_item = QTableWidgetItem(user['role'])
            self.users_table.setItem(row_index, 3, role_item)
            
            # 注册时间
            created_at = user['created_at']
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at_str = str(created_at)
            created_item = QTableWidgetItem(created_at_str)
            self.users_table.setItem(row_index, 4, created_item)
            
            # 上次登录
            last_login = user.get('last_login', '')
            if last_login:
                if isinstance(last_login, datetime):
                    last_login_str = last_login.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    last_login_str = str(last_login)
            else:
                last_login_str = "从未登录"
            last_login_item = QTableWidgetItem(last_login_str)
            self.users_table.setItem(row_index, 5, last_login_item)
            
            # 操作按钮
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建按钮
            edit_btn = QPushButton("编辑")
            user_id = user['id']  # 保存 ID 到局部变量
            edit_btn.clicked.connect(self.create_edit_callback(user_id))
            
            delete_btn = QPushButton("删除")
            # 禁止删除自己
            if user_id == self.user_data['id']:
                delete_btn.setEnabled(False)
                delete_btn.setToolTip("不能删除当前登录的用户")
            else:
                delete_btn.clicked.connect(self.create_delete_user_callback(user_id))
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.users_table.setCellWidget(row_index, 6, btn_widget)
    
    def create_edit_callback(self, user_id):
        """为编辑按钮创建回调函数"""
        return lambda: self.edit_user(user_id)
    
    def create_delete_user_callback(self, user_id):
        """为删除用户按钮创建回调函数"""
        return lambda: self.delete_user(user_id)
    
    def create_delete_detection_callback(self, record_id):
        """为删除检测记录按钮创建回调函数"""
        return lambda: self.delete_detection(record_id)
    
    def load_detections(self):
        """加载所有检测记录"""
        detections = self.db.get_detection_records()
        
        # 清空表格
        self.detections_table.setRowCount(0)
        
        # 填充数据
        for row_index, record in enumerate(detections):
            self.detections_table.insertRow(row_index)
            
            # ID
            id_item = QTableWidgetItem(str(record['id']))
            self.detections_table.setItem(row_index, 0, id_item)
            
            # 用户名
            username_item = QTableWidgetItem(record.get('username', str(record['user_id'])))
            self.detections_table.setItem(row_index, 1, username_item)
            
            # 类型
            type_item = QTableWidgetItem(record['detection_type'])
            self.detections_table.setItem(row_index, 2, type_item)
            
            # 文件路径
            path_item = QTableWidgetItem(record['file_path'])
            self.detections_table.setItem(row_index, 3, path_item)
            
            # 状态
            status_item = QTableWidgetItem(record['status'])
            self.detections_table.setItem(row_index, 4, status_item)
            
            # 创建时间
            created_at = record['created_at']
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at_str = str(created_at)
            created_item = QTableWidgetItem(created_at_str)
            self.detections_table.setItem(row_index, 5, created_item)
            
            # 操作按钮
            view_btn = QPushButton("查看")
            delete_btn = QPushButton("删除")
            record_id = record['id']  # 保存 ID 到局部变量
            file_path = record['file_path']  # 保存文件路径到局部变量
            detection_type = record['detection_type']  # 保存检测类型到局部变量
            
            view_btn.clicked.connect(self.create_view_detection_callback(file_path, detection_type))
            delete_btn.clicked.connect(self.create_delete_detection_callback(record_id))
            
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(view_btn)
            btn_layout.addWidget(delete_btn)
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.detections_table.setCellWidget(row_index, 6, btn_widget)
    
    def create_view_detection_callback(self, file_path, detection_type):
        """为查看检测记录按钮创建回调函数"""
        return lambda: self.view_detection_result(file_path, detection_type)
    
    def view_detection_result(self, file_path, detection_type):
        """查看检测结果"""
        import os
        
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", f"无法找到文件: {file_path}")
            return
            
        try:
            # 根据检测类型打开不同的查看器
            if detection_type == 'image':
                # 使用系统默认程序打开图片
                self.open_file(file_path)
            elif detection_type == 'video':
                # 使用系统默认程序打开视频
                self.open_file(file_path)
            elif detection_type == 'frames':
                # 打开帧序列所在的文件夹
                self.open_folder(file_path)
            else:
                # 默认使用系统默认程序打开
                self.open_file(file_path)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件: {str(e)}")
    
    def open_file(self, file_path):
        """使用系统默认程序打开文件"""
        import os
        import platform
        import subprocess
        
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', file_path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件: {str(e)}")
    
    def open_folder(self, folder_path):
        """打开文件夹"""
        import os
        import platform
        import subprocess
        
        try:
            if platform.system() == 'Windows':
                os.startfile(folder_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', folder_path], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', folder_path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件夹: {str(e)}")
    
    def add_user(self):
        """添加新用户"""
        dialog = UserDialog(parent=self)
        if dialog.exec():
            user_data = dialog.get_user_data()
            if user_data:
                success, message = self.db.register_user(
                    user_data['username'],
                    user_data['password'],
                    user_data['email'],
                    user_data['role']
                )
                
                if success:
                    QMessageBox.information(self, "成功", "用户添加成功")
                    self.load_users()
                else:
                    QMessageBox.warning(self, "错误", message)
    
    def edit_user(self, user_id):
        """编辑用户信息"""
        user = self.db.get_user_by_id(user_id)
        if not user:
            QMessageBox.warning(self, "错误", "找不到用户信息")
            return
        
        dialog = UserDialog(user, self)
        if dialog.exec():
            user_data = dialog.get_user_data()
            if user_data:
                success, message = self.db.update_user(
                    user_id,
                    user_data['username'],
                    user_data['email'],
                    user_data['role'],
                    user_data.get('password')
                )
                
                if success:
                    QMessageBox.information(self, "成功", "用户信息更新成功")
                    self.load_users()
                else:
                    QMessageBox.warning(self, "错误", message)
    
    def delete_user(self, user_id):
        """删除用户"""
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            "确定要删除此用户吗？此操作将同时删除该用户的所有检测记录。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.db.delete_user(user_id)
            if success:
                QMessageBox.information(self, "成功", "用户已删除")
                self.load_users()
                self.load_detections()  # 刷新检测记录，因为可能有关联删除
            else:
                QMessageBox.warning(self, "错误", message)
    
    def delete_detection(self, record_id):
        """删除检测记录"""
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            "确定要删除此检测记录吗？",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.db.delete_detection_record(record_id)
            if success:
                QMessageBox.information(self, "成功", "检测记录已删除")
                self.load_detections()
            else:
                QMessageBox.warning(self, "错误", message)
    
    def logout(self):
        """注销登录"""
        self.logout_signal.emit()
        self.close()
    
    def back_to_detection(self):
        """返回检测窗口"""
        self.back_to_detection_signal.emit()
        self.hide() 