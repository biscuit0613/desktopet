import random

class SpeedController:
    def __init__(self, physics_system):
        self.physics_system = physics_system
        
        # 随机速度参数
        self._random_speed_enabled = True
        self._speed_min_px_per_sec = 50.0
        self._speed_max_px_per_sec = 170.0
        self._speed_change_interval_range = (1.0, 5.0)  # 秒
        self._speed_current_px_per_sec = 0.0
        self._speed_target_px_per_sec = 0.0
        self._speed_blend_per_sec = 1.5  # 速度朝目标平滑靠拢的速率
        self._time_to_next_speed_change = 0.0
        
        # 摩擦调速（阈值-衰减-停用 循环）
        self._friction_enabled = True
        self._friction_threshold_px_per_sec = 200.0
        self._friction_target_px_per_sec = 100.0
        self._friction_activation_delay_range = (2.0, 4.0)
        self._friction_time_to_activation = 0.0
        self._friction_waiting = False
        self._friction_active = False
        self._friction_blend_per_sec = 0.0005  # 速度朝目标平滑靠拢的速率
        self._friction_cooldown_after_throw = 1  # 抛掷后禁用摩擦的冷却（秒）
        self._friction_cooldown = 0.0
        self._thrown_recently = False  # 仅抛掷来源的高速在地面时触发摩擦
    
    @property
    def random_speed_enabled(self):
        return self._random_speed_enabled
    
    @property
    def thrown_recently(self):
        return self._thrown_recently
    
    @thrown_recently.setter
    def thrown_recently(self, value):
        self._thrown_recently = value
    
    def update(self, dt, interval_ms):
        """更新速度控制状态"""
        # 计算当前速度
        current_speed_px_per_sec = abs(self.physics_system.vx) * 1000.0 / interval_ms
        
        # --- 摩擦调速状态机 --- 
        if self._friction_cooldown > 0:
            self._friction_cooldown -= dt
            # 冷却期不启用摩擦，并重置等待/激活状态
            self._friction_active = False
            self._friction_waiting = False
            self._friction_time_to_activation = 0.0
        elif self._friction_enabled and self.physics_system.on_ground and self._thrown_recently:
            if not self._friction_active:
                if current_speed_px_per_sec >= self._friction_threshold_px_per_sec:
                    if not self._friction_waiting:
                        self._friction_time_to_activation = random.uniform(*self._friction_activation_delay_range)
                        self._friction_waiting = True
                    else:
                        self._friction_time_to_activation -= dt
                        if self._friction_time_to_activation <= 0:
                            self._friction_active = True
                else:
                    self._friction_waiting = False
                    self._friction_time_to_activation = 0.0
            else:
                # 平滑将速度衰减到目标
                blend = min(1.0, self._friction_blend_per_sec * dt)
                new_speed = current_speed_px_per_sec + (self._friction_target_px_per_sec - current_speed_px_per_sec) * blend
                self._speed_current_px_per_sec = new_speed
                per_tick = int(new_speed * interval_ms / 1000.0)
                if per_tick == 0 and new_speed > 0:
                    per_tick = 1
                sign = 1 if self.physics_system.vx >= 0 else -1
                self.physics_system.vx = sign * per_tick
                
                # 终止条件：接近目标
                if abs(new_speed - self._friction_target_px_per_sec) < 5.0:
                    self._friction_active = False
                    self._friction_waiting = False
                    self._friction_time_to_activation = 0.0
                    self._thrown_recently = False
        else:
            # 空中不启用摩擦，清理状态
            self._friction_active = False
            self._friction_waiting = False
            self._friction_time_to_activation = 0.0
        
        # --- 随机速度更新 --- 
        if (self._random_speed_enabled and abs(self.physics_system.vx) > 0 and not self._friction_active
                and self.physics_system.on_ground and not self._thrown_recently):
            self._time_to_next_speed_change -= dt
            if self._time_to_next_speed_change <= 0:
                self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
                self._time_to_next_speed_change = random.uniform(*self._speed_change_interval_range)
            
            # 朝目标平滑靠近
            blend = min(1.0, self._speed_blend_per_sec * dt)
            self._speed_current_px_per_sec += (self._speed_target_px_per_sec - self._speed_current_px_per_sec) * blend
            
            # 换算为每tick像素，保持方向
            per_tick = max(1, int(self._speed_current_px_per_sec * interval_ms / 1000.0))
            sign = 1 if self.physics_system.vx >= 0 else -1
            self.physics_system.vx = sign * per_tick
    
    def start_walk(self, speed_px_per_sec=120, interval_ms=16):
        """开始行走"""
        # 将速度换算为每tick像素，保持方向
        per_tick = max(1, int(speed_px_per_sec * interval_ms / 1000.0))
        self.physics_system.vx = per_tick if self.physics_system.vx >= 0 else -per_tick
        
        # 初始化随机速度状态
        self._speed_current_px_per_sec = speed_px_per_sec
        if self._random_speed_enabled:
            self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
            self._time_to_next_speed_change = random.uniform(*self._speed_change_interval_range)
        else:
            self._speed_target_px_per_sec = speed_px_per_sec
            self._time_to_next_speed_change = 0.0
        
        # 重置摩擦状态
        self._friction_waiting = False
        self._friction_active = False
        self._friction_time_to_activation = 0.0
    
    def stop_walk(self):
        """停止行走"""
        self.physics_system.vx = 0
    
    def enable_random_speed(self, enabled: bool = True):
        """启用或禁用随机速度"""
        self._random_speed_enabled = enabled
        if enabled and self.physics_system.vx != 0:
            self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
            self._time_to_next_speed_change = random.uniform(*self._speed_change_interval_range)
    
    def randomize_speed_once(self):
        """随机变化一次速度"""
        self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
    
    def set_friction_cooldown(self):
        """设置摩擦冷却时间"""
        self._friction_cooldown = self._friction_cooldown_after_throw
    
    def check_friction_cooldown(self):
        """检查摩擦冷却是否结束"""
        return self._friction_cooldown <= 0