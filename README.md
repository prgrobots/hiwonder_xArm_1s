# hiwonder_xArm_1s — ROS 2 simulation

![alt text](image.png)

A ROS 2 (Jazzy) simulation of the [Hiwonder xArm 1S / LeArm](https://www.hiwonder.com/products/xarm-1s?variant=32436121894999),
a 6-DOF aluminium robotic arm. It runs entirely on your computer — **no
physical arm, USB connection, or Gazebo required**.

The simulated arm is displayed in RViz and can be driven in two ways:

1. publishing a string of servo positions (the student-facing interface), or
2. planning and executing motions with MoveIt.

---

## Packages

| Name | Description |
|------|-------------|
| `learm_ros2` | `sim_commands` node and the top-level `sim.launch.py`. |
| `learm_ros2_description` | URDF/xacro, meshes, and mock `ros2_control` configuration. |
| `learm_ros2_moveit_config` | MoveIt config (SRDF, kinematics, OMPL, controllers) and RViz layout. |

---

## Requirements

- Ubuntu 24.04 with **ROS 2 Jazzy**
- MoveIt 2 and ros2_control

```bash
sudo apt install \
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
/xarm/command (std_msgs/String)
        │
        ▼
   sim_commands ──FollowJointTrajectory──▶ joint_trajectory_controller
                                                  │
                                      ros2_control mock hardware
                                      (mock_components/GenericSystem)
                                                  │
                                             /joint_states
                                             ├──▶ robot_state_publisher ──▶ RViz
                                             └──▶ move_group
```

No hardware plugin is used: the `<ros2_control>` block in
`learm_ros2_description/urdf/learm.urdf.xacro` loads
`mock_components/GenericSystem`, which accepts position commands and reports
the resulting joint states.

---

## Tests

```bash
colcon test --packages-select learm_ros2
colcon test-result --verbose
```
