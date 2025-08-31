import time
from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen

import random
import json
import os

class SpeechBubble(QDialog):
    """自定义对话框气泡组件，支持打字效果"""
    def __init__(self, parent=None, text="", timeout=3000, typing_speed=100):
        super().__init__(parent)
        
        # 设置无边框、半透明背景
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 设置内容
        self.full_text = text  # 完整文本
        self.displayed_text = ""  # 当前显示的文本
        self.timeout = timeout
        self.typing_speed = typing_speed  # 打字速度（毫秒/字符）
        self.current_char_index = 0  # 当前字符索引
        self.typing_complete = False  # 打字是否完成
        
        # 布局和样式
        self.init_ui()
        
        # 自动关闭定时器
        if timeout > 0:
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.close)
            
        # 打字效果定时器
        if text and typing_speed > 0:
            self.typing_timer = QTimer(self)
            self.typing_timer.setInterval(typing_speed)
            self.typing_timer.timeout.connect(self._update_typing)
            self.typing_timer.start()
        else:
            # 如果没有文本或者不需要打字效果，直接显示完整文本
            self.displayed_text = text
            self.label.setText(text)
            self.typing_complete = True
            # 启动自动关闭定时器
            if timeout > 0:
                self.timer.start(timeout)
    
    def init_ui(self):
        # 创建标签显示文本
        self.label = QLabel(self.displayed_text)
        self.label.setFont(QFont("SimHei", 10))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        
        # 设置布局
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.setContentsMargins(20, 15, 20, 15)
        self.setLayout(layout)
        
        # 先使用完整文本估算大小，确保气泡足够大
        temp_label = QLabel(self.full_text)
        temp_label.setFont(QFont("SimHei", 10))
        temp_label.setWordWrap(True)
        temp_label.adjustSize()
        
        # 设置气泡大小
        width = temp_label.width() + 40
        height = temp_label.height() + 30
        self.resize(width, height)
    
    def _update_typing(self):
        """更新打字效果，逐字显示文本"""
        if self.current_char_index < len(self.full_text):
            # 添加下一个字符
            self.displayed_text += self.full_text[self.current_char_index]
            self.current_char_index += 1
            self.label.setText(self.displayed_text)
            
            # 如果是最后一个字符，完成打字
            if self.current_char_index >= len(self.full_text):
                self.typing_complete = True
                self.typing_timer.stop()
                # 启动自动关闭定时器
                if hasattr(self, 'timer') and self.timeout > 0:
                    self.timer.start(self.timeout)
        
    def paintEvent(self, event):
        # 自定义绘制气泡形状
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制气泡背景
        bubble_rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
        painter.drawRoundedRect(bubble_rect, 10, 10)
        
        # 绘制小三角形指向桌宠
        if self.parent():
            parent_center = self.parent().geometry().center()
            bubble_bottom = self.geometry().bottom()
            triangle_points = [
                QPoint(parent_center.x() - 10, bubble_bottom),
                QPoint(parent_center.x(), bubble_bottom + 10),
                QPoint(parent_center.x() + 10, bubble_bottom)
            ]
            painter.drawPolygon(triangle_points)

