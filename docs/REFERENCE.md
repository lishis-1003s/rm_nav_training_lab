# RM 哨兵导航训练平台：进阶参考

面向导航新生的 Ubuntu 22.04 / ROS 2 Humble 二维导航仿真平台，不依赖 Gazebo。圆形全向底盘半径默认为 **0.30 m**，支持前后、横移、旋转；网页与 RViz2 观察同一套真实 ROS 数据，Nav2 和 SLAM Toolbox 实际运行。

推荐使用**教学模式**：学生在终端启动不同 Launch、检查 ROS、修改 YAML、保存和加载地图，网页负责观察、手动探索、障碍编辑、前后对比及实验记录。自由体验模式额外提供网页启停和保存按钮；教学模式同样支持参数命令与网页修改对照。

## 先区分运行模式

| 模式 | 启动文件 | 能做什么 |
| --- | --- | --- |
| 仅仿真 | `sim_only.launch.py` | 键盘移动、传感器与 TF；**没有 Nav2，不能自主导航** |
| 建图与导航 | `slam_nav2.launch.py` | 手动建图，等待 Nav2 就绪后可导航 |
| 已知地图导航 | `known_map.launch.py` | 在已知地图中自主到达目标，导航练习优先使用 |

已经编译时，最快验证导航的方法：先结束旧实验，再执行下面的命令。如果已经运行 `training_server` 提供网页，使用：

```bash
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch rm_nav_training_lab known_map.launch.py serve_web:=false rviz:=false
```

没有单独运行网页服务时，去掉 `serve_web:=false`，Launch 会同时提供网页。打开 http://localhost:8080，刷新页面，等待顶部显示“已知地图导航”和“导航已就绪”，然后在空白区域选点，点击“开始导航”。不要用“仅仿真”测试自主导航。

主页面以地图为中心；右侧四个页签分别为“操作、调参、课程、诊断”。课程命令和日志按需打开。导航未就绪会禁用开始按钮并给出原因；Launch 检测到网页或 ROSBridge 端口已占用时，会在启动节点前退出，避免混入多个实验。

## 1 首次安装与编译

以下命令在本机工程目录运行。换机器时将工作区路径替换为实际位置。

```bash
cd ${HOME}/rm_nav_training_lab
sudo bash scripts/install_dependencies_ubuntu2204.sh
source /opt/ros/humble/setup.bash
```

脚本要求已经安装 ROS 2 Humble，会安装 Nav2、SLAM Toolbox、RViz2、ROSBridge、TF 工具、rosbag、Python 地图读取依赖以及编译工具。也可手动安装：

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions python3-rosdep python3-pil python3-yaml \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-slam-toolbox \
  ros-humble-rviz2 ros-humble-rosbridge-suite ros-humble-tf2-tools \
  ros-humble-ros2bag ros-humble-rosbag2-storage-default-plugins
```

首次使用 rosdep 才需要 `sudo rosdep init`，已经初始化则跳过。然后运行：

```bash
# 仅首次需要，已经初始化不要重复执行
sudo rosdep init
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

更新工程后重新运行 `colcon build --symlink-install`，再重新 source 工作区并重启相关服务。

## 2 每个终端先准备环境

每打开一个终端都执行下列命令。后文终端 A、B、C 均指已完成这一步的终端。

```bash
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
```

Launch 默认也使用域 0。其他域通过 `ros_domain_id:=61` 指定，检查命令的终端也要使用相同域。训练话题不要桥接到实车域。

## 先体验定位、建图、导航

启动常驻网页服务 `ros2 run rm_nav_training_lab training_server`，访问 http://localhost:8080。默认进入自由体验；操作页提供三个可直接启动的入口。已有终端 Launch 时先在其终端按 Ctrl+C，避免重复占用 9090。

| 入口 | 运行内容 | 操作与观察 |
| --- | --- | --- |
| ① 定位 | 仿真、Map Server、AMCL；不启动导航控制器 | W/A/S/D 平移、Q/E 旋转；观察激光与墙体重合程度，用初始位姿箭头修正定位。初始位姿不瞬移底盘。 |
| ② 建图 | 仿真、SLAM Toolbox、Nav2 | 手动探索，从扫描生成地图；支持自定义障碍。地图保存使用下文的终端命令。 |
| ③ 导航 | 仿真、Map Server、AMCL、Nav2 | 拖动目标位置与朝向，点击开始导航；观察路径、代价地图及障碍避让。地图输入框可指定自己的 YAML。 |

