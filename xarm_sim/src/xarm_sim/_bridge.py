"""ROS 2 transport for :mod:`xarm_sim`.

Importing this module only needs the standard library. The ROS 2 packages are
imported lazily inside :meth:`_Bridge.start`, so ``import xarm_sim`` works on a
machine where ROS has not been sourced. It is constructing a
:class:`~xarm_sim.controller.Controller` that requires ROS.
"""

import atexit
import math
import os
import threading
import time

# Servo-ID order used by the xArm/LeArm: 1 -> 6.
SERVO_TO_JOINT = {
    1: "grip_left",
    2: "wrist_roll",
    3: "wrist_flex",
    4: "elbow",
    5: "shoulder_lift",
    6: "shoulder_pan",
}

JOINT_TO_SERVO = {joint: servo for servo, joint in SERVO_TO_JOINT.items()}

GRIP_SERVO_ID = 1
HALF_PI = math.pi / 2.0

DEFAULT_ACTION = "/joint_trajectory_controller/follow_joint_trajectory"
DEFAULT_JOINT_STATES = "/joint_states"

# Every joint in the URDF is limited to 0.5 rad/s.
MAX_VELOCITY = 0.5
MIN_DURATION = 0.05
DEFAULT_BATTERY_VOLTAGE = 7.4

_ROS_MISSING = (
    "xarm_sim needs a sourced ROS 2 environment, but rclpy could not be "
    "imported. Source your ROS 2 installation first, for example:\n"
    "    source /opt/ros/jazzy/setup.bash"
)

_SERVER_MISSING = (
    "Could not reach the trajectory action server at {action!r}. Is the "
    "simulator running? Start it with:\n"
    "    ros2 launch learm_ros2 sim.launch.py"
)


def servo_to_joint_radians(servo_id, position, grip_inverted=False):
    """Convert a 0-1000 servo position to the URDF joint angle in radians.

    Servos 2-6 span -pi/2..pi/2. The gripper (servo 1) spans -pi/2..0, where
    0 is open and 1000 is closed. ``grip_inverted`` swaps those two ends.
    """
    if servo_id == GRIP_SERVO_ID:
        fraction = float(position) / 1000.0
        if grip_inverted:
            fraction = 1.0 - fraction
        return -fraction * HALF_PI
    return (float(position) - 500.0) * math.pi / 1000.0


def joint_radians_to_servo(servo_id, radians, grip_inverted=False):
    """Inverse of :func:`servo_to_joint_radians`, clamped to 0-1000."""
    if servo_id == GRIP_SERVO_ID:
        fraction = -float(radians) / HALF_PI
        if grip_inverted:
            fraction = 1.0 - fraction
        position = fraction * 1000.0
    else:
        position = float(radians) * 1000.0 / math.pi + 500.0
    return max(0, min(1000, int(round(position))))


def _duration_msg(duration_cls, seconds):
    """Build a ``builtin_interfaces/Duration`` from a float number of seconds."""
    seconds = max(float(seconds), 0.0)
    sec = int(seconds)
    nanosec = int(round((seconds - sec) * 1e9))
    if nanosec >= 1000000000:
        sec += 1
        nanosec -= 1000000000
    return duration_cls(sec=sec, nanosec=nanosec)