class DialogManager:
    """对话框管理器，负责处理对话框的显示和触发条件"""
    def __init__(self, pet):
        self.pet = pet
        
        # 默认对话框内容库（作为备选）
        self.default_dialogues = {
            "greeting": ["你好呀！", "嗨，很高兴见到你！", "今天过得怎么样？"],
            "bored": ["有点无聊呢...", "来陪我玩吧！", "好想出去走走~"],
            "happy": ["真开心！", "今天心情真好！", "谢谢陪我玩！"],
            "tired": ["好累呀...", "我需要休息一下。", "能让我小睡一会吗？"]
        }
        # 从配置文件加载对话文本
        self.dialogues = {}
        self.dialogues_move = {}
        self._load_dialogues_from_config()
        # 自动触发相关设置
        self.auto_trigger_enabled = True
        self.min_interval = 30  # 最小间隔（秒）
        self.max_interval = 120  # 最大间隔（秒）
        self.last_trigger_time = 0
        self.time_to_next_trigger = random.uniform(self.min_interval, self.max_interval)
        
        # 状态追踪
        self.state_tracker = {
            "idle_time": 0,
            "interacted": False,
            "moved_recently": False
        }
        
        # 启动自动触发检查定时器
        self.check_timer = QTimer(self.pet)
        self.check_timer.setInterval(1000)  # 每秒检查一次
        self.check_timer.timeout.connect(self._check_auto_trigger_conditions)
        self.check_timer.start()
        
    def _load_dialogues_from_config(self):
        """从配置文件加载对话文本"""
        try:
            # 获取配置文件路径
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dialogs.json')
            
            # 检查配置文件是否存在
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 加载常规对话
                if 'dialogues' in config:
                    self.dialogues = config['dialogues']
                else:
                    # 如果配置中没有常规对话，使用默认值
                    self.dialogues = self.default_dialogues.copy()
                    
                # 加载动作相关对话
                if 'dialogues_move' in config:
                    self.dialogues_move = config['dialogues_move']
                else:
                    # 如果配置中没有动作对话，使用默认值
                    self.dialogues_move = self.default_dialogues.copy()
                    
            else:
                # 配置文件不存在，使用默认对话
                self.dialogues = self.default_dialogues.copy()
                self.dialogues_move = self.default_dialogues.copy()
                
                # 创建默认配置文件
                default_config = {
                    'dialogues': self.default_dialogues,
                    'dialogues_move': self.default_dialogues_move
                }
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            # 加载失败，使用默认对话
            print(f"加载对话配置失败: {e}")
            self.dialogues = self.default_dialogues.copy()
            self.dialogues_move = self.default_dialogues.copy()
    
    def show_dialog(self, text=None, dialog_type=None, timeout=3000, typing_speed=30):
        """显示一个对话框"""
        # 如果没有指定文本，根据类型选择一个
        if text is None:
            if dialog_type and dialog_type in self.dialogues:
                text = random.choice(self.dialogues[dialog_type])
            else:
                # 随机选择一个类型和文本
                dialog_type = random.choice(list(self.dialogues.keys()))
                text = random.choice(self.dialogues[dialog_type])
        
        # 创建并显示对话框
        bubble = SpeechBubble(self.pet, text, timeout, typing_speed)
        
        # 计算对话框位置（在桌宠上方居中）
        pet_rect = self.pet.geometry()
        bubble_rect = bubble.geometry()
        x = pet_rect.center().x() - bubble_rect.width() // 2
        y = pet_rect.top() - bubble_rect.height() - 10
        bubble.move(x, y)
        
        bubble.show()
        
        # 更新最后触发时间
        self.last_trigger_time = time.time()
        self.time_to_next_trigger = random.uniform(self.min_interval, self.max_interval)
        
        return bubble
    
    def show_random_dialog(self):
        """显示一个随机对话框"""
        self.show_dialog()
    
    def _check_auto_trigger_conditions(self):
        """检查是否满足自动触发对话框的条件"""
        if not self.auto_trigger_enabled:
            return
        
        # 检查时间间隔
        current_time = time.time()
        if current_time - self.last_trigger_time < self.time_to_next_trigger:
            return
        
        # 这里可以添加更多条件判断，例如：
        # 1. 桌宠是否处于空闲状态
        # 2. 用户是否很久没有交互
        # 3. 特定的物理状态（如静止、跳跃后等）
        
        # 示例条件：桌宠在地面上并且静止不动
        if (self.pet.physics_system.on_ground and 
            abs(self.pet.physics_system.vx) < 1 and 
            abs(self.pet.physics_system.vy) < 1):
            
            # 增加空闲时间计数
            self.state_tracker["idle_time"] += 1
            
            # 如果空闲时间超过一定值，显示无聊相关的对话框
            if self.state_tracker["idle_time"] > 60:  # 60秒
                self.show_dialog(dialog_type="bored")
                self.state_tracker["idle_time"] = 0
        else:
            # 桌宠在移动，重置空闲时间
            self.state_tracker["idle_time"] = 0
    
    def register_interaction(self):
        """注册用户交互事件"""
        self.state_tracker["interacted"] = True
        self.state_tracker["idle_time"] = 0
        
        # 有交互后可以显示开心的对话框
        if random.random() < 0.1:  # 10%的概率
            self.show_dialog(dialog_type="happy")
    
    def add_dialogue(self, dialog_type, texts):
        """添加新的对话框类型和内容"""
        if dialog_type not in self.dialogues:
            self.dialogues[dialog_type] = []
        self.dialogues[dialog_type].extend(texts)
    
    def set_auto_trigger_enabled(self, enabled):
        """启用或禁用自动触发"""
        self.auto_trigger_enabled = enabled