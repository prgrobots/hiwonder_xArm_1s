import os
from glob import glob

from setuptools import setup

package_name = 'learm_ros2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='andrewda',
    maintainer_email='andrewda@todo.todo',
    description='ROS 2 simulation interface for the Hiwonder LeArm / xArm 1S',
    license='BSD-3-Clause',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'sim_commands = learm_ros2.sim_commands:main',
        ],
    },
)
