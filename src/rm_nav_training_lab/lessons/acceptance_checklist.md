# 部署与验收清单

请在 Ubuntu 22.04、ROS 2 Humble 目标机器完成这些步骤。当前工作环境缺少 rosbridge_suite，因此目标机验收仍是必需项。

## 编译与启动

- [ ] `rosdep install --from-paths src --ignore-src -r -y` 成功。
- [ ] `colcon build --symlink-install` 成功。
- [ ] 分别运行 `sim_only.launch.py`、`known_map.launch.py` 和 `slam_nav2.launch.py`。
- [ ] 浏览器打开 `http://localhost:8080` 并连接 `ws://localhost:9090`。
- [ ] `rviz:=true` 时 RViz2 能打开；无图形环境使用 `rviz:=false`。

## 话题、TF 与节点

在 ROS_DOMAIN_ID 与 launch 一致的终端运行：

```bash
export ROS_DOMAIN_ID=42
ros2 node list
ros2 topic hz /scan
ros2 topic echo /odom --once
ros2 topic echo /training/fault_state --once
ros2 run tf2_tools view_frames
```

- [ ] 节点图包含 `training_simulator` 和 `training_bridge`。
- [ ] 仿真模式能收到 `/map`、`/scan`、`/odom`、`/tf` 和 `/tf_static`。
- [ ] 已知地图模式能看到 `map_server`、`amcl` 与 Nav2 节点，且 `map → odom → base_link` 连通。
- [ ] SLAM 模式能看到 `slam_toolbox` 并由 SLAM 输出地图和 `map → odom`。
- [ ] 浏览器与 RViz2 中同一时刻的地图、扫描、位姿和路径一致。

## Action、参数和故障

- [ ] `ros2 action list` 中包含 `/navigate_to_pose`。
- [ ] 从浏览器发送可达目标后，Nav2 Action 有状态变化，路径和位姿来自 ROS 话题。
- [ ] 取消导航后收到 Nav2 的 Action 终态。
- [ ] 浏览器修改膨胀半径后，`ros2 param get /global_costmap/global_costmap inflation_layer.inflation_radius` 返回新值；复位值为 `0.45`。
- [ ] 中断 `/scan` 后 `ros2 topic hz /scan` 无新消息，恢复后重新发布。
- [ ] TF 扰动、里程计噪声、动态障碍物、底盘卡死分别影响对应 ROS 数据；复位可恢复。
- [ ] `/rosout`、`/training/events` 和服务回执能用于定位故障。
- [ ] SLAM 保存地图只有在服务响应 `RESULT_SUCCESS` 时记录成功。

## 教学验收

- [ ] 学生能按 README 完成安装和启动。
- [ ] 每个关卡都可找到目的、步骤、观察项、成功判据或复位方式。
- [ ] 学生能保存包含现象、数据证据和根因的实验记录。
- [ ] 记录失败日志、ROS 包版本、运行命令和修复步骤，以便复现。
