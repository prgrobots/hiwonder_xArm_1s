"""Bring up the simulated xArm/LeArm in RViz.

No physical arm, USB connection or Gazebo is used. The stack is:

    ros2_control (mock hardware)
        + joint_state_broadcaster
        + joint_trajectory_controller
        + robot_state_publisher
        + MoveIt move_group
        + RViz2

Drive it by publishing a string of six servo values (0-1000, servo-ID order
1 -> 6) on /xarm/command, for example:

    ros2 topic pub --once /xarm/command std_msgs/msg/String \
        "{data: '500/500/500/500/500/500'}"
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    use_rviz = LaunchConfiguration("use_rviz")
    use_sim_time = LaunchConfiguration("use_sim_time")
    duration = LaunchConfiguration("duration")
    grip_inverted = LaunchConfiguration("grip_inverted")

    description_share = get_package_share_directory("learm_ros2_description")
    moveit_share = get_package_share_directory("learm_ros2_moveit_config")

    urdf_path = os.path.join(description_share, "urdf", "learm.urdf.xacro")
    controllers_path = os.path.join(
        description_share, "config", "ros2_controllers.yaml"
    )
    rviz_config = os.path.join(moveit_share, "rviz", "sim.rviz")

    robot_description = ParameterValue(
        Command(["xacro ", urdf_path]), value_type=str
    )

    # Builds the MoveIt parameter dictionaries using the correct layout/keys
    # for the installed MoveIt 2 version.
    moveit_config = (
        MoveItConfigsBuilder("learm", package_name="learm_ros2_moveit_config")
        .robot_description(file_path=urdf_path)
        .robot_description_semantic(file_path="config/learm.srdf")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            {"robot_description": robot_description},
            controllers_path,
        ],
        output="screen",
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
        output="screen",
    )

    joint_trajectory_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_trajectory_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
        output="screen",
    )

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        parameters=[moveit_config.to_dict(), {"use_sim_time": use_sim_time}],
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config],
        parameters=[moveit_config.to_dict(), {"use_sim_time": use_sim_time}],
        condition=IfCondition(use_rviz),
        output="screen",
    )

    sim_commands = Node(
        package="learm_ros2",
        executable="sim_commands",
        name="sim_commands",
        parameters=[
            {
                "duration": ParameterValue(duration, value_type=float),
                "grip_inverted": ParameterValue(
                    grip_inverted, value_type=bool
                ),
            }
        ],
        output="screen",
    )

    # Matches the SRDF's virtual world -> base_link joint so MoveIt and RViz
    # agree on the planning frame.
    world_to_base = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="world_to_base_link",
        arguments=[
            "--x", "0", "--y", "0", "--z", "0",
            "--roll", "0", "--pitch", "0", "--yaw", "0",
            "--frame-id", "world",
            "--child-frame-id", "base_link",
        ],
        output="log",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_rviz",
                default_value="true",
                description="Start RViz2 with the MoveIt display.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use simulated time (not needed for mock hardware).",
            ),
            DeclareLaunchArgument(
                "duration",
                default_value="1.0",
                description="Seconds each servo command takes to reach its target.",
            ),
            DeclareLaunchArgument(
                "grip_inverted",
                default_value="false",
                description="Swap the meaning of grip 0 and 1000.",
            ),
            LogInfo(
                msg=(
                    "Simulated LeArm starting. Publish commands with: "
                    "ros2 topic pub --once /xarm/command std_msgs/msg/String "
                    "\"{data: '500/500/500/500/500/500'}\""
                )
            ),
            world_to_base,
            robot_state_publisher,
            control_node,
            joint_state_broadcaster_spawner,
            joint_trajectory_controller_spawner,
            move_group,
            sim_commands,
            rviz,
        ]
    )
