import random
import dialog
from PyQt5.QtCore import Qt

class PhysicsSystem:
    def __init__(self, pet):
        self.pet = pet
        
        self.dialog_manager = dialog.DialogManager(self.pet)
        # 物理参数
        self._vx = 0  # 像素/帧
        self._vy = 0.0  # 像素/秒
        self._gravity_px_per_sec2 = 2000.0  # 重力加速度
        
        # 反弹参数
        self._bounce_min = 1
        self._bounce_max = 3
        self._bounce_restitution_range = (0.35, 0.6)  # 速度保留比例
        self._remaining_bounces = 0
        self._on_ground = False
        self._air_grace_time = 0.0  # 抛掷后短暂忽略地面碰撞
    
    @property
    def vx(self):
        return self._vx
    
    @vx.setter
    def vx(self, value):
        self._vx = value
    
    @property
    def vy(self):
        return self._vy
    
    @vy.setter
    def vy(self, value):
        self._vy = value
    
    @property
    def on_ground(self):
        return self._on_ground
        
    @on_ground.setter
    def on_ground(self, value):
        self._on_ground = value
    
    def update(self, dt, interval_ms):
        """更新物理状态"""
        avail = self.pet._available_rect()
        
        # --- 水平运动 --- 
        x = self.pet.x() + int(self._vx)  # 按每tick像素应用，简单平滑
        left_limit = avail.left()
        right_limit = avail.right() - self.pet.width() + 1
        
        if x < left_limit:
            x = left_limit
            self._vx = abs(self._vx)
            self.pet.face_right()
        elif x > right_limit:
            x = right_limit
            self._vx = -abs(self._vx)
            self.pet.face_left()
        
        # --- 垂直运动（重力+跳跃+反弹）---
        ground_y = self.pet._ground_y()
        y = self.pet.y()
        
        # 应用重力
        self._vy += self._gravity_px_per_sec2 * dt
        y = int(y + self._vy * dt)
        
        # 碰撞地面（考虑空中宽限时间）
        if y >= ground_y and self._air_grace_time <= 0:
            # 刚落地事件（从空中到地面且有向下速度）
            if not self._on_ground and self._vy > 0:
                if self._remaining_bounces <= 0:
                    self._remaining_bounces = random.randint(self._bounce_min, self._bounce_max)
                
                # 速度阈值过小则直接停住
                speed = self._vy
                if self._remaining_bounces > 0 and speed > 150:
                    r = random.uniform(*self._bounce_restitution_range)
                    self._vy = -speed * r
                    self._remaining_bounces -= 1
                    # 轻微抬起避免下一帧重复判定
                    y = ground_y - 1
                    self._on_ground = False
                else:
                    y = ground_y
                    self._vy = 0.0
                    self._remaining_bounces = 0
                    self._on_ground = True
            else:
                y = ground_y
                self._vy = 0.0
                self._remaining_bounces = 0
                self._on_ground = True
        else:
            self._on_ground = False
        
        self.pet.move(x, y)
        
        # 更新空中宽限计时
        if self._air_grace_time > 0:
            self._air_grace_time -= dt
    
    def jump(self):
        """执行跳跃动作"""
        # if self.pet.y() >= self.pet._ground_y() and self._vy == 0.0:
        if self._vy == 0.0:
            jump_speed = -random.randint(700, 1800)
            self._vy = jump_speed
            self._remaining_bounces = 0
            self._on_ground = False
            self.dialog_manager.show_jump_dialog()
    
    def set_air_grace_time(self, time):
        """设置空中宽限时间"""
        self._air_grace_time = time
    
    def stop_movement(self):
        """停止所有移动"""
        self._vx = 0
        self._vy = 0.0