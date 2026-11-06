# 哨兵导航训练平台

用网页体验机器人的**定位、建图与导航**，再学习用 ROS 2 命令行完成同样的工作。

平台运行于 **Ubuntu 22.04 + ROS 2 Humble**，不依赖 Gazebo。机器人为半径 **0.30 m** 的圆形全向底盘，可以前后、左右平移和原地旋转。Nav2、AMCL、SLAM Toolbox 均实际运行，网页显示真实 ROS 数据。

第一次使用建议按顺序完成：**启动网页 → 定位体验 → 建图并保存 → 加载地图导航 → 命令行检查与调参**。

从源码包在新目录部署，请先阅读 [DEPLOY.md](DEPLOY.md)。编译与启动脚本会自动识别工作区位置。

## 1. 首次安装与编译

打开终端（Ubuntu 通常用 `Ctrl+Alt+T`）。以下示例假设工程位于 `${HOME}/rm_nav_training_lab`；换电脑后将该路径替换为实际工程目录。

请参考 DEPLOY.MD，完成DEPLOY.MD所有步骤再进行。
请参考 DEPLOY.MD，完成DEPLOY.MD所有步骤再进行。
请参考 DEPLOY.MD，完成DEPLOY.MD所有步骤再进行。

安装脚本会通过 `sudo` 请求系统密码；输入密码时终端不显示字符是正常现象。编译结束应显示 `1 package finished`，且没有失败包。

如果提示 `/opt/ros/humble/setup.bash` 不存在，先安装 ROS 2 Humble；如果 `cd` 失败，先核对工程路径。


## 2. 命令行启动：两个终端各做一件事

### 终端 A：启动网页服务

```bash
cd ~/rm_nav_training_lab
source install/setup.bash
ros2 run rm_nav_training_lab training_server
```

保持终端 A 运行，在同一台 Ubuntu 的浏览器打开 http://localhost:8080/ 。尽量不要在vscode终端直接点击，请用复制网址在浏览器打开。网页使用方式改为“教学模式 · 终端驱动”。暂时不要点击体验模式的网页启动按钮。

### 终端 B：启动导航实验

新终端也要重新加载环境。以下命令使用新增的入门地图和半径 0.30 m 的底盘：
下面的命令含义：进入工作空间目录；加载环境；启动导航
```bash
cd ~/rm_nav_training_lab
source install/setup.bash
ros2 launch rm_nav_training_lab known_map.launch.py \
  serve_web:=false rviz:=false \
  map:="$(ros2 pkg prefix --share rm_nav_training_lab)/maps/beginner_arena.yaml"
```

serve_web:=false 表示网页已由终端 A 提供，避免重复占用 8080；rviz:=false 表示暂不打开 RViz。两个终端的域 ID 必须一致。

### 切换建图模式

在终端 B 按 Ctrl+C 停止旧实验，等待退出后，再选下面一条执行。每次只运行一个实验，终端 A 保持运行。


# 建图：键盘探索，随后在另一终端使用 map_saver_cli 保存地图
```bash
ros2 launch rm_nav_training_lab slam_nav2.launch.py \
  serve_web:=false rviz:=false \
  map:="$(ros2 pkg prefix --share rm_nav_training_lab)/maps/beginner_arena.yaml"
```

若要体验网页启停，先停止终端 B 的实验，再切换网页“自由体验”并点击体验按钮。网页启动和终端 Launch 不要同时使用。

VS Code Simple Browser 使用同一个 HTTP 地址，不要直接预览 HTML 或使用 Live Server。更新后可用 Ctrl+Shift+R 强制刷新。

## 在终端保存自己建立的地图 默认保存在/maps目录

保持**建图模式**运行，停止手动运动。在终端 C 执行：

```bash

ros2 topic echo /map --once --field info

cd ~/rm_nav_training_lab/src/rm_nav_training_lab/maps

ros2 run nav2_map_server map_saver_cli \
  -f slam_01 

```

确认终端报告成功，且文件夹中存在 `slam_01.pgm` 和 `slam_01.yaml`。YAML 记录图片位置、每格尺寸 `resolution` 和地图原点 `origin`。图片与 YAML 必须一起保留；同名保存会覆盖旧文件。

这里保存的是栅格地图，不包含继续建图所需的 SLAM 位姿图状态。

## 加载自己的地图导航
由终端 B 启动，先按 `Ctrl+C` 停止旧实验，再执行：

