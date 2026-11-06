#!/usr/bin/env bash
set -euo pipefail

mode="${1:-known_map}"
domain_id="${ROS_DOMAIN_ID:-0}"

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo "ROS 2 Humble was not found at /opt/ros/humble." >&2
  exit 2
fi
if [[ ! -f install/setup.bash ]]; then
  echo "Workspace is not built. Run colcon build --symlink-install from the project root." >&2
  exit 3
fi

source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID="$domain_id"

case "$mode" in
  sim|sim_only) launch_file=sim_only.launch.py ;;
  known|known_map) launch_file=known_map.launch.py ;;
  slam|slam_nav2) launch_file=slam_nav2.launch.py ;;
  *) echo "Usage: $0 {sim|known_map|slam}" >&2; exit 1 ;;
esac

exec ros2 launch rm_nav_training_lab "$launch_file" "ros_domain_id:=$domain_id"
