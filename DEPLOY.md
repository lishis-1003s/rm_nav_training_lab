# 从源码包模拟部署

适用环境：Ubuntu 22.04 + ROS 2 Humble。支持本机或虚拟机，不依赖 Gazebo。源码包没有包含 ROS、系统依赖或编译产物，安装依赖需要联网。

## 1. 到新目录

git clone 得到 `rm_nav_training_lab` 文件夹，建议放到主目录。以下假设路径为 `~/rm_nav_training_lab`；也可放到其他位置，后文的 cd 命令相应替换为实际目录。

```bash
cd ~/rm_nav_training_lab
```

不要覆盖已有实验文件。用户自己的地图、bag 和浏览器实验记录不包含在此源码包中。

## 2. 安装依赖

需要预先安装 ROS 2 Humble，并确认 `/opt/ros/humble/setup.bash` 存在。此脚本不安装 ROS 本体：

```bash
bash scripts/install_dependencies_ubuntu2204.sh
```

脚本会通过 sudo 安装 Nav2、SLAM Toolbox、ROSBridge、地图读取依赖与编译工具。

## 3. 在终端逐条编译

```bash
cd ~/rm_nav_training_lab
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

应显示 `1 package finished`，没有失败包。第一个 source 加载 ROS，colcon 编译当前工作区，第二个 source 加载本工程。不要复制旧工程的 build、install 和 log。

