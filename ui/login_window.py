from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                          QLabel, QLineEdit, QMessageBox, QFormLayout, QDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

class LoginWindow(QWidget):
    login_success = Signal(dict)  # 登录成功信号，传递用户信息
    register_clicked = Signal()   # 切换到注册窗口信号
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无人机目标检测系统 - 登录")
        self.resize(400, 250)
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("无人机目标检测系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 登录表单
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 20, 0, 20)
        
        # 用户名输入
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名")
        form_layout.addRow("用户名:", self.username_edit)
        
        # 密码输入
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_edit)
        
        main_layout.addLayout(form_layout)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.clicked.connect(self.login)
        
        # 注册按钮
        self.register_btn = QPushButton("注册")
        self.register_btn.clicked.connect(self.register)
        
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "登录提示", "用户名和密码不能为空")
            return
        
        # 登录验证逻辑在调用这个方法的地方实现
        self.login_success.emit({"username": username, "password": password})
    
    def register(self):
        # 触发切换到注册界面信号
        self.register_clicked.emit()
    
    def clear_fields(self):
        self.username_edit.clear()
        self.password_edit.clear()
        self.username_edit.setFocus()


class RegisterWindow(QWidget):
    register_success = Signal()    # 注册成功信号
    back_to_login = Signal()       # 返回登录窗口信号
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无人机目标检测系统 - 用户注册")
        self.resize(450, 300)
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("用户注册")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 注册表单
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 20, 0, 20)
        
        # 用户名输入
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名")
        form_layout.addRow("用户名:", self.username_edit)
        
        # 密码输入
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_edit)
        
        # 确认密码输入
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setPlaceholderText("请再次输入密码")
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("确认密码:", self.confirm_password_edit)
        
        # 邮箱输入
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("请输入电子邮箱")
        form_layout.addRow("电子邮箱:", self.email_edit)
        
        main_layout.addLayout(form_layout)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        # 注册按钮
        self.register_btn = QPushButton("注册")
        self.register_btn.clicked.connect(self.register)
        
        # 返回按钮
        self.back_btn = QPushButton("返回登录")
        self.back_btn.clicked.connect(self.back)
        
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(self.back_btn)
        
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def register(self):
        # 获取输入信息
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        confirm_password = self.confirm_password_edit.text().strip()
        email = self.email_edit.text().strip()
        
        # 验证输入
        if not username or not password or not confirm_password or not email:
            QMessageBox.warning(self, "注册提示", "所有字段都必须填写")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "注册提示", "两次输入的密码不一致")
            return
        
        # 验证邮箱格式
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "注册提示", "请输入有效的电子邮箱地址")
            return
        
        # 注册成功，发出信号
        user_info = {
            "username": username,
            "password": password,
            "email": email
        }
        
        # 注册逻辑在调用这个方法的地方实现
        self.user_info = user_info
        self.register_success.emit()
    
    def back(self):
        # 触发返回登录界面信号
        self.back_to_login.emit()
    
    def clear_fields(self):
        self.username_edit.clear()
        self.password_edit.clear()
        self.confirm_password_edit.clear()
        self.email_edit.clear()
        self.username_edit.setFocus() 