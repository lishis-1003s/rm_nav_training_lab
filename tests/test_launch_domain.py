"""Launch must not silently override the domain selected by the user's terminal."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from launch.actions import DeclareLaunchArgument

class LaunchDomainTests(unittest.TestCase):
    def test_all_launch_modes_inherit_terminal_or_use_ros_default(self):
        root=Path(__file__).resolve().parents[1]/'src/rm_nav_training_lab/launch'
        for path in root.glob('*.launch.py'):
            spec=importlib.util.spec_from_file_location('domain_check_'+path.stem,path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            for selected,expected in [(None,'0'),('73','73')]:
                env=dict(os.environ);env.pop('ROS_DOMAIN_ID',None)
                if selected is not None:env['ROS_DOMAIN_ID']=selected
                with self.subTest(mode=path.name,domain=selected),patch.dict(os.environ,env,clear=True):
                    description=module.generate_launch_description()
                    argument=next(x for x in description.entities if isinstance(x,DeclareLaunchArgument) and x.name=='ros_domain_id')
                    self.assertEqual(''.join(x.text for x in argument.default_value),expected)

if __name__=='__main__':unittest.main()
