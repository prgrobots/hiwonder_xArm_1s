import os
from glob import glob

from setuptools import setup

package_name = 'learm_ros2_moveit_config'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', '.setup_assistant']),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='andrewda',
    maintainer_email='andrewda@todo.todo',
    description='MoveIt configuration for the Hiwonder LeArm / xArm 1S simulation',
    license='BSD-3-Clause',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)
