#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f /etc/os-release ]]; then
  echo "Cannot identify the operating system." >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
  echo "This dependency script targets Ubuntu 22.04; detected ${PRETTY_NAME:-unknown}." >&2
  exit 2
fi
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo "ROS 2 Humble is not installed at /opt/ros/humble." >&2
  exit 3
fi

sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-slam-toolbox \
  ros-humble-rviz2 \
  ros-humble-tf2-tools \
  ros-humble-ros2bag \
  ros-humble-rosbag2-storage-default-plugins \
  python3-pil \
  python3-yaml \
  ros-humble-rosbridge-suite

echo "Dependencies installed. Build the workspace from its root with colcon build --symlink-install."