class _Bridge:
    """Owns the hidden rclpy node, its executor thread and the action client."""

    def __init__(self, action_name, joint_states_topic, node=None):
        self._action_name = action_name
        self._joint_states_topic = joint_states_topic
        self._provided_node = node
        self._lock = threading.Lock()
        self._state_condition = threading.Condition()
        self._joint_positions = {}
        self._node = None
        self._external_node = False
        self._executor = None
        self._thread = None
        self._owns_context = False
        self._action_client = None
        self._started = False
        self._ros = {}

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    def start(self):
        with self._lock:
            if self._started:
                return
            try:
                import rclpy
                from builtin_interfaces.msg import Duration
                from control_msgs.action import FollowJointTrajectory
                from rclpy.action import ActionClient
                from rclpy.executors import SingleThreadedExecutor
                from sensor_msgs.msg import JointState
                from trajectory_msgs.msg import JointTrajectoryPoint
            except ImportError as exc:
                raise RuntimeError(_ROS_MISSING) from exc

            if not rclpy.ok():
                try:
                    rclpy.init()
                    self._owns_context = True
                except RuntimeError:
                    # Already initialized, or shut down by the caller.
                    pass

            if self._provided_node is not None:
                self._node = self._provided_node
                self._external_node = True
            else:
                try:
                    self._node = rclpy.create_node("xarm_sim_bridge")
                except Exception as exc:  # noqa: BLE001 - report init problems
                    raise RuntimeError(
                        "Could not create the xarm_sim ROS 2 node. Has the "
                        "ROS 2 context already been shut down?"
                    ) from exc

            self._ros = {
                "rclpy": rclpy,
                "Duration": Duration,
                "FollowJointTrajectory": FollowJointTrajectory,
                "ActionClient": ActionClient,
                "SingleThreadedExecutor": SingleThreadedExecutor,
                "JointState": JointState,
                "JointTrajectoryPoint": JointTrajectoryPoint,
            }

            self._node.create_subscription(
                JointState,
                self._joint_states_topic,
                self._on_joint_state,
                10,
            )
            self._action_client = ActionClient(
                self._node,
                FollowJointTrajectory,
                self._action_name,
            )

            if not self._external_node:
                self._executor = SingleThreadedExecutor()
                self._executor.add_node(self._node)
                self._thread = threading.Thread(
                    target=self._spin,
                    name="xarm-sim-bridge",
                    daemon=True,
                )
                self._thread.start()

            self._started = True

    def _spin(self):
        try:
            self._executor.spin()
        except Exception:  # noqa: BLE001 - the process is going away
            pass

    def shutdown(self):
        with self._lock:
            executor = self._executor
            self._executor = None
            if executor is not None:
                try:
                    executor.shutdown(timeout_sec=1.0)
                except Exception:  # noqa: BLE001 - best effort cleanup
                    pass

            thread = self._thread
            self._thread = None
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)

            if not self._external_node and self._node is not None:
                try:
                    self._node.destroy_node()
                except Exception:  # noqa: BLE001 - best effort cleanup
                    pass
            self._node = None
            self._started = False

            if self._owns_context:
                rclpy = self._ros.get("rclpy")
                if rclpy is not None:
                    try:
                        if rclpy.ok():
                            rclpy.shutdown()
                    except Exception:  # noqa: BLE001 - best effort cleanup
                        pass
                self._owns_context = False

    # ------------------------------------------------------------------
    # Joint state feedback
    # ------------------------------------------------------------------

    def _on_joint_state(self, message):
        with self._state_condition:
            for name, position in zip(message.name, message.position):
                self._joint_positions[name] = float(position)
            self._state_condition.notify_all()

    def read_positions(self, joint_names, timeout=1.0):
        """Return the latest known positions for ``joint_names``.

        Waits up to ``timeout`` seconds for the first message. Joints that are
        missing from ``/joint_states`` are simply absent from the result.
        """
        self.start()
        deadline = time.monotonic() + max(float(timeout), 0.0)
        with self._state_condition:
            while not self._joint_positions:
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    break
                self._state_condition.wait(remaining)
            return {
                name: self._joint_positions[name]
                for name in joint_names
                if name in self._joint_positions
            }

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _wait_for_server(self, timeout):
        deadline = time.monotonic() + max(float(timeout), 0.0)
        while not self._action_client.server_is_ready():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def _derive_duration(self, targets):
        """Pick a sensible duration when the caller asked for zero."""
        with self._state_condition:
            current = dict(self._joint_positions)
        deltas = [
            abs(target - current[name])
            for name, target in targets.items()
            if name in current
        ]
        if not deltas:
            return 1.0
        return max(deltas) / MAX_VELOCITY

    def send(self, targets, duration, wait=False, timeout=1.0):
        """Send ``targets`` (joint name -> radians) to the controller."""
        if not targets:
            return

        self.start()
        if not self._wait_for_server(timeout):
            raise RuntimeError(_SERVER_MISSING.format(action=self._action_name))

        if duration <= 0.0:
            duration = self._derive_duration(targets)
        duration = max(float(duration), MIN_DURATION)

        goal = self._ros["FollowJointTrajectory"].Goal()
        goal.trajectory.joint_names = list(targets)

        point = self._ros["JointTrajectoryPoint"]()
        point.positions = [targets[name] for name in goal.trajectory.joint_names]
        point.velocities = [0.0] * len(goal.trajectory.joint_names)
        point.accelerations = [0.0] * len(goal.trajectory.joint_names)
        point.time_from_start = _duration_msg(self._ros["Duration"], duration)
        goal.trajectory.points = [point]

        send_future = self._action_client.send_goal_async(goal)
        if not wait:
            send_future.add_done_callback(self._discard_result)
            return

        goal_handle = self._await_future(send_future, timeout + 1.0)
        if goal_handle is None:
            raise RuntimeError(
                "Timed out waiting for the trajectory controller to accept "
                "the goal."
            )
        if not goal_handle.accepted:
            raise RuntimeError(
                "The trajectory controller rejected the goal. Check that it "
                "is active with: ros2 control list_controllers"
            )

        result_future = goal_handle.get_result_async()
        self._await_future(result_future, duration + timeout + 1.0)

    def _discard_result(self, future):
        try:
            goal_handle = future.result()
        except Exception:  # noqa: BLE001 - goal may have been cancelled
            return
        if goal_handle.accepted:
            try:
                goal_handle.get_result_async()
            except Exception:  # noqa: BLE001 - nothing useful to report
                pass

    @staticmethod
    def _await_future(future, timeout):
        """Wait for an rclpy future from a non-executor thread."""
        done = threading.Event()
        box = {}

        def _on_done(completed):
            try:
                box["value"] = completed.result()
            except Exception as exc:  # noqa: BLE001 - re-raised by the caller
                box["error"] = exc
            finally:
                done.set()

        future.add_done_callback(_on_done)
        if not done.wait(max(float(timeout), 0.0)):
            return None
        if "error" in box:
            return None
        return box.get("value")

    # ------------------------------------------------------------------
    # Hardware-only methods
    # ------------------------------------------------------------------

    def servo_off(self, servo_ids):
        """Turns off servo torque on real hardware; a no-op here."""
        del servo_ids

    def battery_voltage(self):
        """Return a simulated, configurable battery voltage."""
        raw = os.environ.get(
            "XARM_SIM_BATTERY_VOLTAGE", str(DEFAULT_BATTERY_VOLTAGE)
        )
        try:
            return float(raw)
        except ValueError:
            return DEFAULT_BATTERY_VOLTAGE


_bridge = None
_bridge_lock = threading.Lock()


def get_bridge(action_name=None, joint_states_topic=None, node=None):
    """Return the process-wide bridge, starting it on first use."""
    global _bridge
    if _bridge is None:
        with _bridge_lock:
            if _bridge is None:
                bridge = _Bridge(
                    action_name or DEFAULT_ACTION,
                    joint_states_topic or DEFAULT_JOINT_STATES,
                    node=node,
                )
                atexit.register(bridge.shutdown)
                _bridge = bridge
    return _bridge