点击体验按钮会重启实验，清除临时障碍和轨迹；网页保持打开。可用“停止实验”结束网页启动的进程。切回“教学模式 · 终端驱动”可继续命令行课程，不会自动停止当前实验。

定位体验也支持终端启动：`ros2 launch rm_nav_training_lab localization.launch.py serve_web:=false rviz:=false`。激光偏移可能来自定位误差或显示时间同步，体验入口并不保证消除偏移；应结合 RViz、TF 和定位结果判断。

## 3 推荐运行方式 教学模式

### 终端 A 启动网页服务

```bash
ros2 run rm_nav_training_lab training_server
```

这个网页服务只需运行一份。如果提示 8080 已占用，先按第 10 节检查已有进程；已有本平台服务时可直接访问网页，或在原服务终端按 Ctrl+C 后重新启动。

保持这个终端运行，打开 [http://localhost:8080](http://localhost:8080)。页面默认进入自由体验，请手动选择“教学模式 · 终端驱动”。此时不要切到自由体验并点击启动，实际实验交给终端 B。

### 终端 B 启动一个实验模式

下列三个命令**每次只运行一个**。切换前对当前 Launch 按 `Ctrl+C`，等待其退出，再运行另一条。

```bash
# 仅仿真：练习节点、话题、TF、激光与全向运动
ros2 launch rm_nav_training_lab sim_only.launch.py serve_web:=false rviz:=false

# SLAM 建图与 Nav2：通过网页手动探索，终端保存地图
ros2 launch rm_nav_training_lab slam_nav2.launch.py serve_web:=false rviz:=false

# 已知地图导航：Map Server、AMCL、Nav2
ros2 launch rm_nav_training_lab known_map.launch.py serve_web:=false rviz:=false
```

`serve_web:=false` 表示网页由终端 A 提供，避免两个 HTTP 服务争用 8080；`rviz:=false` 表示暂时不启动桌面 RViz。ROSBridge 由 Launch 启动，网页自动连接 `ws://localhost:9090`，切换实验后自动重连。

仅仿真模式没有 Nav2/SLAM，导航或保存建图相关服务不可用属于正常现象。已知地图模式保留 AMCL 作为定位基础服务，不以 AMCL 专项调参作为课程重点。

### 终端 C 检查是否正常运行

```bash
ros2 node list
ros2 topic list -t
ros2 topic info /scan --verbose
ros2 topic echo /scan --once
ros2 topic hz /scan
```

`hz` 持续运行，按 `Ctrl+C` 退出。正常时可发现 `/training_simulator`、`/training_bridge`，接收到 `/scan`、`/odom` 和 TF；网页出现地图、圆形机器人及激光。导航模式还应出现规划、控制、地图等节点，启动日志提示导航生命周期节点已激活。仅连接 WebSocket 不代表全部节点就绪。

网页管理器“未运行实验”的提示只针对它自己管理的子进程；终端 B 启动的实验应以实际 ROS 节点、话题和图层为准。

### 可选终端 D 打开 RViz 对照

```bash
rviz2 -d ${HOME}/rm_nav_training_lab/src/rm_nav_training_lab/config/training.rviz
```

也可在终端 B 的 Launch 命令中改成 `rviz:=true`，让 RViz 随实验启动。

### 停止与切换

- 先取消导航目标，停止手动输入；对终端 B 按 `Ctrl+C` 停止实验。切换模式时保持终端 A 运行。
- 全部结束时，再对终端 A 按 `Ctrl+C`；独立启动的 RViz 另行关闭。
- 如果实验此前由网页启动，应先切到自由体验点击“停止实验”，再使用终端 B。切换教学/自由体验只是改变界面，不会停止进程。

## 4 网页如何使用

1. 在“课程”页签选择关卡。前 3 关显示完整命令，中间 3 关先显示提示，后 3 关要求独立完成；“查看命令参考”只展示文本，不会代替学生执行。
2. 地图展示真实地图、TF 位姿和激光；图层可开启全局路径、局部轨迹、全局/局部 Costmap。在“诊断”页签可展开 Node List、Topic List、类型和发布/订阅数量，并查看 ROS 日志。
3. 手动探索使用 **W/S 前后、A/D 左右平移、Q/E 旋转**，支持组合按键和按住屏幕按钮。松开、失焦或隐藏页面会停止。输入框获得焦点时不接管键盘。手动控制前先取消导航，避免松手后恢复未完成的导航任务。
4. 障碍工具选择“添加圆形障碍”，设置半径后点击地图；选择“删除最近障碍”再点击，或清空全部。障碍真实影响激光和圆形底盘碰撞，SLAM/Costmap 根据传感器数据更新。
5. 导航模式选择“导航目标”，在可达位置按下并拖动箭头设置目标朝向，再点击“发送 Nav2 目标”。勾选“松手直接导航”可连续操作；短点击沿用当前机器人朝向。观察路径、局部轨迹、速度、Action 反馈；“取消导航”用于取消网页网关发出的目标。
6. “调参”页签提供节点当前值、滑块和数值输入、动态应用按钮，以及随输入值更新的 CLI 命令。教学模式也可网页调参，鼓励与终端命令对照；记录调整前后画布、参数、路径长度和速度，并用紫线叠加调整前路径。
7. 在实验记录中填写实际命令、原始终端输出、现象与诊断分析，保存后导出 JSON。截图、地图、配置和 bag 文件另外保存到提交目录，由教师人工验收，不自动评分。

网页手动命令使用 `/cmd_vel_explore`，Nav2 使用 `/cmd_vel`，两者可以检查区分；仿真器对新鲜的手动输入优先响应。实验记录保存在当前浏览器本机，清除浏览器数据前先导出。

### 激光显示的时间同步

局部代价地图（odom 坐标系）按自身 `header.stamp` 查询 map→odom，不再随最新定位修正重投影旧地图；二维和三维视图采用同一规则。

默认 AMCL 配置针对无噪声二维仿真，采用较小运动噪声与初始协方差；该配置不是实车推荐参数。启用里程计故障或错误初始位姿时，仍会出现真实定位偏差，不使用仿真真值替换定位。

网页按 `/scan.header.stamp` 查询历史 TF，将每帧激光固定在采集时的地图坐标；等待所需 TF 到达后再显示，不使用最新底盘位姿重投影旧扫描。TF 缺失时不外推，超过一秒未更新的激光隐藏。该处理修复网页显示不同步，不会掩盖 AMCL/SLAM 定位跳变、TF 故障或真实传感器畸变。

更新后使用 Ctrl+Shift+R 强制刷新网页，避免浏览器沿用旧脚本。

### 轻量三维视图

默认使用可旋转的正交三维视图；点击“切换二维”返回原来的俯视图。三维视图右键拖动旋转与改变俯仰，Shift + 左键或中键平移，滚轮围绕光标缩放。目标、初始位姿和障碍工具仍在地图地面坐标中工作。全屏底部提供视图切换、发送目标、取消导航和退出按钮。

场景由真实 OccupancyGrid 生成墙体示意，圆形底盘、ROS 全局/局部路径、蓝色/深蓝色代价地图及时间同步的扫描点共用 map 坐标。墙高仅为示意，不是赛场实测高程；LaserScan 仍是一层二维扫描，当前没有 PointCloud2、三维 SLAM 或三维碰撞仿真。采用本地 Canvas 正交投影，无 CDN、WebGL 框架、Gazebo 或额外 ROS 依赖。

### 地图交互与真实导航对照

- 滚轮以鼠标位置为中心缩放；二维视图中键、右键或 Shift + 左键拖动平移（三维右键用于旋转），也可选择“浏览地图”。“适应地图”恢复全图，“跟随机器人”保持底盘居中，“全屏”扩大操作空间。
- “导航目标”拖动指定位置和朝向，发送真实 Nav2 Action。页面显示真实剩余距离、预计时间和恢复次数；机器人轨迹来自 TF 实际位姿，规划路径来自 ROS 路径话题。
- “初始位姿”在定位体验或已知地图导航模式使用，拖动后发布 `/initialpose`，供 AMCL 修正定位；它不会移动仿真机器人。定位正确时不必反复设置。
- “移动障碍”拖动已有橙色圆形障碍，松手后更新仿真场景。激光和代价地图随后更新；静态地图中的墙体需通过更换地图修改。SLAM 探索仍使用键盘控制前后、横移和旋转。
- 全局代价地图为蓝色，局部代价地图为深蓝色。调参页面保留当前值回读、动态修改命令、网页应用、调整前后对比和默认值恢复。

设计参考 [pb2025_sentry_nav](https://github.com/SMBU-PolarBear-Robotics-Team/pb2025_sentry_nav) 的仿真/实车配置分离、Nav2 数据链路以及 RViz 目标、初始位姿、路径和代价地图工具。网页交互为本项目实现，保留 Humble 的真实 Nav2/SLAM 接口；不引入该项目的 Point-LIO、small_gicp、三维地形和点云处理链，以维持二维教学的轻量运行。当前仍使用本项目的全向 DWB 控制配置，并未移植其控制器。二维射线和运动模型不能替代实车传感器、底盘动力学或三维地形验证。

## 5 命令行建图与保存地图

先按第 3 节启动 SLAM 模式，用网页键盘探索，确认 `/map` 已发布。在终端 C 执行：

```bash
ros2 topic echo /map --once --field info
mkdir -p ~/rm_training_maps
ros2 run nav2_map_server map_saver_cli \
  -f ~/rm_training_maps/slam_01 \
  --ros-args -p map_subscribe_transient_local:=true
ls -lh ~/rm_training_maps/slam_01.*
cat ~/rm_training_maps/slam_01.yaml
```

`-f` 是不带扩展名的文件前缀；正常生成 `slam_01.pgm` 和 `slam_01.yaml`。检查终端成功日志及两个实际文件，并理解 YAML 的 `image`、`resolution`、`origin`。不要仅凭网页已有地图判断保存成功；再次使用同一前缀会覆盖自己的同名文件。

本阶段保存占据栅格图片与 YAML，不包含 SLAM 位姿图序列化和恢复继续建图。

## 6 加载自己的地图导航

先在终端 B 对 SLAM Launch 按 `Ctrl+C`，再运行：

```bash
ros2 launch rm_nav_training_lab known_map.launch.py \
  serve_web:=false rviz:=false \
  map:=$HOME/rm_training_maps/slam_01.yaml
```

也可以替换为其他地图 YAML 的绝对路径。加载时，仿真激光/碰撞世界与导航共同读取这份地图，机器人自动选择能容纳底盘的出生点，AMCL 初始位置同步设置。重新加载 SLAM 栅格不是恢复原始物理世界和 SLAM 状态。

当前支持 trinary 地图、P2/P5 PGM 或 PNG 图片，读取分辨率、原点、反色与阈值；要求 `origin` 的 yaw 为 0，未知格按不可通行处理。移动 YAML 时同时保留其引用的图片，注意相对图片路径。

默认地图为官方 **2026 RMUL 3V3 V1.0.0 STEP 的二维截面**，分辨率 0.05 m，范围 12.6 × 8.6 m；高台和坡道截面作为障碍，不模拟爬坡，也不是后续规则修订的实地测绘图。来源和转换方法见 [地图说明](../src/rm_nav_training_lab/maps/SOURCES.md)。原教学地图可这样选择：

```bash
ros2 launch rm_nav_training_lab known_map.launch.py \
  serve_web:=false rviz:=false \
  map:=${HOME}/rm_nav_training_lab/src/rm_nav_training_lab/maps/training_map.yaml
```

## 7 参数检查与修改 YAML

导航运行时，在终端 C 先记录参数基线，再修改膨胀参数并读回：

```bash
mkdir -p ~/rm_training_evidence ~/rm_training_configs
ros2 param list /global_costmap/global_costmap
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param set /global_costmap/global_costmap inflation_layer.inflation_radius 0.7
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param dump /global_costmap/global_costmap > ~/rm_training_evidence/global_costmap.yaml
```

打开网页 Costmap 图层，记录同一目标、同一障碍布局下的变化。实时参数设置在重启后可能被配置文件覆盖；单节点 dump 也不等于完整 Nav2 参数文件。

学习持久配置时，复制完整基线 YAML 再编辑：

```bash
cp "$(ros2 pkg prefix --share rm_nav_training_lab)/config/nav2_params.yaml" \
  ~/rm_training_configs/nav2_experiment.yaml
nano ~/rm_training_configs/nav2_experiment.yaml
```

例如修改全局/局部 `inflation_layer.inflation_radius`，或 `controller_server` 下 `FollowPath.max_vel_x`、`max_vel_y`、`max_speed_xy`。速度上限还受到 `velocity_smoother` 配置约束，需要理解整条链路。保存 YAML，结束旧 Launch，再用终端 B 启动：

```bash
ros2 launch rm_nav_training_lab known_map.launch.py \
  serve_web:=false rviz:=false \
  map:=$HOME/rm_training_maps/slam_01.yaml \
  params_file:=$HOME/rm_training_configs/nav2_experiment.yaml
```

DWB 速度、加速度、目标容差以及 NavFn 规划容差支持动态修改。DWB 的 PathDist/GoalDist 评分权重需要重新配置控制器，网页要求勾选重载选项；CLI 参考中提供取消目标、暂停导航、cleanup、写参数、configure、恢复的逐条命令。参数回读成功不等于轨迹效果已经改变，仍需观察实际图层和运动。恢复基线时去掉 `params_file` 参数重启；地图路径保持相同便于对比。

底盘半径统一通过 Launch 参数配置，例如 `robot_radius:=0.3`，它会同步到仿真器与两个 Costmap；单独修改 YAML 中的 `robot_radius` 会被该 Launch 参数覆盖。

## 8 TF Action 日志与 rosbag

在终端 C 或更多独立终端运行，持续命令用 `Ctrl+C` 退出：

```bash
ros2 run tf2_ros tf2_echo map base_link
ros2 run tf2_ros tf2_echo base_link laser_frame
mkdir -p ~/rm_training_evidence
cd ~/rm_training_evidence
ros2 run tf2_tools view_frames
ros2 action list -t
ros2 action info /navigate_to_pose
ros2 interface show nav2_msgs/action/NavigateToPose
ros2 topic echo /rosout
ros2 topic echo /behavior_tree_log
```

需要练习 CLI 发送目标时，将下面示例坐标替换成当前地图的可达坐标：

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: -5.0, y: -3.0}, orientation: {w: 1.0}}}}" \
  --feedback
