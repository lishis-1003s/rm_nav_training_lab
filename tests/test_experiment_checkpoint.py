"""Checkpoint must restore physical pose and obstacles, never an aliased UI copy."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from rclpy.time import Time
from std_srvs.srv import Trigger
from rm_nav_training_lab.simulator import TrainingSimulator

class CheckpointTests(unittest.TestCase):
    def test_restores_pose_obstacles_and_zero_commands(self):
        s=SimpleNamespace(x=1.,y=2.,yaw=.4,obstacles={'a':{'x':4.,'y':3.,'radius':.3}},checkpoint=None,
            _publish_odom_and_tf=Mock(),initial_pose_pub=Mock(),_publish_fault_state=Mock(),get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=10)))
        r=TrainingSimulator._capture_start(s,None,Trigger.Response());self.assertTrue(r.success)
        s.x=8.;s.y=9.;s.yaw=2.;s.obstacles['a']['x']=7.
        r=TrainingSimulator._restore_start(s,None,Trigger.Response());self.assertTrue(r.success)
        self.assertEqual((s.x,s.y,s.yaw),(1.,2.,.4));self.assertEqual((s.odom_x,s.odom_y,s.odom_yaw),(1.,2.,.4))
        self.assertEqual(s.obstacles['a']['x'],4.);self.assertEqual(s.nav_cmd,(0.,0.,0.));self.assertEqual(s.explore_cmd_time,0.)
        s.obstacles['a']['x']=99.;self.assertEqual(s.checkpoint['obstacles']['a']['x'],4.)
        message=s.initial_pose_pub.publish.call_args.args[0];self.assertEqual(message.pose.pose.position.x,1.)
        s._publish_odom_and_tf.assert_called_once_with(0.,0.,0.)

    def test_restore_requires_saved_checkpoint(self):
        r=TrainingSimulator._restore_start(SimpleNamespace(checkpoint=None),None,Trigger.Response());self.assertFalse(r.success)

if __name__=='__main__':unittest.main()
