import json
import os
from PyQt5.QtGui import QMovie, QPixmap, QTransform
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QLabel

class Renderer:
    def __init__(self, pet_widget, asset_path=None, max_width=None, max_height=None):
        self.pet_widget = pet_widget
        
        # 显示容器
        self.label = QLabel(self.pet_widget)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setScaledContents(True)
        
        # 从配置文件加载状态与图片路径的字典
        self._states = {}
        self._default_asset = "assets/扫地机器人.png"
        self._load_assets_from_config()
        
        # 设置默认资源路径
        if asset_path is None:
            asset_path = self._default_asset
        
        # 兼容 GIF/PNG
        self._dir = 1  # 朝向：1 面向右，-1 面向左
        self.asset_path = asset_path
        self._is_movie = asset_path.lower().endswith(".gif")
        self.current_state = "default"  # 跟踪当前状态
        
        # 加载资源并设置初始尺寸
        if self._is_movie:
            self.movie = QMovie(asset_path)
            # 初始原始尺寸
            base_size = self.movie.frameRect().size()
            # 计算目标尺寸（可选）
            if max_width or max_height:
                target = QSize(max_width or base_size.width(), max_height or base_size.height())
                new_size = base_size.scaled(target, Qt.KeepAspectRatio)
                self.movie.setScaledSize(new_size)
                size = new_size
            else:
                size = base_size
            # 不将 movie 直接绑定到 label，转为手动更新以支持镜像
            self.movie.frameChanged.connect(self._on_movie_frame)
            self.movie.start()
        else:
            self.pixmap = QPixmap(asset_path)
            base_size = self.pixmap.size()
            if max_width or max_height:
                target = QSize(max_width or base_size.width(), max_height or base_size.height())
                scaled_pixmap = self.pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._base_pixmap = scaled_pixmap
                size = scaled_pixmap.size()
            else:
                self._base_pixmap = self.pixmap
                size = base_size
            # 初始化展示
            self._refresh_label_pixmap()
        
        # 调整窗口与标签大小
        self.base_size = size
        self.pet_widget.resize(size)
        self.label.resize(size)
    
    def _load_assets_from_config(self):
        """从配置文件加载图片资源路径"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic_asset.json")
        
        # 默认配置，当配置文件不存在或加载失败时使用
        default_config = {
            "states": {
                "default": "assets/扫地机器人.png",
                "shache": "assets/brake.png"
            },
            "default_asset": "assets/扫地机器人.png"
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 加载状态与图片路径
                    if "states" in config and isinstance(config["states"], dict):
                        self._states = config["states"]
                    else:
                        self._states = default_config["states"]
                    # 加载默认资源
                    if "default_asset" in config:
                        self._default_asset = config["default_asset"]
                    else:
                        self._default_asset = default_config["default_asset"]
            else:
                # 如果配置文件不存在，创建默认配置文件
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                # 使用默认配置
                self._states = default_config["states"]
                self._default_asset = default_config["default_asset"]
        except Exception as e:
            print(f"加载资源配置失败: {e}")
            # 使用默认配置
            self._states = default_config["states"]
            self._default_asset = default_config["default_asset"]
    
    def _switch_to_state_image(self, state_name):
        """根据状态名称切换图像资源"""
        if state_name in self._states:
            self.asset_path = self._states[state_name]
            self.current_state = state_name  # 更新当前状态
        if state_name not in self._states:
            return False
        
        new_asset_path = self._states[state_name]
        
        # 停止之前的动画（如果有）
        if hasattr(self, 'movie') and self.movie:
            self.movie.stop()
            self.movie.frameChanged.disconnect(self._on_movie_frame)
            self.movie = None
        
        # 更新asset_path和is_movie属性
        self.asset_path = new_asset_path
        self._is_movie = new_asset_path.lower().endswith(".gif")
        
        # 加载新的资源
        if self._is_movie:
            self.movie = QMovie(new_asset_path)
            # 初始原始尺寸
            base_size = self.movie.frameRect().size()
            # 计算目标尺寸
            target = QSize(self.base_size.width(), self.base_size.height())
            new_size = base_size.scaled(target, Qt.KeepAspectRatio)
            self.movie.setScaledSize(new_size)
            # 连接信号并启动动画
            self.movie.frameChanged.connect(self._on_movie_frame)
            self.movie.start()
        else:
            self.pixmap = QPixmap(new_asset_path)
            # 缩放到当前尺寸
            target = QSize(self.base_size.width(), self.base_size.height())
            scaled_pixmap = self.pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._base_pixmap = scaled_pixmap
            # 刷新显示
            self._refresh_label_pixmap()
        
        return True


    def _refresh_label_pixmap(self):
        """刷新标签上显示的图像"""
        if self._is_movie:
            # 等待 frameChanged 回调进行更新
            pix = self.movie.currentPixmap()
            if not pix.isNull():
                if self._dir == -1:
                    pix = pix.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
                self.label.setPixmap(pix)
        else:
            pix = self._base_pixmap
            if self._dir == -1:
                pix = pix.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
            self.label.setPixmap(pix)
    
    def _on_movie_frame(self, _index):
        """GIF 帧更新回调"""
        # 每帧更新时应用朝向镜像
        pix = self.movie.currentPixmap()
        if pix.isNull():
            return
        if self._dir == -1:
            pix = pix.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
        self.label.setPixmap(pix)
    
    def turn_to(self, direction: int, animate: bool = True):
        """转向指定方向"""
        from PyQt5.QtWidgets import QApplication
        
        if direction not in (-1, 1) or direction == self._dir:
            return
        
        if not animate:
            self._dir = direction
            self._refresh_label_pixmap()
            return
        
        # 过渡动画：水平挤压到窄->翻转->恢复
        steps = 50
        min_scale_x = 0.2
        width0 = self.pet_widget.width()
        height0 = self.pet_widget.height()
        
        # 收缩阶段
        for i in range(1, steps + 1):
            s = 1.0 - (1.0 - min_scale_x) * (i / steps)
            new_w = max(1, int(width0 * s))
            self.label.resize(new_w, height0)
            self.pet_widget.resize(new_w, height0)
            # 只在地面上时才执行贴地操作
            if hasattr(self.pet_widget, 'physics_system') and self.pet_widget.physics_system.on_ground:
                if hasattr(self.pet_widget, '_stick_to_ground'):
                    self.pet_widget._stick_to_ground()
            QApplication.processEvents()
        
        # 翻转方向
        self._dir = direction
        self._refresh_label_pixmap()
        
        # 展开阶段
        for i in range(1, steps + 1):
            s = min_scale_x + (1.0 - min_scale_x) * (i / steps)
            new_w = max(1, int(width0 * s))
            self.label.resize(new_w, height0)
            self.pet_widget.resize(new_w, height0)
            # 只在地面上时才执行贴地操作
            if hasattr(self.pet_widget, 'physics_system') and self.pet_widget.physics_system.on_ground:
                if hasattr(self.pet_widget, '_stick_to_ground'):
                    self.pet_widget._stick_to_ground()
            QApplication.processEvents()
    
    def face_left(self, animate: bool = True):
        """面向左"""
        self.turn_to(-1, animate)
    
    def face_right(self, animate: bool = True):
        """面向右"""
        self.turn_to(1, animate)
    
    def apply_scale(self, scale_factor, min_scale=0.2, max_scale=5.0):
        """应用缩放"""
        # 限制缩放范围
        scale_factor = max(min_scale, min(scale_factor, max_scale))
        
        if self._is_movie:
            w = max(1, int(self.base_size.width() * scale_factor))
            h = max(1, int(self.base_size.height() * scale_factor))
            new_size = QSize(w, h)
            self.movie.setScaledSize(new_size)
            self.label.resize(new_size)
            self.pet_widget.resize(new_size)
        else:
            w = max(1, int(self.base_size.width() * scale_factor))
            h = max(1, int(self.base_size.height() * scale_factor))
            target = QSize(w, h)
            scaled_pixmap = self._base_pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._base_pixmap = scaled_pixmap
            self._refresh_label_pixmap()
            self.label.resize(scaled_pixmap.size())
            self.pet_widget.resize(scaled_pixmap.size())