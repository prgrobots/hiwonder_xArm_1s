# hiwonder_xArm_1s — ROS 2 simulation

![alt text](image.png)

A ROS 2 (Jazzy) simulation of the [Hiwonder xArm 1S / LeArm](https://www.hiwonder.com/products/xarm-1s?variant=32436121894999),
a 6-DOF aluminium robotic arm. It runs entirely on your computer — **no
physical arm, USB connection, or Gazebo required**.

The simulated arm is displayed in RViz and can be driven in three ways:

1. publishing a string of servo positions (the student-facing interface),
2. calling the `xarm_sim` Python package, or
3. planning and executing motions with MoveIt.

---

## Student quick start

This walks you from a clean Ubuntu 24.04 machine to a moving arm and your own
Python program. The simulator runs in one terminal; your code runs in another.

> **You do not need the physical arm, a USB cable, or Gazebo.**

Works on Ubuntu 24.04, WSL2 (Ubuntu 24.04 with WSLg), and Ubuntu virtual
machines. If RViz cannot open, see [Troubleshooting](#troubleshooting).

### 1. Install ROS 2 Jazzy

Follow the official instructions if you do not already have it:

<https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html>

Then install the simulator dependencies:

```bash
sudo apt update
sudo apt install \
  git \
  python3-venv \
  python3-colcon-common-extensions \
  ros-jazzy-desktop \
  ros-jazzy-moveit \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers
```

Check that ROS is available:

```bash
source /opt/ros/jazzy/setup.bash
ros2 --help
```

### 2. Get and build this repository

```bash
cd ~
git clone -b xarm-sim https://github.com/prgrobots/hiwonder_xArm_1s.git
cd hiwonder_xArm_1s

source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

You must run the two `source` commands in every new terminal.

### 3. Start the simulator (terminal A)

```bash
source /opt/ros/jazzy/setup.bash
source ~/hiwonder_xArm_1s/install/setup.bash
ros2 launch learm_ros2 sim.launch.py
```

RViz opens with the arm. **Leave this terminal running.** If you have no
display, start it without RViz:

```bash
ros2 launch learm_ros2 sim.launch.py use_rviz:=false
```

With RViz, wait for these lines before running your code:

```
You can start planning now!
Ready to take commands for planning group arm.
```

Confirm the controllers are active in another terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/hiwonder_xArm_1s/install/setup.bash
ros2 control list_controllers
```

Both `joint_state_broadcaster` and `joint_trajectory_controller` should say
`active`.

### 4. Install `xarm_sim` (once, terminal B)

`xarm_sim` uses the `rclpy` that comes with ROS, so the virtual environment must
be able to see system packages:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/hiwonder_xArm_1s
python3 -m venv --system-site-packages ~/xarm-sim-venv
source ~/xarm-sim-venv/bin/activate
pip install ./xarm_sim
```

`xarm_sim` is not on PyPI yet. If you do not have the repository locally:

```bash
pip install "git+https://github.com/prgrobots/hiwonder_xArm_1s.git@xarm-sim#subdirectory=xarm_sim"
```

Source ROS **before** activating the venv in every new terminal.

### 5. Move the arm from Python

Create `first_move.py`:

```python
import xarm_sim as xarm

# The argument is accepted for compatibility with the hardware library.
arm = xarm.Controller('USB')

print('Battery voltage in volts:', arm.getBatteryVoltage())

# Servo 1 = gripper, 2 = wrist roll, 3 = wrist flex,
# 4 = elbow, 5 = shoulder lift, 6 = shoulder pan.
arm.setPosition(
    [[1, 0], [2, 500], [3, 500], [4, 500], [5, 500], [6, 500]],
    duration=1000,
    wait=True,
)

print('Current positions:', [arm.getPosition(i) for i in range(1, 7)])
```

Run it:

```bash
source /opt/ros/jazzy/setup.bash
source ~/xarm-sim-venv/bin/activate
python first_move.py
```

Expected output:

```
Battery voltage in volts: 7.4
Current positions: [0, 500, 500, 500, 500, 500]
```

You should see the arm move in RViz.

### 6. Drive the arm from a ROS 2 subscriber

This is the capstone pattern: a ROS 2 node subscribes to a topic and calls the
same `xarm` API from the callback.

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray

import xarm_sim as xarm


class XArmNode(Node):
    def __init__(self):
        super().__init__('xarm_node')
        # rclpy.init() has already run, so xarm_sim reuses that context.
        self.arm = xarm.Controller('USB', timeout=5.0)
        self.create_subscription(
            Int32MultiArray, '/target_servos', self.on_target, 10
        )
        self.get_logger().info('xarm_node ready')

    def on_target(self, message):
        pairs = [
            [index + 1, int(value)]
            for index, value in enumerate(message.data)
        ]
        try:
            self.arm.setPosition(pairs, duration=500, wait=True)
            positions = [self.arm.getPosition(i) for i in range(1, 7)]
            self.get_logger().info(f'moved to {positions}')
        except Exception as exc:
            self.get_logger().error(f'command failed: {exc}')


def main():
    rclpy.init()          # must come before Controller(...)
    node = XArmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

Send it a command from another terminal:

```bash
ros2 topic pub --once /target_servos std_msgs/msg/Int32MultiArray \
  "{data: [0, 700, 500, 800, 300, 500]}"
```

Rules that matter:

- Call `rclpy.init()` **before** `xarm.Controller(...)`.
- `wait=True` blocks that callback until the move finishes. Use `wait=False` if
  the node must stay responsive.
- Only the servos you name move; every other joint holds its position.
- A new command cancels the previous trajectory. Two programs driving the arm
  will fight over it — use one command source at a time.

---

## Packages

| Name | Description |
|------|-------------|
| `learm_ros2` | `sim_commands` node and the top-level `sim.launch.py`. |
| `learm_ros2_description` | URDF/xacro, meshes, and mock `ros2_control` configuration. |
| `learm_ros2_moveit_config` | MoveIt config (SRDF, kinematics, OMPL, controllers) and RViz layout. |
| `xarm_sim` | Pip-installable `xarm`-compatible Python API. See [`xarm_sim/README.md`](xarm_sim/README.md). |

---

## Requirements

- Ubuntu 24.04 with **ROS 2 Jazzy**
- MoveIt 2 and ros2_control

```bash
sudo apt install \
  git \
  python3-venv \
  python3-colcon-common-extensions \
  ros-jazzy-desktop \
  ros-jazzy-moveit \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers
```

---

## Build

```bash
cd ~/path/to/this/repo
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

---

## Run the simulation

```bash
ros2 launch learm_ros2 sim.launch.py
```

This starts the mock hardware, joint state broadcaster, joint trajectory
controller, MoveIt `move_group`, the command listener, and RViz2.

Useful launch arguments:

| Argument | Default | Meaning |
|----------|---------|---------|
| `use_rviz` | `true` | Start RViz2. |
| `duration` | `1.0` | Seconds each command takes to reach its target. |
| `grip_inverted` | `false` | Swap the meaning of grip values 0 and 1000. |
| `use_sim_time` | `false` | Use `/clock` (not needed for mock hardware). |

---

## Sending position commands

Publish a `std_msgs/String` on `/xarm/command` with **six servo values** in the
range **0–1000**, separated by `/`.

The order is xArm **servo-ID order 1 → 6**:

| Position | Servo ID | Joint |
|----------|----------|-------|
| 1 | 1 | grip (`0` = open, `1000` = closed) |
| 2 | 2 | wrist roll |
| 3 | 3 | wrist flex |
| 4 | 4 | elbow |
| 5 | 5 | shoulder lift |
| 6 | 6 | shoulder pan |

Center position for every joint:

```bash
ros2 topic pub --once /xarm/command std_msgs/msg/String \
  "{data: '500/500/500/500/500/500'}"
```

Fully open the gripper:

```bash
ros2 topic pub --once /xarm/command std_msgs/msg/String \
  "{data: '0/500/500/500/500/500'}"
```

Servo values are mapped to joint angles with:

- joints 2–6: `rad = (value - 500) * pi / 1000` (i.e. `0 → -90°`, `1000 → +90°`)
- grip: `0 → 0°` (open), `1000 → -90°` (closed)

If your gripper moves in the opposite direction, launch with
`grip_inverted:=true`:

```bash
ros2 launch learm_ros2 sim.launch.py grip_inverted:=true
```

A new command cancels the previous trajectory, so rapid updates do not queue up.

---

## Full `xarm_sim` API

`xarm_sim` is a pip-installable drop-in replacement for the PyPI
[`xarm`](https://pypi.org/project/xarm/) package. Code written against the
hardware library only needs a different import:

```python
import xarm_sim as xarm

arm = xarm.Controller("USB")
arm.setPosition([[1, 0], [2, 500], [3, 500], [4, 500], [5, 500], [6, 500]])
```

The [student quick start](#student-quick-start) covers installation. See
[`xarm_sim/README.md`](xarm_sim/README.md) for the full API (`Servo`,
`Controller`, `setPosition`, `getPosition`, `servoOff`, `getBatteryVoltage`),
all argument forms, and the differences from the hardware package.

---

## Using MoveIt

In RViz, open the **MotionPlanning** panel:

1. Select the `arm` planning group.
2. Drag the interactive marker or set a goal state.
3. Press **Plan**, then **Execute**.

MoveIt sends trajectories to the same `joint_trajectory_controller` used by the
string interface, so both paths drive the same simulated robot.

Useful checks:

```bash
ros2 control list_controllers
ros2 action list
ros2 topic echo /joint_states
```

---

## How it works

```
/xarm/command (std_msgs/String)          xarm_sim.Controller("USB")
        │                                         │
        ▼                                         │
   sim_commands ──FollowJointTrajectory──┐        │
                                         ▼        ▼
                              joint_trajectory_controller
                                         │
                            ros2_control mock hardware
                            (mock_components/GenericSystem)
                                         │
                                    /joint_states
                                    ├──▶ robot_state_publisher ──▶ RViz
                                    ├──▶ move_group
                                    └──▶ xarm_sim.getPosition()
```

No hardware plugin is used: the `<ros2_control>` block in
`learm_ros2_description/urdf/learm.urdf.xacro` loads
`mock_components/GenericSystem`, which accepts position commands and reports
the resulting joint states.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'rclpy'` | ROS is not sourced in **that** terminal. Run `source /opt/ros/jazzy/setup.bash`, then reactivate the venv. |
| `ModuleNotFoundError: No module named 'xarm_sim'` | The venv is not active, or you installed it in a different environment. `source ~/xarm-sim-venv/bin/activate` and `pip show xarm-sim`. |
| `pip install xarm-sim` cannot find the package | It is not on PyPI yet. Use `pip install ./xarm_sim` or the git URL from the quick start. |
| `Could not reach the trajectory action server` | The simulator is not running, or it uses a different `ROS_DOMAIN_ID`. Start `sim.launch.py` and check `ros2 action list`. |
| `The trajectory controller rejected the goal` | The controller is not active. Check `ros2 control list_controllers`; restart the launch if needed. |
| `Function 'getPosition' recv error.` | No `/joint_states` message arrived. Confirm the simulator is up with `ros2 topic echo --once /joint_states`. |
| RViz does not open | No display (SSH, headless VM). Use `ros2 launch learm_ros2 sim.launch.py use_rviz:=false` and check motion with `ros2 topic echo /joint_states`. |
| The arm keeps replaying a planned path in RViz | That is the **Loop Animation** option in the MotionPlanning display, not the simulator. Untick it in the display properties. |
| Two students move each other's arm | Every machine on the same ROS domain shares the graph. Give each student a unique domain: `export ROS_DOMAIN_ID=42`. |
| Nodes survive after stopping | Stop the launch with **Ctrl+C**. Killing the launch PID from outside can orphan child nodes; remove them with `pkill -f ros2_control_node` and `pkill -f static_transform_publisher`. |

---

## Tests

```bash
colcon test --packages-select learm_ros2
colcon test-result --verbose
```

The `xarm_sim` package has its own tests, which do not need ROS:

```bash
cd xarm_sim
pip install -e ".[test]"
pytest
```
