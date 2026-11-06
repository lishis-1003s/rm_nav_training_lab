# 导航训练命令行课程与人工验收

学生使用终端启动、停止和切换 Launch 模式，使用命令保存地图和修改配置；网页负责观察、交互、比较和实验记录。教学模式默认启用，自由体验模式保留网页控制。两种方式切换不改变正在运行的进程。切换到终端前，先在自由体验停止其管理的实验；终端启动的实验用 Ctrl+C 结束。

## 环境和终端分工

终端 A 运行 training_server，仅提供网页。终端 B 执行以下各模式 Launch，统一使用 serve_web:=false，避免重复占用 8080。终端 C 及更多终端检查 ROS、保存地图或录制 bag。每个终端先 source 环境并设置 ROS_DOMAIN_ID=0。独立 Launch 也可以提供静态网页，但此时不要运行 training_server。

前 3 关提供完整示例，中间 3 关先给提示，后 3 关要求独立组织操作。网页展开命令只供参考，不自动执行。命令输出是学生提供的证据，不会伪装成平台读取的 ROS 日志。

## 1 Linux 与 ROS 2 入门

目标：在终端启动仅仿真，确认节点与传感器的发布/订阅关系。

引导：完整示例阶段：区分持续运行的 Launch、持续观测的 hz 与只读一次的 echo。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 launch rm_nav_training_lab sim_only.launch.py serve_web:=false rviz:=false
# 在另一个已完成环境准备的终端
ros2 node list
ros2 node info /training_simulator
ros2 topic list -t
ros2 topic info /scan --verbose
ros2 topic hz /scan
# Ctrl+C 退出 hz 后运行
ros2 topic echo /scan --once
```

人工验收证据：启动命令、Node List、/scan 类型/发布者/频率和一次消息；用自己的话解释节点与话题的区别。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 2 TF2 与激光

目标：检查 map → odom → base_link → laser_frame，解释横移时里程计和坐标变换的变化。

引导：完整示例阶段：一个终端运行 TF 检查，网页用 W/S、A/D、Q/E 操作，保留变换与激光截图。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 run tf2_ros tf2_echo map base_link
# Ctrl+C 后检查传感器外参
ros2 run tf2_ros tf2_echo base_link laser_frame
# 在证据目录生成 TF 图
mkdir -p ~/rm_training_evidence
cd ~/rm_training_evidence
ros2 run tf2_tools view_frames
ros2 topic echo /odom --once
```

人工验收证据：TF 图、两组 tf2_echo 输出、横移前后 odom 与网页截图；解释哪个变换由哪一类节点提供。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 3 SLAM 与命令行保存地图

目标：通过终端切换到 SLAM，手动探索，用命令保存地图图片与 YAML，并检查保存结果。

引导：完整示例阶段：先对旧 Launch 按 Ctrl+C。地图前缀不带扩展名；保留保存日志，不能只凭网页显示地图就认定已保存。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 launch rm_nav_training_lab slam_nav2.launch.py serve_web:=false rviz:=false
# 在另一终端检查建图数据；网页手动探索
ros2 node list
ros2 topic echo /map --once --field info
mkdir -p ~/rm_training_maps
ros2 run nav2_map_server map_saver_cli -f ~/rm_training_maps/slam_01 --ros-args -p map_subscribe_transient_local:=true
ls -lh ~/rm_training_maps/slam_01.*
cat ~/rm_training_maps/slam_01.yaml
```

人工验收证据：SLAM 启动命令、探索截图、map_saver_cli 成功日志、地图图片与 YAML；说明 resolution、origin、image 的含义。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 4 地图加载与导航流程

目标：独立停止 SLAM，加载刚保存的 YAML 进行导航，追踪目标从地图到规划、控制、执行的流程。

引导：使用 known_map.launch.py 的 map 参数传入地图绝对路径；先检查 TF 和节点，再发送目标。先自行组织命令，需要时展开参考。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 launch rm_nav_training_lab known_map.launch.py serve_web:=false rviz:=false map:=$HOME/rm_training_maps/slam_01.yaml
# 在另一终端检查导航链路
ros2 node list
ros2 topic info /map
ros2 run tf2_ros tf2_echo map base_link
# 退出 TF 观察后检查 Action
ros2 action list -t
ros2 action info /navigate_to_pose
ros2 topic echo /training/navigation_status --once
```

