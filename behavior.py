import random
import time
import math
from PyQt5.QtWidgets import QMenu
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt, QTimer

class BehaviorController:
    def __init__(self, pet):
        self.pet = pet
        # 拖动相关
        self._drag_offset = None
        self._is_dragging = False
        self._drag_history = []  # [(x, y, t), ...]

        self._swing_angle = 0
        self._swing_speed = 0
        self._swing_damping = 0.90  # 降低阻尼系数，使摆动更持久
        self._max_swing_angle = 25  # 增加最大晃动角度
        self._mouse_velocity = [0, 0]  # 鼠标速度 [vx, vy]
        self._prev_mouse_pos = None  # 上一帧鼠标位置
        self._prev_time = time.time()  # 上一帧时间
    
    @property
    def is_dragging(self):
        return self._is_dragging
    
    def on_mouse_press(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.pet.frameGeometry().topLeft()
            self._is_dragging = True
            self._drag_history.clear()
            # 停止当前速度，避免拖拽时被物理影响
            self.pet.physics_system.stop_movement()
        elif event.button() == Qt.RightButton:
            self.show_context_menu()
    
    def on_mouse_move(self, event):
        """处理鼠标移动事件"""
        current_time = time.time()
        dt = current_time - self._prev_time
        # 检查是否处于lift状态，如果是，则跟随鼠标并添加晃动效果
        if hasattr(self.pet, 'is_in_lift_state') and self.pet.is_in_lift_state:
            current_mouse_pos = (event.globalX(), event.globalY())
            
            # 计算鼠标速度
            if self._prev_mouse_pos and dt > 0:
                dx = current_mouse_pos[0] - self._prev_mouse_pos[0]
                self._mouse_velocity[0] = dx / dt  # 水平速度
            
            # 更新摆动物理
            self._update_swing(dt)
            
            # 计算摆动位移
            swing_offset_x = math.sin(math.radians(self._swing_angle)) * 30  # 增加摆动幅度的乘数，从15增加到30
            
            # 计算目标位置，考虑摆动偏移
            target_x = int(event.globalX() - self.pet.width() // 2 + swing_offset_x)
            target_y = int(event.globalY() - self.pet.height() // 3)
            
            self.pet.move(target_x, target_y)
            
            # 更新朝向（根据摆动方向）
            if self._swing_angle > 0:
                self.pet.renderer.face_right(False)
            elif self._swing_angle < 0:
                self.pet.renderer.face_left(False)
            
            # 保存当前鼠标位置和时间
            self._prev_mouse_pos = current_mouse_pos
            self._prev_time = current_time
        elif event.buttons() & Qt.LeftButton and self._drag_offset is not None:
            self.pet.move(event.globalPos() - self._drag_offset)
            # 记录轨迹（限制长度与时间窗口）
            now = time.monotonic()
            self._drag_history.append((self.pet.x(), self.pet.y(), now))
            # 保留最近 ~0.2 秒的样本
            cutoff = now - 0.2
            while len(self._drag_history) > 0 and self._drag_history[0][2] < cutoff:
                self._drag_history.pop(0)
        else:
            # 不在lift状态且未拖动时，重置摆动相关变量
            self._prev_mouse_pos = None
            self._swing_angle = 0
            self._swing_speed = 0
    
    def _update_swing(self, dt):
        """更新摆动物理状态"""
        # 根据鼠标水平速度影响摆动
        mouse_influence = self._mouse_velocity[0] * 0.15  # 增加鼠标速度对摆动的影响系数
        
        # 计算恢复力（让摆动回到中心位置的力）
        restoring_force = -self._swing_angle * 0.05  # 减小恢复力，使摆动更缓慢地回到中心
        
        # 更新摆动速度
        self._swing_speed += (mouse_influence + restoring_force) * dt
        
        # 应用阻尼
        self._swing_speed *= self._swing_damping
        
        # 更新摆动角度
        self._swing_angle += self._swing_speed
        
        # 限制最大角度
        self._swing_angle = max(-self._max_swing_angle, min(self._max_swing_angle, self._swing_angle))
        
        # 逐渐减小鼠标速度影响（摩擦）
        self._mouse_velocity[0] *= 0.8  # 减小摩擦系数，使鼠标速度影响更持久
    
    def on_mouse_release(self, event):
        """处理鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self._drag_offset = None
            # 抛掷速度估计
            vx_tick, vy_per_sec = self._estimate_throw_velocity()
            if vx_tick is not None and vy_per_sec is not None:
                self.pet.physics_system.vx = vx_tick
                self.pet.physics_system.vy = vy_per_sec
                # 根据水平速度设置面向
                if self.pet.physics_system.vx > 0:
                    self.pet.renderer.face_right(False)
                elif self.pet.physics_system.vx < 0:
                    self.pet.renderer.face_left(False)
                
                self.pet.physics_system.set_air_grace_time(0.12)  # 空中宽限时间
                
                # 抛掷后短暂禁用摩擦，避免瞬间被摩擦拉回慢速
                self.pet.speed_controller.set_friction_cooldown()
                self.pet.speed_controller.thrown_recently = True
                # 启动对话框交互
                self.pet.register_interaction()
            self._is_dragging = False
    
    def show_context_menu(self):
        """显示右键菜单"""
        menu = QMenu(self.pet)
        bigger_action = menu.addAction("变大")
        smaller_action = menu.addAction("变小")
        reset_action = menu.addAction("重置大小")
        menu.addSeparator()
        start_walk_action = menu.addAction("开始行走")
        stop_walk_action = menu.addAction("停止行走")
        jump_action = menu.addAction("跳跃")
        menu.addSeparator()
        toggle_random_speed_action = menu.addAction("切换随机速度")
        randomize_speed_once_action = menu.addAction("随机变化一次")
        menu.addSeparator()
        random_place_ground_action = menu.addAction("随机放置（任务栏上）")
        random_place_free_action = menu.addAction("随机放置（屏幕上）")
        menu.addSeparator()
        face_left_action = menu.addAction("面向左")
        face_right_action = menu.addAction("面向右")
        quit_action = menu.addAction("退出")
        menu.addSeparator()
        show_dialog_action = menu.addAction("显示对话")
        toggle_auto_dialog_action = menu.addAction("启用自动对话")
        toggle_auto_dialog_action.setCheckable(True)
        toggle_auto_dialog_action.setChecked(True)  # 默认启用
        menu.addSeparator()
        save_size_action = menu.addAction("保存当前设置")
    
        
        action = menu.exec_(QCursor.pos())
        
        if action == bigger_action:
            self.pet.increase_scale(0.1)
        elif action == smaller_action:
            self.pet.decrease_scale(0.1)
        elif action == reset_action:
            self.pet.reset_scale()
        elif action == start_walk_action:
            self.pet.start_walk()
        elif action == stop_walk_action:
            self.pet.stop_walk()
        elif action == jump_action:
            self.pet.jump()
        elif action == toggle_random_speed_action:
            self.pet.enable_random_speed(not self.pet.speed_controller.random_speed_enabled)
        elif action == randomize_speed_once_action:
            self.pet.speed_controller.randomize_speed_once()
        elif action == random_place_ground_action:
            self.pet._place_random_in_available_area(on_ground=True)
        elif action == random_place_free_action:
            self.pet._place_random_in_available_area(on_ground=False)
        elif action == face_left_action:
            self.pet.renderer.face_left(True)
        elif action == face_right_action:
            self.pet.renderer.face_right(True)
        elif action == quit_action:
            self.pet.close()
        elif action == show_dialog_action:
            self.pet.show_random_dialog()
            self.pet.register_interaction()
        elif action == toggle_auto_dialog_action:
            self.pet.dialog_manager.set_auto_trigger_enabled(action.isChecked())
        elif action == save_size_action:
            self.pet._save_settings()

    def _estimate_throw_velocity(self):
        """估计抛掷速度"""
        # 使用最近轨迹点估算平均速度
        if len(self._drag_history) < 2:
            return None, None
            
        x0, y0, t0 = self._drag_history[0]
        x1, y1, t1 = self._drag_history[-1]
        dt = max(1e-3, t1 - t0)
        
        vx_px_per_sec = (x1 - x0) / dt
        vy_px_per_sec = (y1 - y0) / (1.2*dt)
        
        # 将水平速度换算为每tick像素
        interval_ms = max(1, self.pet._walk_timer.interval())
        per_tick = int(abs(vx_px_per_sec) * interval_ms / 1000.0)
        
        if per_tick == 0 and abs(vx_px_per_sec) > 0:
            per_tick = 1
            
        vx_tick = per_tick if vx_px_per_sec >= 0 else -per_tick
        return vx_tick, vy_px_per_sec

# 为了向后兼容保留旧的类名
Behaviorcontroller = BehaviorController