from glob import glob
from pathlib import Path
from setuptools import setup

package_name = 'rm_nav_training_lab'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        *[(f'share/{package_name}/{folder}', files)
          for folder in ('launch', 'config', 'maps', 'web', 'lessons')
          for files in [[p for p in glob(f'{folder}/*') if Path(p).is_file()]] if files],
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='RM Navigation Training Lab',
    maintainer_email='training-lab@example.invalid',
    description='ROS 2 Humble navigation training platform.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'training_simulator = rm_nav_training_lab.simulator:main',
            'training_server = rm_nav_training_lab.server:main',
            'training_bridge = rm_nav_training_lab.bridge:main',
        ],
    },
)