人工验收证据：加载地图命令、Map Server/规划/控制节点、TF 与 Action 检查输出、到达或失败原因。保存地图重载会将已建区域作为新的二维仿真世界，不代表恢复原始世界和 SLAM 状态。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 5 参数与 YAML 配置

目标：用 param list/get/set/dump 调整膨胀参数，再修改 YAML 并通过 params_file 启动，对比结果。

引导：先读取基线、记录调整前；膨胀参数可实时修改。速度与加速度可动态修改；评分权重需重载。完整配置仍应保存到 YAML 并通过 Launch 复现。单节点 dump 不等于包含全部 Nav2 节点的参数文件。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
mkdir -p ~/rm_training_evidence ~/rm_training_configs
ros2 param list /global_costmap/global_costmap
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param set /global_costmap/global_costmap inflation_layer.inflation_radius 0.7
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param dump /global_costmap/global_costmap > ~/rm_training_evidence/global_costmap.yaml
cp "$(ros2 pkg prefix --share rm_nav_training_lab)/config/nav2_params.yaml" ~/rm_training_configs/nav2_experiment.yaml
nano ~/rm_training_configs/nav2_experiment.yaml
# 先结束旧 Launch，再运行；按自己的地图路径补充 map 参数
ros2 launch rm_nav_training_lab known_map.launch.py serve_web:=false rviz:=false params_file:=$HOME/rm_training_configs/nav2_experiment.yaml
```

人工验收证据：参数基线/新值、dump 文件、修改过的完整 YAML、启动命令和同一目标/障碍条件下的前后图；说明参数如何影响 Costmap 和路径。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 6 Action 与路径

目标：检查导航 Action 的服务器和客户端，解释目标、反馈、结果与全局路径的关系。

引导：从 action list/info、interface show 开始；先在网页选择可达目标。进阶练习可自行填写 map 坐标发送目标，参考坐标必须替换。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 action list -t
ros2 action info /navigate_to_pose
ros2 interface show nav2_msgs/action/NavigateToPose
ros2 topic info /plan
ros2 topic echo /plan --once
# 以下 x/y 仅为格式示例，先选取当前地图的可达坐标再替换
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: -5.0, y: -3.0}, orientation: {w: 1.0}}}}" --feedback
```

人工验收证据：Action list/info、目标坐标、反馈与最终状态、路径截图；说明浏览器桥接目标与 CLI 直接发送目标的区别。CLI 目标以终端反馈为准，不依赖网页网关的专属状态记录。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 7 底盘与里程计诊断

目标：不给操作步骤，独立诊断一次底盘卡死或里程计异常，定位故障所在链路。

