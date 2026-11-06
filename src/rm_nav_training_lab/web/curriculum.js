// Terminal references only. The browser never executes these commands.
const terminalSetup = `# 每个终端都先执行；在工作区根目录运行
cd ~/rm_nav_training_lab
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=0
# 终端 A 只提供网页，勿点击自由体验启动按钮
# ros2 run rm_nav_training_lab training_server
# 终端 B 启动实验；终端 C 执行检查。Ctrl+C 停止当前命令。`;
const commandLessons = [
 {task:'在终端启动仅仿真，确认节点与传感器的发布/订阅关系。',hint:'完整示例阶段：区分持续运行的 Launch、持续观测的 hz 与只读一次的 echo。',commands:terminalSetup+`\nros2 launch rm_nav_training_lab sim_only.launch.py serve_web:=false rviz:=false
# 在另一个已完成环境准备的终端
ros2 node list
ros2 node info /training_simulator
ros2 topic list -t
ros2 topic info /scan --verbose
ros2 topic hz /scan
# Ctrl+C 退出 hz 后运行
ros2 topic echo /scan --once`,evidence:'启动命令、Node List、/scan 类型/发布者/频率和一次消息；用自己的话解释节点与话题的区别。'},
 {task:'检查 map → odom → base_link → laser_frame，解释横移时里程计和坐标变换的变化。',hint:'完整示例阶段：一个终端运行 TF 检查，网页用 W/S、A/D、Q/E 操作，保留变换与激光截图。',commands:terminalSetup+`\nros2 run tf2_ros tf2_echo map base_link
# Ctrl+C 后检查传感器外参
ros2 run tf2_ros tf2_echo base_link laser_frame
# 在证据目录生成 TF 图
mkdir -p ~/rm_training_evidence
cd ~/rm_training_evidence
ros2 run tf2_tools view_frames
ros2 topic echo /odom --once`,evidence:'TF 图、两组 tf2_echo 输出、横移前后 odom 与网页截图；解释哪个变换由哪一类节点提供。'},
 {task:'通过终端切换到 SLAM，手动探索，用命令保存地图图片与 YAML，并检查保存结果。',hint:'完整示例阶段：先对旧 Launch 按 Ctrl+C。地图前缀不带扩展名；保留保存日志，不能只凭网页显示地图就认定已保存。',commands:terminalSetup+`\nros2 launch rm_nav_training_lab slam_nav2.launch.py serve_web:=false rviz:=false
# 在另一终端检查建图数据；网页手动探索
ros2 node list
ros2 topic echo /map --once --field info
mkdir -p ~/rm_training_maps
ros2 run nav2_map_server map_saver_cli -f ~/rm_training_maps/slam_01 --ros-args -p map_subscribe_transient_local:=true
ls -lh ~/rm_training_maps/slam_01.*
cat ~/rm_training_maps/slam_01.yaml`,evidence:'SLAM 启动命令、探索截图、map_saver_cli 成功日志、地图图片与 YAML；说明 resolution、origin、image 的含义。'},
 {task:'独立停止 SLAM，加载刚保存的 YAML 进行导航，追踪目标从地图到规划、控制、执行的流程。',hint:'使用 known_map.launch.py 的 map 参数传入地图绝对路径；先检查 TF 和节点，再发送目标。先自行组织命令，需要时展开参考。',commands:terminalSetup+`\nros2 launch rm_nav_training_lab known_map.launch.py serve_web:=false rviz:=false map:=$HOME/rm_training_maps/slam_01.yaml
# 在另一终端检查导航链路
ros2 node list
ros2 topic info /map
ros2 run tf2_ros tf2_echo map base_link
# 退出 TF 观察后检查 Action
ros2 action list -t
ros2 action info /navigate_to_pose
ros2 topic echo /training/navigation_status --once`,evidence:'加载地图命令、Map Server/规划/控制节点、TF 与 Action 检查输出、到达或失败原因。保存地图重载会将已建区域作为新的二维仿真世界，不代表恢复原始世界和 SLAM 状态。'},
 {task:'用 param list/get/set/dump 调整膨胀参数，再修改 YAML 并通过 params_file 启动，对比结果。',hint:'先读取基线、记录调整前；膨胀参数可实时修改。速度与加速度可动态修改；评分权重需重载。完整配置仍应保存到 YAML 并通过 Launch 复现。单节点 dump 不等于包含全部 Nav2 节点的参数文件。若提示 Node not found，核对域 ID/节点全名，等待发现；可用 --no-daemon --spin-time 5 排查。',commands:terminalSetup+`\nmkdir -p ~/rm_training_evidence ~/rm_training_configs
ros2 param list /global_costmap/global_costmap
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param set /global_costmap/global_costmap inflation_layer.inflation_radius 0.7
ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius
ros2 param dump /global_costmap/global_costmap > ~/rm_training_evidence/global_costmap.yaml
cp "$(ros2 pkg prefix --share rm_nav_training_lab)/config/nav2_params.yaml" ~/rm_training_configs/nav2_experiment.yaml
nano ~/rm_training_configs/nav2_experiment.yaml
# 先结束旧 Launch，再运行；按自己的地图路径补充 map 参数
ros2 launch rm_nav_training_lab known_map.launch.py serve_web:=false rviz:=false params_file:=$HOME/rm_training_configs/nav2_experiment.yaml`,evidence:'参数基线/新值、dump 文件、修改过的完整 YAML、启动命令和同一目标/障碍条件下的前后图；说明参数如何影响 Costmap 和路径。'},
 {task:'检查导航 Action 的服务器和客户端，解释目标、反馈、结果与全局路径的关系。',hint:'从 action list/info、interface show 开始；先在网页选择可达目标。进阶练习可自行填写 map 坐标发送目标，参考坐标必须替换。',commands:terminalSetup+`\nros2 action list -t
ros2 action info /navigate_to_pose
ros2 interface show nav2_msgs/action/NavigateToPose
ros2 topic info /plan
ros2 topic echo /plan --once
# 以下 x/y 仅为格式示例，先选取当前地图的可达坐标再替换
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: -5.0, y: -3.0}, orientation: {w: 1.0}}}}" --feedback`,evidence:'Action list/info、目标坐标、反馈与最终状态、路径截图；说明浏览器桥接目标与 CLI 直接发送目标的区别。CLI 目标以终端反馈为准，不依赖网页网关的专属状态记录。'},
 {task:'不给操作步骤，独立诊断一次底盘卡死或里程计异常，定位故障所在链路。',hint:'仅给任务：先建立无故障基线；注入一种故障；收集控制输出、实际执行、里程计和 TF 证据；复位并证明恢复。',commands:terminalSetup+`\nros2 topic echo /cmd_vel
ros2 topic echo /training/sim_cmd_vel
ros2 topic echo /odom
ros2 run tf2_ros tf2_echo odom base_link
ros2 topic echo /training/fault_state --once
# 各持续命令在独立终端运行，或 Ctrl+C 后切换`,evidence:'现象、你自行组织的检查命令与原始输出、至少两条互相印证的证据、根因和复位前后结果。'},
 {task:'独立记录一次规划/跟随/恢复过程的日志和 rosbag，在隔离域回放并解释。',hint:'仅给任务：选择必要话题，录制期间产生真实导航行为；停止录制后检查 bag。回放使用域 43，所有检查终端也使用 43，防止与域 0 的在线实验混合。',commands:terminalSetup+`\nros2 topic echo /rosout
ros2 topic echo /behavior_tree_log
mkdir -p ~/rm_training_evidence
# 录制用新的目录名；Ctrl+C 结束后再检查
ros2 bag record -o ~/rm_training_evidence/nav_run_01 /map /scan /odom /tf /tf_static /plan /local_plan /cmd_vel /training/sim_cmd_vel /rosout /behavior_tree_log
ros2 bag info ~/rm_training_evidence/nav_run_01
ROS_DOMAIN_ID=43 ros2 bag play ~/rm_training_evidence/nav_run_01 --loop
# 在另一个终端检查回放，Ctrl+C 结束
ROS_DOMAIN_ID=43 ros2 topic echo /odom --once`,evidence:'录制命令、bag info、bag 文件夹、隔离域回放输出、行为树/日志片段；说明回放数据与重新运行导航的区别。'},
 {task:'独立完成从命令行启动、SLAM、保存地图、加载导航、修改 YAML、诊断故障到证据提交的全流程。',hint:'不给完整操作步骤。自行确定命令顺序、检查节点/话题/参数/TF/Action、录制必要证据并恢复实验基线。参考仅作查漏。',commands:`# 提交前自查，不是可直接执行的脚本
# 1. 环境与域 ID、各模式 Launch 命令
# 2. 地图图片 + YAML；修改后的 Nav2 参数 YAML
# 3. Node / Topic / Param / TF / Action 原始检查输出
# 4. 前后对比截图，日志、bag 与 bag info
# 5. 现象 → 假设 → 证据 → 根因 → 修复 → 验证
# 6. 网页实验记录导出 JSON，交教师人工检查`,evidence:'完整实验目录，含命令记录、终端输出、地图、配置、截图、bag、诊断分析和网页导出 JSON。由教师人工验收，不自动评分。'}
];
