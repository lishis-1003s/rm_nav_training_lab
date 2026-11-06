"""Regress navigation gating and fail-fast launch port ownership."""
import socket
from types import SimpleNamespace
import unittest
from launch import LaunchContext
from rclpy.time import Time
from rm_nav_training_lab.bridge import TrainingBridge
from rm_nav_training_lab.launch_utils import check_ports

class RuntimeReadinessTests(unittest.TestCase):
    def bridge(self):
        b=SimpleNamespace(nav_client=SimpleNamespace(server_is_ready=lambda:True),
            lifecycle_clients={'bt_navigator':None,'controller_server':None,'planner_server':None},
            lifecycle_states={'bt_navigator':3,'controller_server':3,'planner_server':3},
            map_cache=object(),get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=100)))
        b.tf_buffer=SimpleNamespace(lookup_transform=lambda *args:SimpleNamespace(header=SimpleNamespace(stamp=Time(seconds=99).to_msg())))
        return b

    def test_only_active_navigation_is_ready(self):
        b=self.bridge();self.assertTrue(TrainingBridge._navigation_ready(b))
        b.lifecycle_states['controller_server']=2
        self.assertFalse(TrainingBridge._navigation_ready(b))

    def test_missing_server_or_map_disables_navigation(self):
        b=self.bridge();b.map_cache=None
        self.assertFalse(TrainingBridge._navigation_ready(b))
        b=self.bridge();b.nav_client.server_is_ready=lambda:False
        self.assertFalse(TrainingBridge._navigation_ready(b))

    def test_stale_tf_disables_navigation(self):
        b=self.bridge();b.get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=105))
        self.assertFalse(TrainingBridge._navigation_ready(b))

    def test_used_rosbridge_port_rejects_launch(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));s.listen()
            c=LaunchContext();c.launch_configurations.update(rosbridge_port=str(s.getsockname()[1]),serve_web='false')
            with self.assertRaisesRegex(RuntimeError,'实验未启动'):check_ports(c)

if __name__=='__main__':unittest.main()
