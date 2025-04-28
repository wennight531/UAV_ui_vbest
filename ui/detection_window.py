import cv2
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QComboBox, QGroupBox, QFrame, QGridLayout, QProgressDialog,
                             QMessageBox)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
import torch
from pathlib import Path
from datetime import datetime
import os
import traceback
import time
import shutil
import subprocess
import sys

# 结果导出器基类
class ResultExporter(QThread):
    progress_updated = Signal(int)
    export_finished = Signal(bool, str)  # 成功/失败, 消息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_canceled = False
        
    def cancel(self):
        self.is_canceled = True
        
    def get_timestamp(self):
        """获取格式化的时间戳"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def draw_timestamp(self, image):
        """在图像上绘制时间戳"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 在图像底部添加时间戳
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2
        text_size = cv2.getTextSize(timestamp, font, font_scale, font_thickness)[0]
        
        # 图像底部添加黑色半透明条
        h, w = image.shape[:2]
        overlay = image.copy()
        cv2.rectangle(overlay, (0, h - text_size[1] - 10), (w, h), (0, 0, 0), -1)
        # 添加透明度
        alpha = 0.7
        image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
        
        # 添加时间戳文本
        cv2.putText(
            image, 
            timestamp, 
            (10, h - 10), 
            font, 
            font_scale, 
            (255, 255, 255), 
            font_thickness, 
            cv2.LINE_AA
        )
        
        return image

# 图片导出器
class ImageExporter(ResultExporter):
    def __init__(self, image, model, output_path, parent=None):
        super().__init__(parent)
        self.image = image
        self.model = model
        self.output_path = output_path
    
    def run(self):
        try:
            # 发出进度信号 - 开始
            self.progress_updated.emit(10)
            
            # 进行检测
            with torch.no_grad():
                results = self.model(self.image)
                
            # 发出进度信号 - 检测完成
            self.progress_updated.emit(50)
            
            if self.is_canceled:
                self.export_finished.emit(False, "导出已取消")
                return
                
            # 渲染检测结果
            result_image = results.render()[0]
            
            # 添加时间戳
            result_image = self.draw_timestamp(result_image)
            
            # 发出进度信号 - 渲染完成
            self.progress_updated.emit(80)
            
            if self.is_canceled:
                self.export_finished.emit(False, "导出已取消")
                return
                
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
            
            # 保存图片
            cv2.imwrite(self.output_path, result_image)
            
            # 发出进度信号 - 完成
            self.progress_updated.emit(100)
            
            # 发出完成信号
            self.export_finished.emit(True, f"检测结果已成功导出到: {self.output_path}")
            
        except Exception as e:
            error_msg = f"导出错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.export_finished.emit(False, f"导出失败: {str(e)}")

