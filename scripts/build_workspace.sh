#!/usr/bin/env bash
set -eo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo '请先安装 ROS 2 Humble。' >&2
  exit 2
fi
source /opt/ros/humble/setup.bash
colcon build --symlink-install
printf '编译完成。加载 install/setup.bash 后，用 ros2 run 启动网页服务，并在另一终端用 ros2 launch 启动实验。\n'