```

CLI 直接发送的目标不经过网页网关，其反馈与结果以终端为准，网页网关的专属状态和取消按钮不能代替对该目标的管理。

录制时使用新的输出目录名，启动录制后产生一次实际导航或故障现象，再 `Ctrl+C` 结束：

```bash
ros2 bag record -o ~/rm_training_evidence/nav_run_01 \
  /map /scan /odom /tf /tf_static /plan /local_plan /cmd_vel \
  /training/sim_cmd_vel /rosout /behavior_tree_log
ros2 bag info ~/rm_training_evidence/nav_run_01
```

回放用隔离域 43，避免与在线实验域 0 混合：

```bash
ROS_DOMAIN_ID=43 ros2 bag play ~/rm_training_evidence/nav_run_01 --loop
# 在另一个已经 source 的终端检查回放
ROS_DOMAIN_ID=43 ros2 topic echo /odom --once
```

回放后按 `Ctrl+C` 停止。回放只是重发已录消息，不会重新运行导航算法；网页默认仍连接在线实验域 0，不会自动切到回放域。

## 9 自由体验模式与独立 Launch

自由体验：终端 A 启动 `training_server`，网页选择“自由体验 · 网页控制”，设置模式、地图和半径后点击“启动 / 切换”。此时不要另开终端 B 启动相同实验。管理器只控制自己创建的进程组，日志保存在其运行目录的 `training_runtime.log`。

自由体验提供参数应用、教学参数恢复默认值和网页保存地图。动态参数直接应用，不取消导航；需要重载的评分权重会取消全部导航目标，经生命周期管理器暂停、重新配置控制器、恢复后，需要重新发送目标。

如果不需要常驻网页管理器，也可以只执行：

```bash
ros2 launch rm_nav_training_lab sim_only.launch.py rviz:=false
# 或 known_map.launch.py、slam_nav2.launch.py，每次只运行一个
```

默认 `serve_web:=true`，Launch 会同时启动静态网页服务。此方式不要再启动 `training_server`；静态网页支持观察和 ROS 交互，但不支持自由体验的网页启停 API。也可从工程根目录使用 `./scripts/run_training.sh sim`、`known_map` 或 `slam`，该脚本走独立 Launch 方式。

## 10 常见问题

| 现象 | 检查与处理 |
| --- | --- |
| 找不到包或可执行程序 | 确认在工作区编译成功，并在当前终端 source ROS 和 `install/setup.bash`。 |
| 8080 或 9090 已被占用、出现重复节点 | 先用 `ss -ltnp 'sport = :8080'` 检查进程；已有网页服务时直接访问，重启则在原终端按 Ctrl+C。检查是否同时启动了网页管理的实验与终端 Launch；先停止旧实验。终端 A 供网页时，终端 B 使用 `serve_web:=false`。 |
| 网页连接成功但没有地图/机器人 | 检查当前模式、节点、`/scan`、`/map` 和 TF；SLAM 需等待首次扫描和建图；不要仅根据 WebSocket 状态判断就绪。 |
| Node not found 或终端看不到节点 | 核对环境、域 ID、节点全名和 Launch 是否运行；等待图发现，使用下方直接发现命令核对。 |
| 参数值变化但运动无变化 | 检查参数是否属于实际运行的控制器、是否被其他限速环节约束；修改 YAML 后重启，并读回验证。 |
| 键盘不控制机器人 | 点击页面非输入区域，确认 ROSBridge 已连接；取消导航；检查故障中是否开启底盘卡死。 |
| 保存地图失败 | 确认 SLAM 已发布 `/map`、目录可写，检查 CLI 成功日志及图片/YAML 文件；不要误用仅仿真作为 SLAM 建图。 |
| 自己的地图加载失败 | 检查 YAML、图片路径、分辨率、阈值、origin yaw，以及是否有足够空间容纳底盘。 |
| RViz 无法打开 | 使用图形桌面，或通过 `rviz:=false` 关闭 RViz 先用网页；独立 RViz 终端保持域 ID 一致。 |

节点发现排查示例：

```bash
ros2 node list --no-daemon --spin-time 5
ros2 param dump /global_costmap/global_costmap --no-daemon --spin-time 5 \
  > ~/rm_training_evidence/global_costmap.yaml