# 视频检测结果导出器
class VideoExporter(ResultExporter):
    def __init__(self, video_path, model, output_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.model = model
        self.output_path = output_path
        
    def run(self):
        try:
            # 打开视频
            video = cv2.VideoCapture(self.video_path)
            if not video.isOpened():
                self.export_finished.emit(False, f"无法打开视频: {self.video_path}")
                return
            
            # 获取视频属性
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)
            total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 输出调试信息
            print(f"视频属性: 宽={width}, 高={height}, FPS={fps}, 总帧数={total_frames}")
            
            # 确保输出目录存在
            output_dir = os.path.dirname(os.path.abspath(self.output_path))
            os.makedirs(output_dir, exist_ok=True)
            
            # 确保文件扩展名与编解码器匹配
            base_path, ext = os.path.splitext(self.output_path)
            temp_output = f"{base_path}_temp.avi"  # 使用.avi而不是.mp4，更好地兼容多种编解码器
            
            # 尝试不同的编解码器
            writer = None
            codec_tried = []
            
            # 获取当前系统支持的编解码器，使用与测试相同的参数
            test_codecs = ['mp4v', 'XVID', 'MJPG']  # 移除avc1，简化测试
            supported_codecs = []
            for codec in test_codecs:
                try:
                    test_size = (width, height)  # 使用实际尺寸而不是固定的测试尺寸
                    test_file = os.path.join(output_dir, f"test_{codec}.avi")
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    test_writer = cv2.VideoWriter(test_file, fourcc, fps, test_size)
                    is_opened = test_writer.isOpened()
                    test_writer.release()
                    if os.path.exists(test_file):
                        os.remove(test_file)
                    
                    if is_opened:
                        supported_codecs.append(codec)
                        print(f"系统支持编解码器: {codec}")
                    else:
                        print(f"系统不支持编解码器: {codec}")
                except Exception as e:
                    print(f"测试编解码器 {codec} 时出错: {str(e)}")
            
            print(f"系统支持的编解码器: {supported_codecs}")
            
            # 如果没有找到支持的编解码器，则返回错误
            if not supported_codecs:
                self.export_finished.emit(False, "系统不支持任何视频编解码器，请尝试使用图像序列导出。")
                video.release()
                return
            
            # 选择最佳编解码器 - 优先使用XVID，因为它通常最兼容
            if 'XVID' in supported_codecs:
                best_codec = 'XVID'
            elif 'MJPG' in supported_codecs:
                best_codec = 'MJPG'
            else:
                best_codec = supported_codecs[0]
                
            # 尝试创建视频
            try:
                print(f"使用编解码器 {best_codec} 创建视频: {temp_output}, 尺寸: {width}x{height}, FPS: {fps}")
                fourcc = cv2.VideoWriter_fourcc(*best_codec)
                writer = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
                
                # 检查writer是否成功初始化
                if not writer.isOpened():
                    self.export_finished.emit(False, f"无法初始化视频编码器。请尝试使用图像序列导出。")
                    video.release()
                    return
                    
                print(f"成功使用编解码器 {best_codec} 创建视频文件")
            except Exception as e:
                print(f"使用编解码器 {best_codec} 时出错: {str(e)}")
                self.export_finished.emit(False, f"创建视频文件时出错: {str(e)}。请尝试使用图像序列导出。")
                video.release()
                return
            
            # 进度信息
            self.progress_updated.emit(0)
            frame_count = 0
            
            # 处理每一帧
            while not self.is_canceled:
                ret, frame = video.read()
                if not ret:
                    break
                
                # 更新进度 (处理前)
                frame_count += 1
                progress = int((frame_count / total_frames) * 50)
                self.progress_updated.emit(progress)
                
                # 进行检测
                with torch.no_grad():
                    results = self.model(frame)
                
                # 渲染检测结果
                result_frame = results.render()[0]
                
                # 确保帧尺寸匹配
                if result_frame.shape[0] != height or result_frame.shape[1] != width:
                    result_frame = cv2.resize(result_frame, (width, height))
                
                # 添加时间戳
                result_frame = self.draw_timestamp(result_frame)
                
                # 写入帧
                writer.write(result_frame)
                
                # 每处理30帧检查一次是否取消
                if frame_count % 30 == 0:
                    # 更新进度 (处理后)
                    progress = 50 + int((frame_count / total_frames) * 50)
                    self.progress_updated.emit(progress)
                    
                    if self.is_canceled:
                        break
            
            # 释放资源
            video.release()
            writer.release()
            
            # 如果已取消，删除临时文件
            if self.is_canceled:
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                self.export_finished.emit(False, "导出已取消")
            else:
                # 完成导出
                self.progress_updated.emit(100)
                
                # 检查输出文件是否有效
                if os.path.exists(temp_output) and os.path.getsize(temp_output) > 1024:  # 至少要有1KB
                    # 将.avi文件转换为最终格式（如果需要）
                    final_output = self.output_path
                    try:
                        # 简单重命名文件
                        if os.path.exists(final_output):
                            os.remove(final_output)
                        os.rename(temp_output, final_output)
                        
                        print(f"视频成功导出到: {final_output}, 大小: {os.path.getsize(final_output)}")
                        self.export_finished.emit(True, f"视频已成功导出到: {final_output}")
                    except Exception as e:
                        # 如果重命名失败，至少保留临时文件
                        print(f"重命名文件时出错: {str(e)}")
                        self.export_finished.emit(True, f"视频已成功导出到临时文件: {temp_output}")
                else:
                    print(f"导出失败：视频文件无效 - 存在: {os.path.exists(temp_output)}, 大小: {os.path.getsize(temp_output) if os.path.exists(temp_output) else 0}")
                    self.export_finished.emit(False, "导出失败：创建的视频文件无效。请尝试使用图像序列导出。")
                
        except Exception as e:
            error_msg = f"导出错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.export_finished.emit(False, f"导出失败: {str(e)}。请尝试使用图像序列导出。")
            
            
