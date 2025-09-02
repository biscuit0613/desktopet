# 桌宠项目 - DesktopPet

一个基于PyQt5开发的互动桌面宠物应用，具有物理运动、丰富的交互行为和自定义状态等功能。

## 功能特性

- **物理运动系统**：支持重力、碰撞、反弹等物理效果
- **交互行为**：响应鼠标点击、拖动、抛掷等操作
- **对话框系统**：显示不同状态的对话气泡，支持打字效果
- **睡眠系统**：宠物会在空闲时进入睡眠状态
- **点击计数**：内置点击次数统计功能，达到100次后自动重置
- **速度控制**：自动调整移动速度，支持刹车状态
- **状态记忆**：关闭程序后会记住最后设置的桌宠大小

## 安装与运行

### 环境要求
- Python 3.6+ 
- PyQt5

### 安装依赖

```bash
pip install PyQt5
```

或者使用项目根目录下的requirements.txt：

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python main.py
```

## 使用指南

### 基本操作

- **拖动**：按住鼠标左键拖动桌宠
- **抛掷**：拖动后快速释放，桌宠会根据抛掷速度移动
- **右键菜单**：右键点击桌宠显示菜单，可进行缩放、重置等操作
- **自动运动**：桌宠会随机移动并与屏幕边界交互
- **点击交互**：点击桌宠会触发互动效果和对话气泡

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
├── dialogs.json      # 对话内容配置文件
├── pic_asset.json    # 图像资源配置文件
├── assets/           # 图像资源文件夹
└── util.py           # 工具函数
```

## 核心组件详解

### 1. 主宠物类 (DesktopPet)

`DesktopPet`是整个桌宠的核心类，负责整合其他所有组件并管理整体运行逻辑。

**关键功能**：
- 窗口属性设置（无边框、置顶、透明背景等）
- 组件初始化与整合
- 设置管理（保存和加载）
- 空闲时间跟踪与睡眠状态管理
- 点击计数与交互处理

**主要变量**：
- `_scale_factor`: 缩放比例因子
- `_walk_timer`: 控制物理系统更新的定时器（~60 FPS）
- `idle_tracker`: 空闲时间跟踪器
- `total_click_count`: 总点击次数计数器

### 2. 物理系统 (PhysicsSystem)

`PhysicsSystem`负责模拟桌宠的物理行为，包括位置计算、重力、碰撞检测等。

**关键功能**：
- 位置和速度计算
- 重力模拟
- 地面检测与碰撞响应
- 跳跃动作实现

**主要变量**：
- `_vx`, `_vy`: 水平和垂直速度
- `_gravity_px_per_sec2`: 重力加速度
- `_jump_speed_px_per_sec`: 跳跃初速度
- `_on_ground`: 是否在地面上的标志

### 3. 速度控制 (SpeedController)

`SpeedController`负责管理桌宠的移动速度，包括随机行走和摩擦减速等功能。

**关键功能**：
- 随机行走方向控制
- 速度限制与调节
- 摩擦减速模拟

**主要变量**：
- `_walk_speed`: 行走速度
- `_max_walk_speed`: 最大行走速度
- `_friction_coefficient`: 摩擦系数

### 4. 渲染系统 (Renderer)

`Renderer`负责加载和显示图像，处理图像的方向、缩放等视觉效果。

**关键功能**：
- 图像资源加载
- 图像缩放与方向控制
- 状态图像切换

**主要变量**：
- `_asset_path`: 当前加载的图像路径
- `_pixmap`: 当前显示的图像数据
- `_states`: 状态名称到图像路径的映射字典

### 5. 行为控制 (BehaviorController)

`BehaviorController`负责处理用户交互事件，如鼠标点击、拖动等。

**关键功能**：
- 鼠标事件处理
- 拖拽逻辑实现
- 右键菜单管理

**主要变量**：
- `_is_dragging`: 是否正在被拖动
- `_context_menu`: 右键菜单对象

### 6. 对话框管理 (DialogManager)

`DialogManager`负责显示和管理桌宠的对话框，包括不同状态下的对话内容。

**关键功能**：
- 对话内容加载与管理
- 气泡显示与自动关闭
- 打字效果实现
- 自动触发对话
- 特定状态对话（睡眠、跳跃等）

**主要变量**：
- `dialogues`: 普通对话内容
- `dialogues_move`: 移动相关对话内容
- `auto_trigger_enabled`: 是否启用自动触发

## 配置文件

### 1. 应用设置

桌宠的配置文件保存在用户目录下的`.desktopet`文件夹中：

- Windows: `C:\Users\用户名\.desktopet\settings.json`
- macOS/Linux: `/home/用户名/.desktopet/settings.json`

当前配置文件主要存储桌宠的缩放比例设置。

### 2. 图像资源配置 (pic_asset.json)

定义了不同状态下使用的图像资源路径：

```json
{
  "states": {
    "default": "assets/扫地机器人.png",
    "shache": "assets/brake.png",
    "dash": "assets/dash.png",
    "breath": "assets/breath.png",
    "hug": "assets/hug.png",
    "drink": "assets/drink.png",
    "sleep": "assets/sleep.png",
    "sleep2": "assets/sleep2.png",
    "lift": "assets/lift.png",
    "lift2": "assets/lift2.png",
    "paperfly": "assets/paperfly.png"
  },
  "default_asset": "assets/扫地机器人.png"
}
```

### 3. 对话内容配置 (dialogs.json)

定义了不同状态下的对话内容。

## 打包成应用程序

### 1. 安装PyInstaller

```bash
pip install pyinstaller
```

### 2. 打包命令

在项目根目录下执行以下命令：

```bash
pyinstaller --onefile --windowed --icon=assets/扫地机器人.ico --name=桌面宠物 main.py
```

**参数说明**：
- `--onefile`: 生成单个可执行文件
- `--windowed`: 不显示控制台窗口
- `--icon`: 设置应用图标（可选）
- `--name`: 设置应用名称

### 3. 打包结果

打包成功后，可执行文件会在`dist`目录下生成。

## 常见问题与解决方案

### 中文显示问题

程序已在main.py中设置了中文字体支持，确保中文能正常显示：

```python
# 设置应用程序属性，确保中文正常显示
font = app.font()
font.setFamily("SimHei")
app.setFont(font)
```

### 资源文件缺失

确保打包时包含了所有必要的资源文件，特别是assets文件夹下的图像文件。

## 开发指南

### 添加新功能

#### 1. 添加新状态图像

修改`pic_asset.json`文件，添加新的状态和对应的图像路径，然后在代码中调用：

```python
self.renderer._switch_to_state_image("new_state")
```

#### 2. 添加新的对话内容

修改`dialogs.json`文件，添加新的对话类型和内容。

#### 3. 修改物理参数

可以通过调整`PhysicsSystem`类中的物理参数来改变桌宠的运动特性。

## 更新日志

- 添加了点击计数功能，自动统计点击次数并在达到100次后重置
- 优化了睡眠系统，空闲40秒后有30%概率进入睡眠状态
- 改进了对话系统，支持跳跃、睡眠等特定状态的对话显示
- 修复了双击拎起功能
- 优化了物理运动效果

## License

[MIT License](https://opensource.org/licenses/MIT)