```bash
ros2 launch rm_nav_training_lab known_map.launch.py \
  serve_web:=false rviz:=false \
  map:=地图路径
```
例如：/home/rm/rm_nav_training_lab/src/rm_nav_training_lab/maps/rmul2026_3v3.yaml
加载的地图同时用于导航和仿真的激光／碰撞环境，机器人会选择可容纳底盘的出生位置。支持 trinary 地图、PGM 或 PNG 图片，要求地图 `origin` 的 yaw 为 0。未知区域按不可通行处理。


## 参数调整与路径对比实验

新增地图已作为默认体验配置保存在 `src/rm_nav_training_lab/config/experience_defaults.yaml`

按顺序练习：全局代价地图 → 局部代价地图 → 放置障碍 → 运动途中移动障碍 → 速度对比 → 路径跟随权重。一次只改变一个因素。

**完整步骤、参数含义和建议对比值见[可视化导航参数实验](docs/PARAMETER_LAB.md)。**

## 5. 学会检查 ROS 是否正常

在终端 C 执行下面的命令，每条先观察结果再执行下一条：

```bash
# 看有哪些节点
ros2 node list

# 看有哪些话题及其消息类型
ros2 topic list -t

# 看激光话题的发布者、订阅者和通信配置
ros2 topic info /scan --verbose

# 只读一条消息
ros2 topic echo /scan --once

# 持续测量收到消息的频率，Ctrl+C 结束
ros2 topic hz /scan
```

正常应能看到 `/training_simulator`、`/training_bridge`，并接收到 `/scan` 和 `/odom`。激光配置频率为 10 Hz；虚拟机负载和订阅情况可能影响观测值。

检查坐标关系和导航接口：

```bash
# 持续显示地图到机器人的变换，Ctrl+C 结束
ros2 run tf2_ros tf2_echo map base_link

ros2 action list -t
ros2 action info /navigate_to_pose

# 持续查看节点日志，Ctrl+C 结束
ros2 topic echo /rosout
```

定位模式和仅仿真模式没有导航 Action 服务属于正常情况。网页“诊断”页签也能查看节点、话题和日志，但建议先在终端完成一次检查。

### ROS 域与 DDS 一致性

Launch 现在跟随启动终端的 ROS_DOMAIN_ID，未设置时使用默认域 0；也可显式传入 ros_domain_id:=数字覆盖。启动与保存地图使用相同域和 DDS 设置。若修改过环境，需要重新启动实验才生效；不要在当前地图未保存时停止 SLAM。


## 6. 停止、更新与常见问题

**正常停止：** 先取消导航、松开按键。网页启动的实验用“停止实验”；终端启动的实验在原 Launch 终端按 `Ctrl+C`。最后在终端 A 按 `Ctrl+C` 关闭网页服务。

更新代码后，在旧实验停止的情况下重新编译，然后重新启动服务：

```bash
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

网页使用 `Ctrl+Shift+R` 强制刷新。

| 问题 | 先做什么 |
| --- | --- |
| `Package ... not found` | 检查编译结果，并在当前终端重新加载 ROS 和工作区环境。 |
| `Address already in use` | 端口已有服务。已有本平台网页时直接打开；需要重启则在原终端 Ctrl+C，避免重复启动。 |
| 网页连接成功，但没有地图 | 检查 Launch 是否运行、模式、`ros2 node list`、`/scan`、`/map` 和 TF。 |
| 终端看不到节点 | 确认该终端已 source，且 `ROS_DOMAIN_ID` 与实验一致。 |
| 导航按钮不可用 | 确认是导航或建图模式，等待“导航已就绪”，再选可达目标。 |
| 键盘没有反应 | 点击地图或“启用键盘控制”，确认键盘已就绪；取消当前导航，检查底盘卡死故障是否关闭。 |
| 激光或局部地图偏移 | 关闭人为故障，检查定位初始位姿和 TF；更新后重启实验并强制刷新网页。仿真仍有定位误差。 |
| 保存地图失败 | 确认正在建图，`/map` 有数据，输出目录可写，并查看终端报错。 |
| 自己的地图加载失败 | 检查 YAML 引用的图片是否存在、路径正确，且有足够空白区域容纳底盘。 |
| 虚拟机卡顿 | 切二维、关闭 RViz，避免多开实验；用 `top` 检查 CPU 与内存。 |


## 7.目标与成果 
1.使用建图模式，在画面中添加障碍物，构建并保存地图。

2.使用导航模式，加载自己建的图

3.感受参数对于导航的影响，具体参考 ~/rm_nav_training_lab/docs/PARAMETER_LAB.md





