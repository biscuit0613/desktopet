# 桌宠项目 - DesktopPet

一个基于PyQt5开发的桌面宠物应用，具有物理运动、交互行为和自定义状态等功能。

## 功能特性

- **物理运动系统**：支持重力、碰撞、反弹等物理效果
- **交互行为**：响应鼠标点击、拖动、抛掷等操作
- **对话框系统**：显示不同状态的对话气泡

## 使用指南

### 基本操作

- **拖动**：按住鼠标左键拖动桌宠
- **抛掷**：拖动后快速释放，桌宠会根据抛掷速度移动
- **右键菜单**：右键点击桌宠显示菜单，可进行缩放、重置等操作
- **自动运动**：桌宠会随机移动并与屏幕边界交互
- **速度状态**：当桌宠移动速度超过200像素/秒时，会减速
- **记忆大小**：关闭程序后会记住最后设置的桌宠大小

### 项目结构

桌宠项目采用模块化设计，各功能组件分离在不同的文件中：

```
desktopet/
├── main.py           # 应用入口
├── pet.py            # 主宠物类，整合所有组件
├── physics.py        # 物理系统，处理位置和运动
├── speed_control.py  # 速度控制系统
├── renderer.py       # 渲染系统，处理图像显示
├── behavior.py       # 行为控制系统，处理用户交互
├── dialog.py         # 对话框管理系统
└── assets/           # 图像资源文件夹
```

### 核心组件详解

#### 1. 主宠物类 (DesktopPet)

`DesktopPet`是整个桌宠的核心类，负责整合其他所有组件并管理整体运行逻辑。

**关键变量**：

- `screen()`: 当前窗口所在的屏幕
- `size()`: 桌宠窗口的大小
- `width()`, `height()`: 桌宠窗口的宽度和高度
- `x()`, `y()`: 桌宠窗口的当前位置坐标
- `_scale_factor`: 缩放比例因子
- `_walk_timer`: 控制物理系统更新的定时器（~60 FPS）

#### 2. 物理系统 (PhysicsSystem)

`PhysicsSystem`负责模拟桌宠的物理行为，包括位置计算、重力、碰撞检测等。

**关键变量**：

- `_vx`: 水平速度（像素/帧）
- `_vy`: 垂直速度（像素/秒）
- `_gravity_px_per_sec2`: 重力加速度（像素/秒²）
- `_jump_speed_px_per_sec`: 跳跃初速度（像素/秒）
- `_on_ground`: 是否在地面上的标志
- `_air_grace_time`: 空中宽限时间（抛掷后短暂忽略地面碰撞）

#### 3. 速度控制 (SpeedController)

`SpeedController`负责管理桌宠的移动速度，包括随机行走和摩擦减速等功能。

**关键变量**：

- `_walk_speed`: 行走速度（像素/帧）
- `_max_walk_speed`: 最大行走速度
- `_friction_threshold`: 摩擦生效的速度阈值
- `_friction_coefficient`: 摩擦系数
- `_is_in_friction_mode`: 是否处于摩擦减速模式

#### 4. 渲染系统 (Renderer)

`Renderer`负责加载和显示图像，处理图像的方向、缩放等视觉效果。

**关键变量**：

- `_asset_path`: 当前加载的图像路径
- `_pixmap`: 当前显示的图像数据
- `_current_state`: 当前图像状态（如"default"或"shache"）
- `_states`: 状态名称到图像路径的映射字典

#### 5. 行为控制 (BehaviorController)

`BehaviorController`负责处理用户交互事件，如鼠标点击、拖动等。

**关键变量**：

- `_is_dragging`: 是否正在被拖动
- `_drag_start_pos`: 拖动开始的鼠标位置
- `_context_menu`: 右键菜单对象

#### 6. 对话框管理 (DialogManager)

`DialogManager`负责显示和管理桌宠的对话框，包括不同状态下的对话内容。

**关键变量**：

- `_dialog_label`: 显示对话的标签组件
- `_dialog_timer`: 控制对话框显示时间的定时器
- `_dialog_messages`: 不同状态的对话内容映射字典
- `_current_dialog_state`: 当前对话框状态

### 核心流程说明

#### 1. 初始化流程

桌宠的初始化在`DesktopPet`类的`__init__`方法中完成，主要步骤如下：

1. 设置窗口属性（无边框、置顶、透明背景等）
2. 初始化各个组件（渲染器、物理系统、速度控制等）
3. 加载保存的设置（如缩放比例）
4. 配置定时器用于更新物理状态
5. 设置初始位置（随机）
6. 应用加载的缩放比例
7. 启动物理系统

#### 2. 更新循环

桌宠的主要更新逻辑在`_on_walk_tick`方法中，以60 FPS执行：

1. 计算时间步长（delta time）
2. 更新速度控制
3. 检查是否正在拖拽，如果是则跳过物理更新
4. 检查速度并切换刹车图像状态
5. 更新物理状态（位置、速度等）

### 关键概念解释

#### 屏幕坐标系

桌宠使用Qt的屏幕坐标系，特点是：

- 原点(0,0)位于屏幕左上角
- X轴向右为正
- Y轴向下为正
- 物理系统的计算基于此坐标系

#### 可用区域

桌宠的活动范围受限于屏幕的可用工作区（不包括任务栏等系统UI），通过`_available_rect`方法获取。

#### 地面检测

桌宠会自动检测"地面"（通常是屏幕底部减去自身高度），并在接触地面时停止或反弹，通过`_ground_y`方法计算地面位置。

#### 状态管理

桌宠的图像状态通过`_switch_to_state_image`方法进行管理，常见状态包括：

- `default`: 默认图像
- `shache`: 刹车状态图像

### 常见功能实现

#### 1. 添加新状态图像

要添加新的状态图像，需要修改`Renderer`类中的`_states`字典：

```python
# 在renderer.py中添加新状态
def __init__(self, parent_widget, asset_path=None, max_width=None, max_height=None):
    # ... 现有代码 ...
    self._states = {
        "default": "assets/default.gif",  # 默认状态
        "shache": "assets/shache.png",   # 刹车状态
        "new_state": "assets/new_state.png"  # 新增状态
    }
    # ... 现有代码 ...
```

然后在需要的地方调用：

```python
self.renderer._switch_to_state_image("new_state")
```

#### 2. 添加新的对话内容

要添加新的对话内容，需要修改`DialogManager`类中的`_dialog_messages`字典：

```python
# 在dialog.py中添加新对话
self._dialog_messages = {
    # ... 现有对话 ...
    "new_mood": ["新对话1", "新对话2", "新对话3"]
}
```

#### 3. 修改物理参数

可以通过调整`PhysicsSystem`类中的物理参数来改变桌宠的运动特性：

```python
# 在physics.py中修改物理参数
def __init__(self, pet):
    # ... 现有代码 ...
    self._gravity_px_per_sec2 = 1500.0  # 减小重力
    self._bounce_restitution_range = (0.4, 0.7)  # 增加弹性
    # ... 现有代码 ...
```

## 配置文件

桌宠的配置文件保存在用户目录下的`.desktopet`文件夹中：

- Windows: `C:\Users\用户名\.desktopet\settings.json`
- macOS/Linux: `/home/用户名/.desktopet/settings.json`

当前配置文件主要存储桌宠的缩放比例设置。
