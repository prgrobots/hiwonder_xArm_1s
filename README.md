# hiwonder_xArm_1s — ROS 2 simulation

![alt text](image.png)

A ROS 2 (Jazzy) simulation of the
[Hiwonder xArm 1S / LeArm](https://www.hiwonder.com/products/xarm-1s?variant=32436121894999).
It runs entirely on your computer — **no physical arm, USB connection, or
Gazebo required**.

RViz shows the arm, and your Python code drives it with the same API as the
real `xarm` package.

> **On the supplied VM?** If the build or launch fails, see
> [Fixing the supplied VM](#fixing-the-supplied-vm).

---

## 1. Install ROS 2 Jazzy

Follow the official instructions if you do not already have it:

<https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html>

Then install the dependencies:

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

---

## 2. Build this repository

```bash
cd ~
git clone https://github.com/prgrobots/hiwonder_xArm_1s.git
cd hiwonder_xArm_1s

source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

---

## 3. Start the simulator (terminal A)

```bash
source /opt/ros/jazzy/setup.bash
source ~/hiwonder_xArm_1s/install/setup.bash
ros2 launch learm_ros2 sim.launch.py
```

RViz opens with the arm. **Leave this terminal running.**

If you have no display, start it without RViz:

```bash
ros2 launch learm_ros2 sim.launch.py use_rviz:=false
```

---

## 4. Install the Python package (terminal B)

`xarm_sim` uses the `rclpy` that comes with ROS, so the virtual environment must
be able to see system packages:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/hiwonder_xArm_1s
python3 -m venv --system-site-packages ~/xarm-sim-venv
source ~/xarm-sim-venv/bin/activate
pip install ./xarm_sim
```

Source ROS **before** activating the venv in every new terminal.

---

## 5. Move the arm

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

The arm moves in RViz. `duration` is in milliseconds; `wait=True` waits for the
move to finish before returning.

---

## 6. Test the simulator without Python

With the simulator running, send six servo positions (0–1000) separated by `/`:

```bash
source /opt/ros/jazzy/setup.bash
source ~/hiwonder_xArm_1s/install/setup.bash
ros2 topic pub --once /xarm/command std_msgs/msg/String \
  "{data: '500/500/500/500/500/500'}"
```

The arm moves to its centre position.

---

## Servo IDs

Servo values are **0–1000** and use xArm servo-ID order:

| Servo ID | Joint |
|----------|-------|
| 1 | gripper (`0` = open, `1000` = closed) |
| 2 | wrist roll |
| 3 | wrist flex |
| 4 | elbow |
| 5 | shoulder lift |
| 6 | shoulder pan |

For servos 2–6, `500` is the centre position. You can also pass a `float` in
degrees instead of an `int` position, for example `arm.setPosition(4, 45.0)`.

Only the servos you name move; every other joint holds its position.

---

## Stop the simulator

Press **Ctrl+C** in terminal A.

---

## Fixing the supplied VM

The VM image has two package mismatches that can stop the build or make
`ros2_control_node`, `move_group`, and RViz exit immediately. Apply the fixes
below inside the VM.

### Build fails with `option --editable not recognized`

A newer setuptools in your user site-packages is hiding the ROS-compatible
system one. Check which one Python uses:

```bash
python3 -c "import setuptools; print(setuptools.__version__, setuptools.__file__)"
```

If it reports **84.x** from `/home/webot/.local/...`, remove the user copy:

```bash
rm -rf ~/.local/lib/python3.12/site-packages/setuptools* \
       ~/.local/lib/python3.12/site-packages/_distutils_hack \
       ~/.local/lib/python3.12/site-packages/distutils-precedence.pth
```

It should now report **68.1.2** from `/usr/lib/python3/dist-packages`:

```bash
python3 -c "import setuptools; print(setuptools.__version__, setuptools.__file__)"
```

Rebuild with symlinks — do **not** remove `--symlink-install`:

```bash
cd ~/hiwonder_xArm_1s
rm -rf build install log
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Launch fails with `undefined symbol ... Cdr9serializeEj`

You will see `exit code 127`, or RViz opens and closes, with:

```
symbol lookup error: ... undefined symbol: _ZN8eprosima7fastcdr3Cdr9serializeEj
```

The installed Fast CDR / Fast DDS packages are from different releases.
Upgrade the matching stack:

```bash
sudo apt update
sudo apt install --only-upgrade \
  ros-jazzy-fastcdr \
  ros-jazzy-fastrtps \
  ros-jazzy-fastrtps-cmake-module \
  ros-jazzy-rmw-fastrtps-cpp \
  ros-jazzy-rmw-fastrtps-shared-cpp \
  ros-jazzy-rosidl-dynamic-typesupport-fastrtps \
  ros-jazzy-rosidl-typesupport-fastrtps-c \
  ros-jazzy-rosidl-typesupport-fastrtps-cpp
```

Then restart the ROS daemon and rebuild:

```bash
source /opt/ros/jazzy/setup.bash
ros2 daemon stop
cd ~/hiwonder_xArm_1s
rm -rf build install log
colcon build --symlink-install
source install/setup.bash
```

Check the versions:

```bash
dpkg -l ros-jazzy-fastcdr ros-jazzy-fastrtps ros-jazzy-rmw-fastrtps-cpp | grep ^ii
```

Expected:

```
ros-jazzy-fastcdr          2.2.8
ros-jazzy-fastrtps         2.14.7
ros-jazzy-rmw-fastrtps-cpp 8.4.5
```

If a different `symbol lookup error` appears later, the VM has ROS packages
from mixed dates. Take a VM snapshot, then run `sudo apt upgrade` to align all
`ros-jazzy-*` packages.