class FrameSequenceExporter(ResultExporter):
    """备选方案：导出为帧序列"""
    def __init__(self, video_path, model, output_dir, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.model = model
        self.output_dir = output_dir
        
    def run(self):
        try:
            # 打开视频
            video = cv2.VideoCapture(self.video_path)
            if not video.isOpened():
                self.export_finished.emit(False, f"无法打开视频: {self.video_path}")
                return
            
            # 获取视频属性
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)
            total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 创建输出目录
            frames_dir = os.path.join(self.output_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)
            
            # 保存视频参数
            params_file = os.path.join(self.output_dir, "video_params.txt")
            with open(params_file, 'w') as f:
                f.write(f"fps={fps}\n")
                f.write(f"width={width}\n")
                f.write(f"height={height}\n")
                f.write(f"total_frames={total_frames}\n")
                f.write(f"export_time={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # 创建批处理文件
            self.create_conversion_scripts(frames_dir, fps)
            
            # 进度信息
            self.progress_updated.emit(0)
            frame_count = 0
            
            # 处理每一帧
            while not self.is_canceled:
                ret, frame = video.read()
                if not ret:
                    break
                
                # 进行检测
                with torch.no_grad():
                    results = self.model(frame)
                
                # 渲染检测结果
                result_frame = results.render()[0]
                
                # 确保帧尺寸匹配
                if result_frame.shape[0] != height or result_frame.shape[1] != width:
                    result_frame = cv2.resize(result_frame, (width, height))
                
                # 添加时间戳
                result_frame = self.draw_timestamp(result_frame)
                
                # 保存帧为图像
                frame_path = os.path.join(frames_dir, f"frame_{frame_count:06d}.jpg")
                cv2.imwrite(frame_path, result_frame)
                
                # 更新进度
                frame_count += 1
                progress = int((frame_count / total_frames) * 100)
                self.progress_updated.emit(progress)
                
                # 每处理30帧检查一次是否取消
                if frame_count % 30 == 0 and self.is_canceled:
                    break
            
            # 释放资源
            video.release()
            
            # 如果已取消，删除目录
            if self.is_canceled:
                self.export_finished.emit(False, "导出已取消")
            else:
                # 创建完成标记文件
                with open(os.path.join(self.output_dir, "export_complete.txt"), 'w') as f:
                    f.write(f"Total frames: {frame_count}\n")
                    f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                message = (
                    f"已成功将检测结果导出到: {self.output_dir}\n\n"
                    f"总共导出 {frame_count} 帧。\n\n"
                    f"在输出目录中提供了便捷脚本，可以帮助您将图像序列转换为视频。"
                )
                self.export_finished.emit(True, message)
                
        except Exception as e:
            error_msg = f"导出错误: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            self.export_finished.emit(False, f"导出失败: {str(e)}")
            
    def create_conversion_scripts(self, frames_dir, fps):
        """创建转换脚本，帮助用户将图像序列转换为视频"""
        # 为Windows创建批处理文件
        batch_file = os.path.join(self.output_dir, "create_video.bat")
        with open(batch_file, 'w') as f:
            f.write("@echo off\n")
            f.write("echo 正在将图像序列转换为视频...\n")
            f.write(f'ffmpeg -y -framerate {fps} -i "{frames_dir}\\frame_%06d.jpg" -c:v libx264 -pix_fmt yuv420p -crf 23 "{self.output_dir}\\output_video.mp4"\n')
            f.write("if %ERRORLEVEL% EQU 0 (\n")
            f.write("  echo 视频已成功创建: %CD%\\output_video.mp4\n")
            f.write(") else (\n")
            f.write("  echo 创建视频失败，请确保已安装FFmpeg并添加到系统PATH\n")
            f.write("  echo 您可以从https://ffmpeg.org/download.html下载FFmpeg\n")
            f.write(")\n")
            f.write("pause\n")
        
        # 为Linux/Mac创建shell脚本
        shell_file = os.path.join(self.output_dir, "create_video.sh")
        with open(shell_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write('echo "正在将图像序列转换为视频..."\n')
            f.write(f'ffmpeg -y -framerate {fps} -i "{frames_dir}/frame_%06d.jpg" -c:v libx264 -pix_fmt yuv420p -crf 23 "{self.output_dir}/output_video.mp4"\n')
            f.write('if [ $? -eq 0 ]; then\n')
            f.write('  echo "视频已成功创建: $(pwd)/output_video.mp4"\n')
            f.write('else\n')
            f.write('  echo "创建视频失败，请确保已安装FFmpeg"\n')
            f.write('  echo "您可以访问https://ffmpeg.org/download.html获取安装指南"\n')
            f.write('fi\n')

class DetectionWindow(QMainWindow):
    user_management_signal = Signal(dict)  # 用户管理信号，传递用户信息
    
    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data  # 存储用户信息
        self.setWindowTitle("无人机影像识别系统")
        self.setGeometry(100, 100, 1200, 675)
        self.db = None  # 数据库连接
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QGroupBox {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QComboBox {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-height: 30px;
            }
            QComboBox:hover {
                border: 1px solid #999999;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QLabel {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
        """)
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_widget.setLayout(main_layout)
        
        # 左侧控制面板
        control_panel = QFrame()
        control_panel.setObjectName("controlPanel")
        control_panel.setStyleSheet("""
            QFrame#controlPanel {
                background-color: white;
                border-radius: 8px;
                border: 2px solid #e0e0e0;
            }
        """)
        control_layout = QVBoxLayout()
        control_layout.setSpacing(15)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(250)
        
        # 标题标签
        title_label = QLabel("无人机影像识别系统")
        title_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # 用户信息显示
        if self.user_data:
            user_info = QLabel(f"当前用户: {self.user_data['username']}")
            user_info.setStyleSheet("""
                QLabel {
                    color: #333333;
                    padding: 5px;
                    background-color: #f9f9f9;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            user_info.setAlignment(Qt.AlignCenter)
        else:
            user_info = QLabel("游客模式")
            user_info.setStyleSheet("""
                QLabel {
                    color: #777777;
                    padding: 5px;
                    background-color: #f9f9f9;
                    border-radius: 4px;
                }
            """)
            user_info.setAlignment(Qt.AlignCenter)
        
        # 模型选择组
        model_group = QGroupBox("模型选择")
        model_layout = QVBoxLayout()
        model_group.setLayout(model_layout)
        
        # 模型选择下拉框
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(35)
        self.load_models()
        model_layout.addWidget(self.model_combo)
        
        # 添加按钮
        self.load_image_btn = QPushButton("📷 加载图片")
        self.load_video_btn = QPushButton("🎥 加载视频")
        self.start_detect_btn = QPushButton("🔍 开始检测")
        self.pause_btn = QPushButton("⏸️ 暂停检测")
        self.export_btn = QPushButton("💾 导出结果")
        
        # 用户管理按钮
        if self.user_data:
            if self.user_data['role'] == 'admin':
                self.user_management_btn = QPushButton("👤 管理员控制台")
            else:
                self.user_management_btn = QPushButton("👤 个人中心")
            self.user_management_btn.clicked.connect(self.open_user_management)
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 40px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        self.load_image_btn.setStyleSheet(button_style)
        self.load_video_btn.setStyleSheet(button_style)
        self.start_detect_btn.setStyleSheet(button_style)
        self.pause_btn.setStyleSheet(button_style)
        self.export_btn.setStyleSheet(button_style)
        self.user_management_btn.setStyleSheet(button_style)
        
        # 添加部件到控制面板
        control_layout.addWidget(title_label)
        control_layout.addWidget(user_info)
        control_layout.addWidget(model_group)
        control_layout.addWidget(self.load_image_btn)
        control_layout.addWidget(self.load_video_btn)
        control_layout.addWidget(self.start_detect_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.export_btn)
        
        # 如果有用户数据，则添加用户管理按钮
        if self.user_data:
            control_layout.addWidget(self.user_management_btn)
            
        control_layout.addStretch()
        
        # 右侧显示区域
        display_panel = QFrame()
        display_panel.setObjectName("displayPanel")
        display_panel.setStyleSheet("""
            QFrame#displayPanel {
                background-color: white;
                border-radius: 8px;
                border: 2px solid #e0e0e0;
            }
        """)
        display_layout = QGridLayout()
        display_layout.setSpacing(10)
        display_layout.setContentsMargins(10, 10, 10, 10)
        display_panel.setLayout(display_layout)
        
        # 原始图像显示区域
        self.original_label = QLabel("原始图像")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setMinimumSize(600, 400)
        self.original_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # 检测结果显示区域
        self.result_label = QLabel("检测结果")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(600, 400)
        self.result_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        # 添加显示区域到布局
        display_layout.addWidget(self.original_label, 0, 0)
        display_layout.addWidget(self.result_label, 0, 1)
        
        # 添加部件到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(display_panel)
        
        # 连接信号和槽
        self.load_image_btn.clicked.connect(self.load_image)
        self.load_video_btn.clicked.connect(self.load_video)
        self.start_detect_btn.clicked.connect(self.start_detection)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.export_btn.clicked.connect(self.export_results)
        
        # 初始化变量
        self.current_image = None
        self.current_video = None
        self.model = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_paused = False
        self.is_detecting = False
        
        # 添加状态变量
        self.video_path = None  # 存储原始视频路径
        self.video_finished = False  # 标记视频是否播放完成
        self.exporting_video = False  # 标记是否正在导出视频
        
    def load_models(self):
        """加载models目录下的所有模型文件"""
        models_dir = Path("models")
        if not models_dir.exists():
            models_dir.mkdir()
            
        # 清空现有选项
        self.model_combo.clear()
        
        # 添加所有.pt文件到下拉框
        model_files = list(models_dir.glob("*.pt"))
        if model_files:
            for model_file in model_files:
                self.model_combo.addItem(model_file.name, str(model_file))
        else:
            self.model_combo.addItem("未找到模型文件", "")
            
    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_name:
            # 清除视频相关状态
            if self.current_video is not None:
                self.current_video.release()
                self.current_video = None
                self.timer.stop()

            # 加载图片
            self.current_image = cv2.imread(file_name)
            # 重置结果显示
            self.result_label.setText("检测结果")
            self.result_label.setAlignment(Qt.AlignCenter)
            # 显示图片
            self.display_image(self.current_image, self.original_label)
            # 重置检测状态
            self.is_detecting = False
            
    def load_video(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Video Files (*.mp4 *.avi)")
        if file_name:
            # 清除图片相关状态
            self.current_image = None
            
            # 如果之前有视频在运行，释放资源
            if self.current_video is not None:
                self.current_video.release()
            
            # 存储视频路径
            self.video_path = file_name
            
            # 加载新视频
            self.current_video = cv2.VideoCapture(file_name)
            self.timer.start(30)  # 30ms = ~33fps
            self.is_paused = False
            self.video_finished = False
            self.pause_btn.setEnabled(True)
            
            # 重置检测状态
            self.is_detecting = False
            
            # 重置结果显示
            self.result_label.setText("检测结果")
            self.result_label.setAlignment(Qt.AlignCenter)
            
            # 更新UI状态
            self.update_ui_state()
    
    def display_image(self, image, label):
        if image is not None:
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            label.setPixmap(QPixmap.fromImage(q_image))
            
    def update_frame(self):
        if self.current_video is not None and not self.is_paused:
            ret, frame = self.current_video.read()
            if ret:
                # 成功读取帧，重置视频完成标记
                self.video_finished = False
                
                # 显示原始帧
                self.display_image(frame, self.original_label)
                
                # 如果正在检测，显示检测结果
                if self.is_detecting:
                    results = self.model(frame)
                    self.display_image(results.render()[0], self.result_label)
            else:
                # 视频播放结束
                self.video_finished = True
                
                # 如果不是正在导出视频，重置视频到开始位置
                if not self.exporting_video:
                    self.reset_video()
                    
                    # 可选：如果用户想要自动循环播放
                    # self.current_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def reset_video(self):
        """重置视频到开始位置，但不释放资源"""
        if self.current_video is not None:
            # 暂停播放
            self.is_paused = True
            self.pause_btn.setText("▶️ 继续检测")
            
            # 显示提示信息（可选）
            self.result_label.setText("视频播放完毕，点击开始检测可重新检测")
            self.result_label.setAlignment(Qt.AlignCenter)
            
            # 更新UI状态
            self.update_ui_state()
    
    def update_ui_state(self):
        """更新UI按钮状态"""
        # 根据当前状态设置按钮启用/禁用
        has_media = self.current_image is not None or self.current_video is not None
        self.start_detect_btn.setEnabled(has_media)
        self.pause_btn.setEnabled(self.current_video is not None)
        self.export_btn.setEnabled(self.is_detecting)
    
    def start_detection(self):
        # 获取选中的模型路径
        model_path = self.model_combo.currentData()
        if not model_path:
            QMessageBox.warning(self, "警告", "请先选择有效的模型")
            return
            
        if self.model is None or self.model_path != model_path:
            # 加载YOLOv5模型
            try:
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
                self.model_path = model_path
            except Exception as e:
                QMessageBox.critical(self, "错误", f"模型加载失败: {str(e)}")
                return
            
        # 正确检查是否有媒体加载
        if self.current_image is None and self.current_video is None:
            QMessageBox.warning(self, "警告", "请先加载图片或视频")
            return
        
        # 设置检测状态
        self.is_detecting = True
        
        if self.current_image is not None:
            # 对图片进行检测
            results = self.model(self.current_image)
            # 显示检测结果
            self.display_image(results.render()[0], self.result_label)
        elif self.current_video is not None:
            # 如果视频已经播放完毕，重置到开始位置
            if self.video_finished:
                self.current_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.video_finished = False
            
            # 如果视频处于暂停状态，恢复播放
            if self.is_paused:
                self.is_paused = False
                self.pause_btn.setText("⏸️ 暂停检测")
        
        # 更新UI状态
        self.update_ui_state()
    
    def toggle_pause(self):
        if self.current_video is not None:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_btn.setText("▶️ 继续检测")
            else:
                self.pause_btn.setText("⏸️ 暂停检测")
                # 如果视频已经播放完毕但用户点击继续播放，重置到开始位置
                if self.video_finished:
                    self.current_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.video_finished = False
    
    def export_results(self):
        """导出检测结果"""
        if not self.is_detecting:
            QMessageBox.warning(self, "警告", "请先开始检测后再导出结果")
            return
            
        # 创建保存目录
        results_dir = Path("results")
        if not results_dir.exists():
            results_dir.mkdir()
            
        # 获取当前时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        if self.current_image is not None and self.current_video is None:
            # 导出图片
            default_name = f"detection_result_{timestamp}.jpg"
            file_name, _ = QFileDialog.getSaveFileName(
                self, 
                "保存检测结果图片", 
                str(results_dir / default_name),
                "Image Files (*.jpg *.jpeg *.png)"
            )
            
            if file_name:
                # 禁用导出按钮，防止重复操作
                self.export_btn.setEnabled(False)
                
                # 创建进度对话框
                self.progress_dialog = QProgressDialog("正在生成检测结果...", "取消", 0, 100, self)
                self.progress_dialog.setWindowTitle("导出进度")
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.setMinimumDuration(500)  # 只有操作超过500ms才显示
                self.progress_dialog.setValue(0)
                
                # 创建导出线程
                self.exporter = ImageExporter(self.current_image, self.model, file_name, self)
                
                # 连接信号
                self.exporter.progress_updated.connect(self.progress_dialog.setValue)
                self.exporter.export_finished.connect(self.on_export_finished)
                self.progress_dialog.canceled.connect(self.exporter.cancel)
                
                # 启动线程
                self.exporter.start()
                
        elif self.current_video is not None and self.video_path is not None:
            # 提供两种导出选项 - 使用正确的 QMessageBox 语法
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("选择导出方式")
            msg_box.setText("请选择导出方式：")
            msg_box.setInformativeText("1. 导出完整视频 - 直接创建视频文件\n2. 导出图像序列 - 创建一系列图像和转换脚本")
            
            # 添加按钮
            video_btn = msg_box.addButton("导出完整视频", QMessageBox.AcceptRole)
            frames_btn = msg_box.addButton("导出图像序列", QMessageBox.ActionRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            msg_box.exec_()
            
            # 判断用户选择
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == cancel_btn:
                return
                
            if clicked_button == video_btn:
                # 导出完整检测视频
                default_name = f"detection_result_{timestamp}.mp4"
                file_name, _ = QFileDialog.getSaveFileName(
                    self,
                    "保存检测结果视频",
                    str(results_dir / default_name),
                    "Video Files (*.mp4)"
                )
                
                if file_name:
                    # 禁用导出按钮，防止重复操作
                    self.export_btn.setEnabled(False)
                    
                    # 标记正在导出视频
                    self.exporting_video = True
                    
                    # 暂停视频播放
                    was_paused = self.is_paused
                    self.is_paused = True
                    
                    # 创建进度对话框
                    self.progress_dialog = QProgressDialog("正在导出检测视频...", "取消", 0, 100, self)
                    self.progress_dialog.setWindowTitle("导出进度")
                    self.progress_dialog.setWindowModality(Qt.WindowModal)
                    self.progress_dialog.setMinimumDuration(0)
                    self.progress_dialog.setValue(0)
                    self.progress_dialog.show()
                    
                    # 创建导出线程
                    self.exporter = VideoExporter(self.video_path, self.model, file_name, self)
                    
                    # 连接信号
                    self.exporter.progress_updated.connect(self.progress_dialog.setValue)
                    self.exporter.export_finished.connect(lambda success, msg: self.on_video_export_finished(success, msg, was_paused))
                    self.progress_dialog.canceled.connect(self.exporter.cancel)
                    
                    # 启动线程
                    self.exporter.start()
            elif clicked_button == frames_btn:
                # 选择导出目录
                folder_dialog = QFileDialog(self)
                folder_dialog.setFileMode(QFileDialog.Directory)
                folder_dialog.setOption(QFileDialog.ShowDirsOnly, True)
                folder_dialog.setWindowTitle("选择导出目录")
                folder_dialog.setDirectory(str(results_dir))
                
                if folder_dialog.exec_():
                    selected_dir = folder_dialog.selectedFiles()[0]
                    output_dir = os.path.join(selected_dir, f"detection_result_{timestamp}")
                    
                    # 禁用导出按钮，防止重复操作
                    self.export_btn.setEnabled(False)
                    
                    # 标记正在导出视频
                    self.exporting_video = True
                    
                    # 暂停视频播放
                    was_paused = self.is_paused
                    self.is_paused = True
                    
                    # 创建进度对话框
                    self.progress_dialog = QProgressDialog("正在导出检测序列...", "取消", 0, 100, self)
                    self.progress_dialog.setWindowTitle("导出进度")
                    self.progress_dialog.setWindowModality(Qt.WindowModal)
                    self.progress_dialog.setMinimumDuration(0)
                    self.progress_dialog.setValue(0)
                    self.progress_dialog.show()
                    
                    # 创建导出线程
                    self.exporter = FrameSequenceExporter(self.video_path, self.model, output_dir, self)
                    
                    # 连接信号
                    self.exporter.progress_updated.connect(self.progress_dialog.setValue)
                    self.exporter.export_finished.connect(lambda success, msg: self.on_video_export_finished(success, msg, was_paused))
                    self.progress_dialog.canceled.connect(self.exporter.cancel)
                    
                    # 启动线程
                    self.exporter.start()
                    
        else:
            QMessageBox.warning(self, "警告", "没有检测内容可导出")
    
    def on_export_finished(self, success, message):
        """处理导出完成事件"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # 重新启用导出按钮
        self.export_btn.setEnabled(True)
        
        # 显示结果信息
        if success:
            QMessageBox.information(self, "导出成功", message)
            
            # 如果用户已登录，保存检测记录到数据库
            if self.user_data and self.db:
                file_path = str(self.exporter.output_path)
                self.db.add_detection_record(
                    self.user_data['id'], 
                    'image', 
                    file_path, 
                    'completed'
                )
        else:
            QMessageBox.critical(self, "导出失败", message)
    
    def on_video_export_finished(self, success, message, was_paused):
        """处理视频导出完成事件"""
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        # 重置导出标记
        self.exporting_video = False
        
        # 重新启用导出按钮
        self.export_btn.setEnabled(True)
        
        # 恢复视频播放状态
        self.is_paused = was_paused
        if self.is_paused:
            self.pause_btn.setText("▶️ 继续检测")
        else:
            self.pause_btn.setText("⏸️ 暂停检测")
        
        # 显示结果信息
        if success:
            QMessageBox.information(self, "导出成功", message)
            
            # 如果用户已登录，保存检测记录到数据库
            if self.user_data and self.db:
                # 根据导出器类型确定文件路径和类型
                if isinstance(self.exporter, VideoExporter):
                    file_path = str(self.exporter.output_path)
                    detection_type = 'video'
                elif isinstance(self.exporter, FrameSequenceExporter):
                    file_path = str(self.exporter.output_dir)
                    detection_type = 'frames'
                else:
                    # 未知类型，使用默认值
                    file_path = "未知路径"
                    detection_type = '未知类型'
                
                self.db.add_detection_record(
                    self.user_data['id'], 
                    detection_type, 
                    file_path, 
                    'completed'
                )
        else:
            QMessageBox.critical(self, "导出失败", message)
            
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 取消正在进行的导出
        if hasattr(self, 'exporter') and self.exporter.isRunning():
            self.exporter.cancel()
            self.exporter.wait()
        
        # 释放视频资源
        if self.current_video is not None:
            self.current_video.release()
            
        event.accept()

    def open_user_management(self):
        """打开用户管理界面"""
        if not self.user_data:
            QMessageBox.warning(self, "错误", "请先登录后再使用此功能")
            return
        
        # 发送信号，通知主应用打开用户管理界面
        self.user_management_signal.emit(self.user_data) 