引导：仅给任务：先建立无故障基线；注入一种故障；收集控制输出、实际执行、里程计和 TF 证据；复位并证明恢复。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 topic echo /cmd_vel
ros2 topic echo /training/sim_cmd_vel
ros2 topic echo /odom
ros2 run tf2_ros tf2_echo odom base_link
ros2 topic echo /training/fault_state --once
# 各持续命令在独立终端运行，或 Ctrl+C 后切换
```

人工验收证据：现象、你自行组织的检查命令与原始输出、至少两条互相印证的证据、根因和复位前后结果。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 8 行为树日志与 rosbag

目标：独立记录一次规划/跟随/恢复过程的日志和 rosbag，在隔离域回放并解释。

引导：仅给任务：选择必要话题，录制期间产生真实导航行为；停止录制后检查 bag。回放使用域 43，所有检查终端也使用 43，防止与域 0 的在线实验混合。

```bash
# 每个终端都先执行；在工作区根目录运行
cd ${HOME}/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。
ros2 topic echo /rosout
ros2 topic echo /behavior_tree_log
mkdir -p ~/rm_training_evidence
# 录制用新的目录名；Ctrl+C 结束后再检查
ros2 bag record -o ~/rm_training_evidence/nav_run_01 /map /scan /odom /tf /tf_static /plan /local_plan /cmd_vel /training/sim_cmd_vel /rosout /behavior_tree_log
ros2 bag info ~/rm_training_evidence/nav_run_01
ROS_DOMAIN_ID=43 ros2 bag play ~/rm_training_evidence/nav_run_01 --loop
# 在另一个终端检查回放，Ctrl+C 结束
ROS_DOMAIN_ID=43 ros2 topic echo /odom --once
```

人工验收证据：录制命令、bag info、bag 文件夹、隔离域回放输出、行为树/日志片段；说明回放数据与重新运行导航的区别。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 9 综合独立实验

目标：独立完成从命令行启动、SLAM、保存地图、加载导航、修改 YAML、诊断故障到证据提交的全流程。

引导：不给完整操作步骤。自行确定命令顺序、检查节点/话题/参数/TF/Action、录制必要证据并恢复实验基线。参考仅作查漏。

```bash
# 提交前自查，不是可直接执行的脚本
# 1. 环境与域 ID、各模式 Launch 命令
# 2. 地图图片 + YAML；修改后的 Nav2 参数 YAML
# 3. Node / Topic / Param / TF / Action 原始检查输出
# 4. 前后对比截图，日志、bag 与 bag info
# 5. 现象 → 假设 → 证据 → 根因 → 修复 → 验证
# 6. 网页实验记录导出 JSON，交教师人工检查
```

人工验收证据：完整实验目录，含命令记录、终端输出、地图、配置、截图、bag、诊断分析和网页导出 JSON。由教师人工验收，不自动评分。

复位：退出持续检查命令；结束当前目标，停止手动输入、清除故障；需要切换模式时对旧 Launch 按 Ctrl+C，并确认节点退出。参数实验使用基线 YAML 重启。保留自己的地图和证据文件。

## 教师人工检查

检查学生能否解释自己的启动参数、坐标系、消息、参数值与数据因果。每关至少检查命令原文、原始输出、截图和原因说明；不能仅凭界面正常或服务调用成功判定掌握。综合实验提交地图图片与 YAML、完整参数 YAML、终端记录、截图、bag 目录和 bag info、诊断报告及网页导出 JSON。平台不自动评分。

地图保存范围为占据栅格图片与 YAML，不包含 SLAM 位姿图序列化或继续建图。已知地图仿真会把加载地图作为新的激光/碰撞世界；这不是恢复原始赛场状态。AMCL 作为基础定位服务存在，不要求专项调参。

注意：CLI 直接发送的 Action 目标不由网页 Action 网关管理，其反馈和取消以相应 CLI/Action 接口为准。查看在线实验用域 0，bag 回放用域 43；回放不会重新执行导航算法。

## 节点发现与参数命令排查

若参数命令返回 `Node not found`，先核对目标 Launch 是否仍运行、当前终端已 source 环境且域 ID 为 0，并检查节点全名。ROS 图发现可能有延迟，不能把一次发现失败直接认定为节点退出。

```bash
ros2 node list --no-daemon --spin-time 5
ros2 param dump /global_costmap/global_costmap --no-daemon --spin-time 5 > ~/rm_training_evidence/global_costmap.yaml
```

如果 CLI 守护进程视图与直接发现结果不同，可在相同域中执行 `ros2 daemon stop`、`ros2 daemon start` 后重新检查。保留失败信息和最终有效输出，解释排查依据。
