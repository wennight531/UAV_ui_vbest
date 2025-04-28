from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                          QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                          QHeaderView, QMessageBox, QFormLayout, QLineEdit, 
                          QDialog, QGridLayout, QGroupBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from datetime import datetime

class UserProfileDialog(QDialog):
    """用户个人信息编辑对话框"""
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle("个人资料")
        self.setFixedSize(400, 300)
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
        
        # 密码（新密码）
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("留空表示不修改密码")
        form_layout.addRow("新密码:", self.password_edit)
        
        # 确认密码
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit.setPlaceholderText("留空表示不修改密码")
        form_layout.addRow("确认新密码:", self.confirm_password_edit)
        
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
    
    def get_user_data(self):
        # 返回用户输入的数据
        data = {
            "username": self.username_edit.text().strip(),
            "email": self.email_edit.text().strip(),
        }
        
        password = self.password_edit.text().strip()
        if password:
            if password != self.confirm_password_edit.text().strip():
                QMessageBox.warning(self, "错误", "两次输入的密码不一致")
                return None
            data["password"] = password
        
        return data


class UserWindow(QMainWindow):
    """用户主窗口"""
    logout_signal = Signal()  # 注销信号
    back_to_detection_signal = Signal()  # 返回检测窗口信号
    
    def __init__(self, user_data, database):
        super().__init__()
        self.user_data = user_data
        self.db = database
        
        self.setWindowTitle(f"无人机目标检测系统 - 用户: {user_data['username']}")
        self.resize(800, 600)
        self.setup_ui()
        self.load_detection_records()
    
    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部信息区域
        info_layout = QHBoxLayout()
        
        # 用户信息
        user_info_group = QGroupBox("用户信息")
        user_info_layout = QVBoxLayout()
        
        self.username_label = QLabel(f"用户名: {self.user_data['username']}")
        self.email_label = QLabel(f"邮箱: {self.user_data['email']}")
        last_login = self.user_data.get('last_login', '')
        if last_login:
            if isinstance(last_login, datetime):
                last_login_str = last_login.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_login_str = str(last_login)
        else:
            last_login_str = "首次登录"
        self.last_login_label = QLabel(f"上次登录: {last_login_str}")
        
        user_info_layout.addWidget(self.username_label)
        user_info_layout.addWidget(self.email_label)
        user_info_layout.addWidget(self.last_login_label)
        user_info_group.setLayout(user_info_layout)
        
        # 操作按钮
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout()
        
        self.profile_btn = QPushButton("编辑个人资料")
        self.profile_btn.clicked.connect(self.edit_profile)
        
        self.refresh_btn = QPushButton("刷新记录")
        self.refresh_btn.clicked.connect(self.load_detection_records)
        
        self.back_btn = QPushButton("返回检测界面")
        self.back_btn.clicked.connect(self.back_to_detection)
        
        self.logout_btn = QPushButton("注销")
        self.logout_btn.clicked.connect(self.logout)
        
        action_layout.addWidget(self.profile_btn)
        action_layout.addWidget(self.refresh_btn)
        action_layout.addWidget(self.back_btn)
        action_layout.addWidget(self.logout_btn)
        action_group.setLayout(action_layout)
        
        info_layout.addWidget(user_info_group, 2)
        info_layout.addWidget(action_group, 1)
        
        main_layout.addLayout(info_layout)
        
        # 检测记录表格
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(6)
        self.records_table.setHorizontalHeaderLabels(["ID", "类型", "文件路径", "状态", "创建时间", "操作"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        main_layout.addWidget(QLabel("我的检测记录"))
        main_layout.addWidget(self.records_table)
    
    def load_detection_records(self):
        """加载用户的检测记录"""
        records = self.db.get_detection_records(self.user_data['id'])
        
        # 清空表格
        self.records_table.setRowCount(0)
        
        # 填充数据
        for row_index, record in enumerate(records):
            self.records_table.insertRow(row_index)
            
            # ID
            id_item = QTableWidgetItem(str(record['id']))
            self.records_table.setItem(row_index, 0, id_item)
            
            # 类型
            type_item = QTableWidgetItem(record['detection_type'])
            self.records_table.setItem(row_index, 1, type_item)
            
            # 文件路径
            path_item = QTableWidgetItem(record['file_path'])
            self.records_table.setItem(row_index, 2, path_item)
            
            # 状态
            status_item = QTableWidgetItem(record['status'])
            self.records_table.setItem(row_index, 3, status_item)
            
            # 创建时间
            created_at = record['created_at']
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_at_str = str(created_at)
            created_item = QTableWidgetItem(created_at_str)
            self.records_table.setItem(row_index, 4, created_item)
            
            # 操作按钮
            view_btn = QPushButton("查看")
            delete_btn = QPushButton("删除")
            record_id = record['id']  # 保存 ID 到局部变量
            file_path = record['file_path']  # 保存文件路径到局部变量
            detection_type = record['detection_type']  # 保存检测类型到局部变量
            
            view_btn.clicked.connect(self.create_view_callback(file_path, detection_type))
            delete_btn.clicked.connect(self.create_delete_callback(record_id))
            
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(view_btn)
            btn_layout.addWidget(delete_btn)
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.records_table.setCellWidget(row_index, 5, btn_widget)
    
    def create_view_callback(self, file_path, detection_type):
        """为查看按钮创建回调函数"""
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
    
    def create_delete_callback(self, record_id):
        """为删除按钮创建回调函数"""
        return lambda: self.delete_record(record_id)
    
    def edit_profile(self):
        """编辑个人资料"""
        dialog = UserProfileDialog(self.user_data, self)
        if dialog.exec():
            new_data = dialog.get_user_data()
            if new_data:
                # 更新用户信息
                success, message = self.db.update_user(
                    self.user_data['id'], 
                    new_data['username'], 
                    new_data['email'], 
                    password=new_data.get('password')
                )
                
                if success:
                    # 更新本地用户数据
                    self.user_data['username'] = new_data['username']
                    self.user_data['email'] = new_data['email']
                    
                    # 更新UI
                    self.username_label.setText(f"用户名: {self.user_data['username']}")
                    self.email_label.setText(f"邮箱: {self.user_data['email']}")
                    self.setWindowTitle(f"无人机目标检测系统 - 用户: {self.user_data['username']}")
                    
                    QMessageBox.information(self, "成功", "个人资料更新成功")
                else:
                    QMessageBox.warning(self, "错误", message)
    
    def delete_record(self, record_id):
        """删除检测记录"""
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            "是否确认删除此检测记录？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.db.delete_detection_record(record_id, self.user_data['id'])
            if success:
                QMessageBox.information(self, "成功", "记录已删除")
                self.load_detection_records()
            else:
                QMessageBox.warning(self, "错误", message)
    
    def logout(self):
        """注销登录"""
        self.logout_signal.emit()
        self.close()
    
    def back_to_detection(self):
        """返回检测界面"""
        self.back_to_detection_signal.emit()
        self.hide() 