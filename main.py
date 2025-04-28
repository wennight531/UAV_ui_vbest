import sys
from PySide6.QtWidgets import QApplication
from ui import DetectionWindow, LoginWindow, RegisterWindow, UserWindow, AdminWindow
from database import Database

class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.db = Database()
        
        # 初始化界面
        self.login_window = None
        self.register_window = None
        self.detection_window = None
        self.user_window = None
        self.admin_window = None
        
        # 显示登录界面
        self.show_login_window()
        
    def show_login_window(self):
        """显示登录界面"""
        if not self.login_window:
            self.login_window = LoginWindow()
            self.login_window.login_success.connect(self.handle_login)
            self.login_window.register_clicked.connect(self.show_register_window)
        
        # 关闭其他窗口
        if self.register_window and self.register_window.isVisible():
            self.register_window.hide()
        if self.detection_window and self.detection_window.isVisible():
            self.detection_window.close()
        if self.user_window and self.user_window.isVisible():
            self.user_window.close()
        if self.admin_window and self.admin_window.isVisible():
            self.admin_window.close()
            
        self.login_window.show()
    
    def show_register_window(self):
        """显示注册界面"""
        if not self.register_window:
            self.register_window = RegisterWindow()
            self.register_window.register_success.connect(self.handle_register)
            self.register_window.back_to_login.connect(self.show_login_window)
        
        self.login_window.hide()
        self.register_window.show()
    
    def handle_login(self, credentials):
        """处理登录逻辑"""
        user = self.db.verify_user(credentials['username'], credentials['password'])
        
        if user:
            self.login_window.hide()
            
            # 无论管理员或普通用户，都显示检测窗口
            self.show_detection_window(user)
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self.login_window, "登录失败", "用户名或密码错误")
    
    def handle_register(self):
        """处理注册逻辑"""
        user_info = self.register_window.user_info
        
        success, message = self.db.register_user(
            user_info['username'],
            user_info['password'],
            user_info['email']
        )
        
        if success:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self.register_window, "注册成功", "账号注册成功，请登录")
            self.register_window.clear_fields()
            self.show_login_window()
        else:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self.register_window, "注册失败", message)
    
    def show_detection_window(self, user_data=None):
        """显示检测界面"""
        if self.detection_window:
            self.detection_window.close()
        
        self.detection_window = DetectionWindow(user_data)
        # 设置数据库连接
        self.detection_window.db = self.db
        
        # 连接信号
        if user_data:
            # 根据用户角色确定点击用户管理按钮后跳转到哪个界面
            if user_data['role'] == 'admin':
                self.detection_window.user_management_signal.connect(
                    self.show_admin_window
                )
            else:
                self.detection_window.user_management_signal.connect(
                    self.show_user_window
                )
        
        self.detection_window.show()
    
    def show_user_window(self, user_data):
        """显示用户管理界面"""
        if self.user_window:
            self.user_window.close()
        
        self.user_window = UserWindow(user_data, self.db)
        self.user_window.logout_signal.connect(self.show_login_window)
        self.user_window.back_to_detection_signal.connect(
            lambda: self.toggle_detection_window(True)
        )
        self.user_window.show()
        
        # 隐藏检测窗口
        if self.detection_window and self.detection_window.isVisible():
            self.detection_window.hide()
    
    def show_admin_window(self, user_data):
        """显示管理员界面"""
        if self.admin_window:
            self.admin_window.close()
        
        self.admin_window = AdminWindow(user_data, self.db)
        self.admin_window.logout_signal.connect(self.show_login_window)
        self.admin_window.back_to_detection_signal.connect(
            lambda: self.toggle_detection_window(True)
        )
        self.admin_window.show()
        
        # 隐藏检测窗口
        if self.detection_window and self.detection_window.isVisible():
            self.detection_window.hide()
    
    def toggle_detection_window(self, show=True):
        """显示或隐藏检测窗口"""
        if self.detection_window:
            if show:
                self.detection_window.show()
            else:
                self.detection_window.hide()
    
    def run(self):
        """运行应用"""
        sys.exit(self.app.exec())

def main():
    app = Application()
    app.run()

if __name__ == "__main__":
    main()