```

若守护进程视图与直接发现不同，在同域终端运行 `ros2 daemon stop`、`ros2 daemon start` 后重新检查。记录失败和恢复证据，不要仅凭一次发现失败断定节点崩溃。

## 11 课程提交与验证范围

九关完整任务、逐步减少提示的命令参考和人工验收要求见 [命令行课程](../src/rm_nav_training_lab/lessons/lesson_guide.md)。提交实际命令、原始输出、截图、地图图片/YAML、修改后的完整参数 YAML、bag 目录与 `bag info`、诊断分析，以及网页导出的 JSON。

已实际验证构建、三种模式启动、真实 Nav2 目标成功、全局/局部路径、SLAM 横移和保存、CLI 地图保存与参数导出、地图重新解析、圆形碰撞回归测试和教学/自由体验界面切换。长时间运行、全部参数效果、复杂故障组合及 RViz 与网页逐帧对照仍需教学现场验收。仿真是二维运动与射线模型，不替代实车动力学验证。

几何回归测试：

```bash
python3 -m unittest discover -s tests -v
```


## 12 Costmap 配色与直观调参

全局代价地图为蓝色 `#3b82f6`，局部代价地图为深蓝色 `#123f91`，按真实代价值显示透明度梯度；自由和未知栅格不着色。局部图层按消息坐标系、原点和 TF 变换绘制，不能通过修改浏览器图像代替 ROS Costmap 更新。

