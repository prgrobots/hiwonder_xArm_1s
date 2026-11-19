#!/usr/bin/env python3
"""Drive the simulated LeArm from a string of servo positions.

Students publish a ``std_msgs/String`` such as::

    ros2 topic pub --once /xarm/command std_msgs/msg/String \
        "{data: '500/500/500/500/500/500'}"

The six values are servo positions in the range 0-1000, in xArm servo-ID
order (1 -> 6)::

    grip / wrist_roll / wrist_flex / elbow / shoulder_lift / shoulder_pan

Each command is turned into a single-point FollowJointTrajectory goal and sent
to the ros2_control joint_trajectory_controller, which moves the mock hardware
shown in RViz.
"""

import math

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectoryPoint

SERVO_COUNT = 6
SERVO_MIN = 0
SERVO_MAX = 1000
HALF_PI = math.pi / 2.0

# Servo-ID order 1 -> 6.
JOINT_NAMES = [
    "grip_left",
    "wrist_roll",
    "wrist_flex",
    "elbow",
    "shoulder_lift",
    "shoulder_pan",
]


def parse_command(text):
    """Parse ``"v1/v2/.../v6"`` into six integers in the range 0-1000.

    ``/``, ``,`` and ``;`` are all accepted as separators. Raises ValueError
    with a human-readable message on invalid input.
    """
    if not isinstance(text, str):
        raise ValueError("command must be a string")

    normalized = text.replace(",", "/").replace(";", "/").strip()
    parts = [part.strip() for part in normalized.split("/") if part.strip()]

    if len(parts) != SERVO_COUNT:
        raise ValueError(
            f"expected {SERVO_COUNT} values separated by '/', got {len(parts)}"
        )

    try:
        values = [int(part) for part in parts]
    except ValueError as exc:
        raise ValueError("all values must be integers") from exc

    for value in values:
        if not SERVO_MIN <= value <= SERVO_MAX:
            raise ValueError(
                f"servo values must be between {SERVO_MIN} and {SERVO_MAX}, "
                f"got {value}"
            )

    return values


def servo_to_rad(value):
    """Map a 0-1000 servo value to a -pi/2..pi/2 joint angle."""
    return (float(value) - 500.0) * math.pi / 1000.0


def grip_to_rad(value, inverted=False):
    """Map servo 1 (grip) to grip_left's -pi/2..0 range.

    By default 0 = open and 1000 = closed. Set ``inverted`` to reverse that.
    """
    fraction = float(value) / 1000.0
    if inverted:
        fraction = 1.0 - fraction
    return -fraction * HALF_PI


def command_to_positions(values, grip_inverted=False):
    """Convert six servo values into joint positions in JOINT_NAMES order."""
    if len(values) != SERVO_COUNT:
        raise ValueError(f"expected {SERVO_COUNT} values, got {len(values)}")

    positions = [grip_to_rad(values[0], inverted=grip_inverted)]
    positions.extend(servo_to_rad(value) for value in values[1:])
    return positions


class SimCommandNode(Node):
    """Listen for servo strings and forward them to the trajectory controller."""

    def __init__(self):
        super().__init__("sim_commands")

        self.declare_parameter("command_topic", "/xarm/command")
        self.declare_parameter(
            "controller_action",
            "/joint_trajectory_controller/follow_joint_trajectory",
        )
        self.declare_parameter("duration", 1.0)
        self.declare_parameter("grip_inverted", False)

        command_topic = self.get_parameter("command_topic").value
        action_name = self.get_parameter("controller_action").value
        self._duration = max(0.01, float(self.get_parameter("duration").value))
        self._grip_inverted = bool(self.get_parameter("grip_inverted").value)

        self._action_client = ActionClient(self, FollowJointTrajectory, action_name)
        self._active_goal = None

        self.create_subscription(String, command_topic, self._on_command, 10)

        self.get_logger().info(
            f"Listening on {command_topic} for 6 servo values (0-1000) in "
            "servo-ID order: grip/wrist_roll/wrist_flex/elbow/"
            "shoulder_lift/shoulder_pan."
        )
        self.get_logger().info(
            "Example: ros2 topic pub --once "
            f"{command_topic} std_msgs/msg/String "
            "\"{data: '500/500/500/500/500/500'}\""
        )
        self.get_logger().info(f"Trajectory action: {action_name}")

    def _on_command(self, message):
        try:
            values = parse_command(message.data)
        except ValueError as exc:
            self.get_logger().warning(
                f"Ignoring command {message.data!r}: {exc}"
            )
            return

        positions = command_to_positions(values, self._grip_inverted)
        self.get_logger().info(f"Command {values} -> {positions}")

        if not self._action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error(
                "Trajectory controller is not available yet; command dropped."
            )
            return

        # Replace any command that is still executing so rapid updates do not
        # queue up behind each other.
        if self._active_goal is not None:
            try:
                self._active_goal.cancel_goal_async()
            except Exception:  # noqa: BLE001 - goal may already be finished
                pass
            self._active_goal = None

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(JOINT_NAMES)

        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start = Duration(
            sec=int(self._duration),
            nanosec=int((self._duration % 1.0) * 1e9),
        )
        goal.trajectory.points = [point]

        send_future = self._action_client.send_goal_async(goal)
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        try:
            goal_handle = future.result()
        except Exception as exc:  # noqa: BLE001 - report send failures
            self.get_logger().error(f"Failed to send trajectory: {exc}")
            return

        if not goal_handle.accepted:
            self.get_logger().warning("Trajectory goal was rejected.")
            return

        self._active_goal = goal_handle
        goal_handle.get_result_async().add_done_callback(self._on_result)

    def _on_result(self, future):
        self._active_goal = None
        try:
            result = future.result()
        except Exception as exc:  # noqa: BLE001 - cancelled goals raise
            self.get_logger().warning(f"Trajectory did not complete: {exc}")
            return

        code = result.result.error_code
        if code == FollowJointTrajectory.Result.SUCCESSFUL:
            self.get_logger().info("Trajectory reached its target.")
        else:
            self.get_logger().warning(
                f"Trajectory finished with error code {code}: "
                f"{result.result.error_string}"
            )


def main(args=None):
    rclpy.init(args=args)
    node = SimCommandNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
