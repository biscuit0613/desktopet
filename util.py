import time

class IdleTimeTracker:
    def __init__(self):
        """初始化空闲时间跟踪器"""
        self.idle_time = 0  # 空闲时间（秒）
        self.last_update_time = time.time()
        self.is_idle = False
        self.idle_threshold = 30  # 默认空闲阈值（秒）
    
    def update(self, is_actually_idle):
        """更新空闲时间状态
        
        Args:
            is_actually_idle: 布尔值，表示当前是否真的处于空闲状态
        
        Returns:
            tuple: (是否进入空闲状态, 是否离开空闲状态)
        """
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time
        
        was_idle = self.is_idle
        
        if is_actually_idle:
            self.idle_time += delta_time
            if self.idle_time >= self.idle_threshold:
                self.is_idle = True
            else:
                self.is_idle = False
        else:
            self.idle_time = 0
            self.is_idle = False
        
        entered_idle = not was_idle and self.is_idle
        exited_idle = was_idle and not self.is_idle
        
        return entered_idle, exited_idle
    
    def reset(self):
        """重置空闲时间"""
        self.idle_time = 0
        self.is_idle = False
    
    def set_threshold(self, threshold):
        """设置空闲时间阈值
        
        Args:
            threshold: 空闲时间阈值（秒）
        """
        self.idle_threshold = threshold
    
    def get_idle_time(self):
        """获取当前的空闲时间
        
        Returns:
            float: 当前的空闲时间（秒）
        """
        return self.idle_time
    
    def get_is_idle(self):
        """获取当前是否处于空闲状态
        
        Returns:
            bool: 当前是否处于空闲状态
        """
        return self.is_idle