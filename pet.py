import sys
import random
import time
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QMenu
from PyQt5.QtGui import QMovie, QPixmap, QCursor, QTransform
from PyQt5.QtCore import Qt, QSize, QTimer


class DesktopPet(QWidget):
    def __init__(self, asset_path="assets\扫地机器人.png", max_width=None, max_height=None,
                 initial_random=True, initial_on_ground=False):
        super().__init__()
        # 无边框、置顶、不出现在任务栏、背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | 
                            Qt.WindowStaysOnTopHint | 
                            Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 显示容器
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setScaledContents(True)

        # 兼容 GIF/PNG：GIF 用 QMovie（手动取帧），PNG 用 QPixmap
        self._is_movie = asset_path.lower().endswith(".gif")
        # 朝向：1 面向右，-1 面向左
        self._dir = 1

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
        self.resize(size)
        self.label.resize(size)

        # 拖动偏移
        self._drag_offset = None
        self._is_dragging = False
        self._drag_history = []  # [(x, y, t), ...]

        # 缩放参数
        self._scale_factor = 1.0
        self._base_size = size  # 作为 GIF 的基准尺寸以及 PNG 目标计算的参考

        # 物理 & 行走相关
        self._walk_timer = QTimer(self)
        self._walk_timer.setInterval(16)  # ~60 FPS
        self._walk_timer.timeout.connect(self._on_walk_tick)
        self._vx = 0  # 像素/帧（内部以 dt 转换为像素/秒逻辑）
        self._vy = 0.0  # 像素/秒
        self._gravity_px_per_sec2 = 2000.0  # 重力加速度（像素/秒²）
        self._jump_speed_px_per_sec = random.randint(700,1800)  # 起跳初速度
        # 反弹参数
        self._bounce_min = 1
        self._bounce_max = 3
        self._bounce_restitution_range = (0.35, 0.6)  # 速度保留比例
        self._remaining_bounces = 0
        self._on_ground = False
        self._air_grace_time = 0.0  # 抛掷后短暂忽略地面碰撞，避免突兀贴地

        # 随机速度参数（时快时慢）
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

        # 初始位置
        if initial_random:
            self._place_random_in_available_area(on_ground=initial_on_ground)
        else:
            self._stick_to_ground()
        self._walk_timer.start()  # 物理系统常开
        self._on_ground = True

    # 缩放应用
    def _apply_scale(self):
        # 限制缩放范围
        min_scale, max_scale = 0.2, 5.0
        if self._scale_factor < min_scale:
            self._scale_factor = min_scale
        if self._scale_factor > max_scale:
            self._scale_factor = max_scale

        if self._is_movie:
            w = max(1, int(self._base_size.width() * self._scale_factor))
            h = max(1, int(self._base_size.height() * self._scale_factor))
            new_size = QSize(w, h)
            self.movie.setScaledSize(new_size)
            self.label.resize(new_size)
            self.resize(new_size)
            # movie 帧更新回调里会刷新镜像后的帧
        else:
            w = max(1, int(self._base_size.width() * self._scale_factor))
            h = max(1, int(self._base_size.height() * self._scale_factor))
            target = QSize(w, h)
            scaled_pixmap = self._base_pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._base_pixmap = scaled_pixmap
            self._refresh_label_pixmap()
            self.label.resize(scaled_pixmap.size())
            self.resize(scaled_pixmap.size())

        # 缩放后保持贴地
        self._stick_to_ground()

    def increase_scale(self, step=0.1):
        self._scale_factor += step
        self._apply_scale()

    def decrease_scale(self, step=0.1):
        self._scale_factor -= step
        self._apply_scale()

    def reset_scale(self):
        self._scale_factor = 1.0
        self._apply_scale()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._is_dragging = True
            self._drag_history.clear()
            # 停止当前速度，避免拖拽时被物理影响
            self._vx = 0
            self._vy = 0.0
        elif event.button() == Qt.RightButton:
            self.show_context_menu()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_offset is not None:
            self.move(event.globalPos() - self._drag_offset)
            # 记录轨迹（限制长度与时间窗口）
            now = time.monotonic()
            self._drag_history.append((self.x(), self.y(), now))
            # 保留最近 ~0.2 秒的样本
            cutoff = now - 0.2
            while len(self._drag_history) > 0 and self._drag_history[0][2] < cutoff:
                self._drag_history.pop(0)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = None
            # 抛掷速度估计
            vx_tick, vy_per_sec = self._estimate_throw_velocity()
            if vx_tick is not None and vy_per_sec is not None:
                self._vx = vx_tick
                self._vy = vy_per_sec
                # 根据水平速度设置面向
                if self._vx > 0:
                    self.face_right(False)
                elif self._vx < 0:
                    self.face_left(False)
                self._on_ground = False
                self._air_grace_time = 0.12# 空中宽限时间，避免抛掷后立即贴地
    
                # 抛掷后短暂禁用摩擦，避免瞬间被摩擦拉回慢速
                self._friction_cooldown = self._friction_cooldown_after_throw
                self._thrown_recently = True
            self._is_dragging = False

    def show_context_menu(self):
        menu = QMenu(self)
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
        action = menu.exec_(QCursor.pos())
        if action == bigger_action:
            self.increase_scale(0.1)
        elif action == smaller_action:
            self.decrease_scale(0.1)
        elif action == reset_action:
            self.reset_scale()
        elif action == start_walk_action:
            self.start_walk()
        elif action == stop_walk_action:
            self.stop_walk()
        elif action == jump_action:
            self.jump()
        elif action == toggle_random_speed_action:
            self.enable_random_speed(not self._random_speed_enabled)
        elif action == randomize_speed_once_action:
            self.randomize_speed_once()
        elif action == random_place_ground_action:
            self._place_random_in_available_area(on_ground=True)
        elif action == random_place_free_action:
            self._place_random_in_available_area(on_ground=False)
        elif action == face_left_action:
            self.face_left(True)
        elif action == face_right_action:
            self.face_right(True)
        elif action == quit_action:
            self.close()

    # ====== 朝向、镜像与转身动画 ======
    def _refresh_label_pixmap(self):
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
        # 每帧更新时应用朝向镜像
        pix = self.movie.currentPixmap()
        if pix.isNull():
            return
        if self._dir == -1:
            pix = pix.transformed(QTransform().scale(-1, 1), Qt.SmoothTransformation)
        self.label.setPixmap(pix)

    def turn_to(self, direction: int, animate: bool = True):
        if direction not in (-1, 1) or direction == self._dir:
            return
        if not animate:
            self._dir = direction
            self._refresh_label_pixmap()
            return
        # 过渡动画：水平挤压到窄->翻转->恢复
        steps = 50
        min_scale_x = 0.2
        width0 = self.width()
        height0 = self.height()
        # 收缩阶段
        for i in range(1, steps + 1):
            s = 1.0 - (1.0 - min_scale_x) * (i / steps)
            new_w = max(1, int(width0 * s))
            self.label.resize(new_w, height0)
            self.resize(new_w, height0)
            if self._on_ground:
                self._stick_to_ground()
            QApplication.processEvents()
        # 翻转方向
        self._dir = direction
        self._refresh_label_pixmap()
        # 展开阶段
        for i in range(1, steps + 1):
            s = min_scale_x + (1.0 - min_scale_x) * (i / steps)
            new_w = max(1, int(width0 * s))
            self.label.resize(new_w, height0)
            self.resize(new_w, height0)
            if self._on_ground:
                self._stick_to_ground()
            QApplication.processEvents()

    def face_left(self, animate: bool = True):
        self.turn_to(-1, animate)

    def face_right(self, animate: bool = True):
        self.turn_to(1, animate)

    # ===== 行走与贴地 =====
    def _available_rect(self):
        # 当前窗口所在屏幕的可用工作区（排除任务栏）
        scr = self.screen()
        if scr is None:
            # 退化：使用主屏可用区域
            scr = QApplication.primaryScreen()
        return scr.availableGeometry()

    def _ground_y(self):
        # 任务栏上边界 == 可用区域底边
        avail = self._available_rect()
        return avail.bottom() - self.height() + 1  # Qt 座标包含边界，用 +1 消除贴边抖动

    def _stick_to_ground(self):
        # 将宠物的 bottom 贴到可用区域的 bottom（任务栏上边界）
        avail = self._available_rect()
        new_x = min(max(self.x(), avail.left()), avail.right() - self.width() + 1)
        self.move(new_x, self._ground_y())

    def _place_random_in_available_area(self, on_ground=True):
        # 在可用区域内随机放置
        avail = self._available_rect()
        max_x = max(avail.left(), avail.right() - self.width() + 1)
        max_y = max(avail.top(), avail.bottom() - self.height() + 1)
        rand_x = random.randint(avail.left(), max_x)
        if on_ground:
            rand_y = self._ground_y()
        else:
            rand_y = random.randint(avail.top(), max_y)
        self.move(rand_x, rand_y)

    def _on_walk_tick(self):
        # 时间步长（秒）
        dt = max(0.001, self._walk_timer.interval() / 1000.0)
        avail = self._available_rect()

        interval_ms = max(1, self._walk_timer.interval())

        # --- 摩擦调速状态机（仅地面生效，且覆盖随机速度更新；抛掷冷却期跳过）---
        current_speed_px_per_sec = abs(self._vx) * 1000.0 / interval_ms
        if self._friction_cooldown > 0:
            self._friction_cooldown -= dt
            # 冷却期不启用摩擦，并重置等待/激活状态
            self._friction_active = False
            self._friction_waiting = False
            self._friction_time_to_activation = 0.0
        elif self._friction_enabled and self._on_ground and self._thrown_recently:
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
                sign = 1 if self._vx >= 0 else -1
                self._vx = sign * per_tick
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

        # --- 随机速度更新（仅地面行走，且未激活摩擦，且非抛掷状态）---
        if (self._random_speed_enabled and abs(self._vx) > 0 and not self._friction_active
                and self._on_ground and not self._thrown_recently):
            self._time_to_next_speed_change -= dt
            if self._time_to_next_speed_change <= 0:
                self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
                self._time_to_next_speed_change = random.uniform(*self._speed_change_interval_range)
            # 朝目标平滑靠近
            blend = min(1.0, self._speed_blend_per_sec * dt)
            self._speed_current_px_per_sec += (self._speed_target_px_per_sec - self._speed_current_px_per_sec) * blend
            # 换算为每 tick 像素，保持方向
            per_tick = max(1, int(self._speed_current_px_per_sec * interval_ms / 1000.0))
            sign = 1 if self._vx >= 0 else -1
            self._vx = sign * per_tick

        # 若正在拖拽，跳过物理更新
        if self._is_dragging:
            return

        # --- 水平运动 ---
        x = self.x() + int(self._vx)  # _vx 这里按每 tick 像素应用，简单平滑
        left_limit = avail.left()
        right_limit = avail.right() - self.width() + 1
        if x < left_limit:
            x = left_limit
            self._vx = abs(self._vx)
            self.face_right()
        elif x > right_limit:
            x = right_limit
            self._vx = -abs(self._vx)
            self.face_left()
        

        # --- 垂直运动（重力+跳跃+反弹）---
        ground_y = self._ground_y()
        y = self.y()
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
                    # 若抛掷冷却结束且速度已不高，解除抛掷标记，允许随机速度接管
                    if self._friction_cooldown <= 0 and abs(self._vx) * 1000.0 / interval_ms <= self._friction_threshold_px_per_sec:
                        self._thrown_recently = False
            else:
                y = ground_y
                self._vy = 0.0
                self._remaining_bounces = 0
                self._on_ground = True
                if self._friction_cooldown <= 0 and abs(self._vx) * 1000.0 / interval_ms <= self._friction_threshold_px_per_sec:
                    self._thrown_recently = False
        else:
            self._on_ground = False

        self.move(x, y)

        # 更新空中宽限计时
        if self._air_grace_time > 0:
            self._air_grace_time -= dt

    def start_walk(self, speed_px_per_sec=120):
        # 将速度换算为每 tick 像素，保持方向
        interval_ms = max(1, self._walk_timer.interval())
        per_tick = max(1, int(speed_px_per_sec * interval_ms / 1000.0))
        self._vx = per_tick if self._vx >= 0 else -per_tick
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
        self._stick_to_ground()

    def stop_walk(self):
        # 仅停止水平移动，重力与跳跃保持可用
        self._vx = 0

    def jump(self):
        # 仅允许在地面起跳
        if self.y() >= self._ground_y() and self._vy == 0.0:
            self._vy = -self._jump_speed_px_per_sec
            self._remaining_bounces = 0
            self._on_ground = False

    # ===== 随机速度控制 =====
    def enable_random_speed(self, enabled: bool = True):
        self._random_speed_enabled = enabled
        if enabled and abs(self._vx) > 0:
            self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
            self._time_to_next_speed_change = random.uniform(*self._speed_change_interval_range)
        # 开关随机速度时不影响摩擦当前状态

    def randomize_speed_once(self):
        self._speed_target_px_per_sec = random.uniform(self._speed_min_px_per_sec, self._speed_max_px_per_sec)
        self._time_to_next_speed_change = random.uniform(*self._speed_change_interval_range)
        # 立即变化一次不影响摩擦当前状态


    # ===== 抛掷速度估计 =====
    def _estimate_throw_velocity(self):
        # 使用最近轨迹点估算平均速度
        if len(self._drag_history) < 2:
            return None, None
        x0, y0, t0 = self._drag_history[0]
        x1, y1, t1 = self._drag_history[-1]
        dt = max(1e-3, t1 - t0)
        vx_px_per_sec = (x1 - x0) / dt
        vy_px_per_sec = (y1 - y0) / (1.2*dt)
        # 将水平速度换算为每 tick 像素
        per_tick = int(abs(vx_px_per_sec) * self._walk_timer.interval() / 1000.0)
        if per_tick == 0 and abs(vx_px_per_sec) > 0:
            per_tick = 1
        vx_tick = per_tick if vx_px_per_sec >= 0 else -per_tick
        return vx_tick, vy_px_per_sec
def main():
    app = QApplication(sys.argv)
    # 示例：限制最长边 200 像素（保持等比）
    pet = DesktopPet("assets\扫地机器人.png", max_width=200, max_height=200)
    pet.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()