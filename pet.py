import sys
import random
import json
import os
import time
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer

# 导入模块化组件
from physics import PhysicsSystem
from speed_control import SpeedController
from renderer import Renderer
from behavior import BehaviorController
from dialog import DialogManager
from util import IdleTimeTracker

class DesktopPet(QWidget):
    def __init__(self, asset_path=None, max_width=None, max_height=None,
                 initial_random=True, initial_on_ground=False):
        super().__init__()
        
        # 无边框、置顶、不出现在任务栏、背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | 
                            Qt.WindowStaysOnTopHint | 
                            Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 初始化组件
        self.renderer = Renderer(self, asset_path, max_width, max_height)
        self.physics_system = PhysicsSystem(self)
        self.speed_controller = SpeedController(self.physics_system)
        self.behavior_controller = BehaviorController(self)
        self.dialog_manager = DialogManager(self)
        # 缩放参数
        self._scale_factor = 1.0
        
        # 加载保存的设置
        self._load_settings()
        
        # 刹车状态计时器
        self._shache_timer = QTimer(self)
        self._shache_timer.setSingleShot(True)
        self._shache_timer.timeout.connect(lambda: self.renderer._switch_to_state_image("default"))
        
        # 空闲时间跟踪器，用于图片切换
        self.idle_tracker = IdleTimeTracker()
        self.idle_tracker.set_threshold(40)  # 设置40秒的空闲阈值
        self.is_currently_sleeping = False  # 跟踪当前是否处于睡眠状态
        
        # 左键点击计数器，用于2次点击切换到lift状态
        self.left_click_count = 0
        self.last_click_time = 0  # 记录上次点击时间，用于判断点击间隔
        self.is_in_lift_state = False  # 跟踪当前是否处于被拎起状态
        
        # 总点击次数计数器，用于计算所有左键点击次数
        self.total_click_count = 0

        # 定时器 - 物理系统更新
        self._walk_timer = QTimer(self)
        self._walk_timer.setInterval(16)  # ~60 FPS
        self._walk_timer.timeout.connect(self._on_walk_tick)
        
        # 初始位置
        if initial_random:
            self._place_random_in_available_area(on_ground=initial_on_ground)
        else:
            self._stick_to_ground()
            
        # 应用加载的缩放比例
        if self._scale_factor != 1.0:
            self.renderer.apply_scale(self._scale_factor)
            
        # 启动物理系统
        self._walk_timer.start()
    
    def _get_config_path(self):
        """获取配置文件路径"""
        # 在用户目录下创建配置文件夹
        config_dir = os.path.join(os.path.expanduser("~"), ".desktopet")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "settings.json")
    
    def _load_settings(self):
        """加载保存的设置"""
        try:
            config_path = self._get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if "scale_factor" in settings:
                        self._scale_factor = float(settings["scale_factor"])
        except Exception as e:
            # 如果加载失败，使用默认值
            print(f"加载设置失败: {e}")
            self._scale_factor = 1.0
    
    def _save_settings(self):
        """保存当前设置"""
        try:
            config_path = self._get_config_path()
            settings = {
                "scale_factor": self._scale_factor
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"保存设置失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 保存当前设置
        self._save_settings()
        super().closeEvent(event)
    
    # ===== 基础功能方法 =====
    def _available_rect(self):
        """获取当前窗口所在屏幕的可用工作区"""
        scr = self.screen()
        if scr is None:
            # 退化：使用主屏可用区域
            scr = QApplication.primaryScreen()
        return scr.availableGeometry()
    
    def _ground_y(self):
        """计算地面位置（任务栏上边界）"""
        avail = self._available_rect()
        return avail.bottom() - self.height() + 1  # Qt 座标包含边界，用 +1 消除贴边抖动
    
    def _stick_to_ground(self):
        """将宠物的底部贴到可用区域的底部（任务栏上边界）"""
        avail = self._available_rect()
        new_x = min(max(self.x(), avail.left()), avail.right() - self.width() + 1)
        self.move(new_x, self._ground_y())
    
    def _place_random_in_available_area(self, on_ground=True):
        """在可用区域内随机放置"""
        avail = self._available_rect()
        max_x = max(avail.left(), avail.right() - self.width() + 1)
        max_y = max(avail.top(), avail.bottom() - self.height() + 1)
        rand_x = random.randint(avail.left(), max_x)
        if on_ground:
            rand_y = self._ground_y()
        else:
            rand_y = random.randint(avail.top(), max_y)
        self.move(rand_x, rand_y)
    
    # ===== 定时器更新 =====
    def _on_walk_tick(self):
        """主更新循环"""
        # 时间步长（秒）
        dt = max(0.001, self._walk_timer.interval() / 1000.0)
        interval_ms = max(1, self._walk_timer.interval())
        
        # 保存更新前的地面状态
        was_on_ground = self.physics_system.on_ground
        
        # 更新速度控制
        self.speed_controller.update(dt, interval_ms)
        
        # 若正在拖拽，跳过物理更新
        if self.behavior_controller.is_dragging:
            return
        
        # 检查速度并切换到刹车图像
        current_speed_px_per_sec = abs(self.physics_system.vx) * 1000.0 / interval_ms
        current_speed_py_per_sec = abs(self.physics_system.vy) * 1000.0 / interval_ms
        
        # 检查是否真的处于空闲状态（在地面上并且速度小于100）
        is_actually_idle = (self.physics_system.on_ground and 
                          abs(self.physics_system.vx) < 100 and 
                          abs(self.physics_system.vy) < 100)
        
        # 更新空闲时间状态
        entered_idle, exited_idle = self.idle_tracker.update(is_actually_idle)
        
        # 处理速度相关的图片切换（刹车状态）
        if current_speed_px_per_sec > 200 or current_speed_py_per_sec > 200:
            # 速度大于200时，立即切换到刹车图像并重置计时器
            self.renderer._switch_to_state_image("shache")
            self.is_currently_sleeping = False  # 刹车时不睡觉
            if self._shache_timer.isActive():
                self._shache_timer.stop()
        else:
            # 速度低于200时，如果计时器未启动，则启动3秒延时
            if not self._shache_timer.isActive() and self.renderer.current_state == "shache":
                self._shache_timer.start(1500)  # 单位ms
                
        # 处理空闲状态的图片切换（睡眠状态）（睡眠状态下的对话框放在dialog.py中,和idle一起实现）
        # 如果进入空闲状态，切换到sleep图片
        if entered_idle and not self.is_currently_sleeping:
            if random.randint(0, 100) < 30: # 30%的概率进入睡眠状态
            # 随机选择sleep或sleep2图片
                sleep_state = random.choice(["sleep", "sleep2"])
                self.renderer._switch_to_state_image(sleep_state)
                self.is_currently_sleeping = True
        # 如果离开空闲状态且处于睡眠状态，只更新状态标记（实际切换逻辑已移至register_interaction）
        elif exited_idle and self.is_currently_sleeping:
            self.is_currently_sleeping = False
        
        # 更新物理状态
        self.physics_system.update(dt, interval_ms)
        
        # 检查是否离开底部（从地面状态变为非地面状态）
        if was_on_ground and not self.physics_system.on_ground:
            # 从dialogues_move中选择fly类型的对话并显示
            if hasattr(self.dialog_manager, 'dialogues_move') and 'fly' in self.dialog_manager.dialogues_move:
                fly_dialogues = self.dialog_manager.dialogues_move['fly']
                if fly_dialogues and random.randint(0, 100) < 10:
                    text = random.choice(fly_dialogues)
                    self.dialog_manager.show_dialog(text=text, timeout=3000, typing_speed=50)
    
    # ===== 事件处理 =====
    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # # 2次左键点击切换到lift状态的逻辑
            # current_time = time.time()
            
            # # 如果点击间隔超过1秒，重置计数器
            # if current_time - self.last_click_time > 1.0:
            #     self.left_click_count = 0
            
            # self.left_click_count += 1
            # self.last_click_time = current_time
            
            # # 2次点击切换到lift状态
            # if self.left_click_count >= 2:
            #     self.switch_to_lift_state()
            #     self.left_click_count = 0  # 重置计数器
            # else:
                # 普通点击行为
                self.register_interaction()
                
                # 计算总点击次数，不同的次数对应不同的语音
                self.total_click_count += 1
                if self.total_click_count == 10:
                    self.show_dialog(dialog_type="10clicks")
                if self.total_click_count == 25:
                    self.show_dialog(dialog_type="25clicks")
                if self.total_click_count == 50:
                    self.show_dialog(dialog_type="50clicks")
                if self.total_click_count == 75:
                    self.show_dialog(dialog_type="75clicks")
                if self.total_click_count >= 100:
                    self.total_click_count = 0

        self.behavior_controller.on_mouse_press(event)
    
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        self.behavior_controller.on_mouse_move(event)
    
    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        self.behavior_controller.on_mouse_release(event)
    
    # ===== 公共接口方法 =====
    # 缩放相关
    def increase_scale(self, step=0.1):
        """增大宠物尺寸"""
        self._scale_factor += step
        self.renderer.apply_scale(self._scale_factor)
        self._stick_to_ground()
    
    def decrease_scale(self, step=0.1):
        """减小宠物尺寸"""
        self._scale_factor -= step
        self.renderer.apply_scale(self._scale_factor)
        self._stick_to_ground()
    
    def reset_scale(self):
        """重置宠物尺寸"""
        self._scale_factor = 1.0
        self.renderer.apply_scale(self._scale_factor)
        self._stick_to_ground()
    
    # 运动相关
    def start_walk(self, speed_px_per_sec=random.randint(120, 180),dir=random.choice([1,-1])):
        """开始行走"""
        interval_ms = max(1, self._walk_timer.interval())
        self.speed_controller.start_walk(speed_px_per_sec*dir, interval_ms)
        self._stick_to_ground()
        if dir == 1:
            self.face_right()
        else:
            self.face_left()

    def stop_walk(self):
        """停止行走"""
        self.speed_controller.stop_walk()
    
    def jump(self):
        """执行跳跃"""
        self.physics_system.jump()
    
    def enable_random_speed(self, enabled: bool = True):
        """启用或禁用随机速度"""
        self.speed_controller.enable_random_speed(enabled)
    
    # 朝向相关（委托给renderer）
    def face_left(self, animate: bool = True):
        """面向左"""
        self.renderer.face_left(animate)
    
    def face_right(self, animate: bool = True):
        """面向右"""
        self.renderer.face_right(animate)
    
    # 右键菜单（委托给behavior_controller）
    def show_context_menu(self):
        """显示右键菜单"""
        self.behavior_controller.show_context_menu()

    def show_dialog(self, text=None, dialog_type=None, timeout=3000):
        """显示一个对话框"""
        self.dialog_manager.show_dialog(text, dialog_type, timeout)
    
    def show_random_dialog(self):
        """显示一个随机对话框"""
        self.dialog_manager.show_random_dialog()
    
    def switch_to_lift_state(self):
        """切换到被拎起状态"""
        # 切换到lift状态图片
        self.renderer._switch_to_state_image("lift")
        self.is_in_lift_state = True
        self.is_currently_sleeping = False
        
        # 更新物理状态
        self.physics_system.on_ground = False
        self.physics_system.vx = 0
        self.physics_system.vy = 0
        
        # 停止行走
        self.stop_walk()
        
        # 重置空闲时间
        self.idle_tracker.reset()
    
    def register_interaction(self):
        """注册用户交互"""
        self.dialog_manager.register_interaction()
        
        # 用户交互时，重置空闲时间
        self.idle_tracker.reset()
        
        # 用户交互时，如果当前处于睡眠状态，执行跳跃并切换图片
        if self.is_currently_sleeping:
            self.physics_system.on_ground = True
            self.physics_system.vx = 0
            self.physics_system.vy = 0
            self.behavior_controller._drag_offset = None
            self.renderer._switch_to_state_image("lift2")  # 先切换到lift2状态
            self.is_currently_sleeping = False  
            # self.physics_system.jump()
            # 先不急着实现jump,不知道为啥这个方法没效果，到时候试试单独实现。
            # 添加等待时间，使用QTimer.singleShot实现延迟切换到default
            QTimer.singleShot(2000, lambda: self.renderer._switch_to_state_image("default"))  # 2000毫秒
        
        # 用户交互时，如果当前在lift状态，切换回default状态
        elif self.is_in_lift_state:
            self.renderer._switch_to_state_image("default")
            self.is_in_lift_state = False
            # 恢复物理状态
            self.physics_system.on_ground = True
            self.physics_system.vx = 0
            self.physics_system.vy = 0
            self.behavior_controller._drag_offset = None