在“调参”页签：先读取实际值，再拖动滑块或输入数值，检查对应命令和观察方法，点击“动态应用”。拖动本身不发送请求。应用时校验范围，等待真实 SetParameters 响应并 GetParameters 回读；膨胀参数应用后自动打开对应图层。选择评分权重时显示“需重载控制器”，需勾选重载选项才能执行。恢复全部教学参数也需要该选项。命令行使用实际连接实例发布的 ROS 域 ID；尚未取得实例信息时显示默认域 0，执行前需核对。

运行时参数不会自动保存回 Launch 的 YAML，参数 dump 只包含单节点；需要持久配置时修改完整 YAML 再通过 params_file 加载。速度效果受 DWB 各方向上下限、合速度限制和 velocity_smoother 共同约束；网页滑块的默认范围配合本工程基线，若要放大运动范围应同时核对完整配置。二维仿真不模拟电机动力学。

Humble 参数分类参考上游实现：[DWB 运动学动态参数](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_dwb_controller/dwb_plugins/src/kinematic_parameters.cpp)、[目标检查器](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_controller/plugins/simple_goal_checker.cpp)、[NavFn](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_navfn_planner/src/navfn_planner.cpp)、[DWB 评分权重初始化](https://raw.githubusercontent.com/ros-navigation/navigation2/humble/nav2_dwb_controller/dwb_core/include/dwb_core/trajectory_critic.hpp)。不同安装版本或替换插件后，需重新核实其动态行为。


最新可重复对比流程和速度缓存处理说明见[可视化导航参数实验](PARAMETER_LAB.md)。
