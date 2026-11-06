#!/usr/bin/env bash
set -eo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
if [[ ! -f /opt/ros/humble/setup.bash || ! -f install/setup.bash ]]; then
  echo '请先安装 ROS 2 Humble，并执行 bash scripts/build_workspace.sh。' >&2
  exit 2
fi
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
exec ros2 run rm_nav_training_lab training_server
