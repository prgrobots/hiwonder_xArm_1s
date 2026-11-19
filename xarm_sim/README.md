# xarm-sim

A drop-in replacement for the [`xarm`](https://pypi.org/project/xarm/) Python
package that drives the ROS 2 simulation of the
[Hiwonder xArm 1S / LeArm](https://www.hiwonder.com/products/xarm-1s) instead
of a USB-connected arm.

Existing code only needs a different import:

```python
import xarm_sim as xarm
```

`Servo`, `Controller`, `Util` and their methods behave like the original
package. `Controller("USB")`, `Controller("USB<serial>")` and
`Controller("COM5")` are all accepted and ignored, because no hardware is
used.

> The full simulator is in the
> [`hiwonder_xArm_1s`](https://github.com/prgrobots/hiwonder_xArm_1s)
> repository. This package only provides the Python API; the ROS 2 packages
> must be running for the arm to move.

---

## Table of Contents

- [Setup](#setup)
- [Methods and examples](#methods-and-examples)
  - [Connecting to the xArm](#connecting-to-the-xarm)
  - [*class* Servo](#servo)
  - [*class* Controller](#controller)
  - [setPosition](#setposition)
  - [getPosition](#getposition)
  - [servoOff](#servooff)
  - [getBatteryVoltage](#getbatteryvoltage)
- [Differences from the hardware package](#differences-from-the-hardware-package)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Setup

### Requirements

- Ubuntu 24.04 with **ROS 2 Jazzy**
- MoveIt 2 and `ros2_control`
- The ROS 2 packages from this repository

### 1. Build and start the simulator

```bash
cd ~/path/to/hiwonder_xArm_1s
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch learm_ros2 sim.launch.py
```

Leave that terminal running. RViz opens with the simulated arm.

### 2. Create a Python environment

ROS 2 is not installed from PyPI, so `xarm-sim` uses the `rclpy` that comes
with your ROS installation. On Ubuntu 24.04, a virtual environment that can
see the system packages is the cleanest way to install it:

```bash
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages ~/xarm-sim-venv
source ~/xarm-sim-venv/bin/activate
```

Source ROS **before** activating the virtual environment in every new shell.

If you would rather not use a virtual environment:

```bash
pip install --user --break-system-packages ./xarm_sim
```

### 3. Install xarm-sim

From a clone of this repository:

```bash
pip install ./xarm_sim
```

Or directly from GitHub:

```bash
pip install "git+https://github.com/prgrobots/hiwonder_xArm_1s.git#subdirectory=xarm_sim"
```

### 4. Run your code

With the simulator still running, use `xarm_sim` from any Python process that
sources the same ROS 2 environment:

```python
import xarm_sim as xarm

arm = xarm.Controller("USB")
arm.setPosition([[1, 0], [2, 500], [3, 500], [4, 500], [5, 500], [6, 500]])
```

---

## Methods and examples

### Connecting to the xArm

This example connects and reads the (simulated) battery voltage.

```python
import xarm_sim as xarm

# No hardware is opened; the argument is accepted for compatibility.
arm = xarm.Controller('USB')
print('Battery voltage in volts:', arm.getBatteryVoltage())
```

Output:

> Battery voltage in volts: 7.4

The original package lets you choose a specific arm by appending its serial
number to `"USB"`, or by naming a serial port. Both forms still work, but in
the simulation every controller talks to the same arm.

```python
import xarm_sim as xarm

arm1 = xarm.Controller('USB497223563535')
arm2 = xarm.Controller('USB497253743535')
arm3 = xarm.Controller('COM5')
```

<a id="servo"></a>
*class* **Servo**(*servo_id*__[__, *position=500*__]__)

Returns a *Servo* object. The Servo class is used to hold the position of a
given servo in units and angle.

Properties include:

- `servo_id` - ID of servo.
- `position` - Position of servo in units (0 to 1000).
- `angle` - Angle of servo in degrees (-125.0 to 125.0 in 0.25 degree integral).

The *position* parameter may be specified with an *int* value between 0 and
1000. When set to a *float* value between -125.0 to 125.0, the *angle* value
is set in degrees and rounded to a 0.25 degree integral. There are 4 servo
units per degree of angle.

> **Note:** In Python, an *int* value does not have a decimal point (500). A
> *float* value has a decimal point (0.0).

Setting position will also set the corresponding angle and vice-versa. If
*position* is not specified, it will default to `500` and *angle* will be set
to `0.0`.

```python
import xarm_sim as xarm

arm = xarm.Controller('USB')

# define servo as servo ID 1 with position 300
servo = xarm.Servo(1, 300)

print('servo ID:', servo.servo_id)
print('servo position:', servo.position)
print('servo angle:', servo.angle)
```

Output:

> servo ID: 1\
> servo position: 300\
> servo angle: -50.0

<a id="controller"></a>
*class* **Controller**(*com_port*__[__, *debug=False*__]__)

Returns a *Controller* object. In the simulation `com_port` may be a serial
port name (`COM5`), `USB`, `USB<serial>`, or `SIM`; all of them refer to the
same simulated arm.

When *debug* is `True`, each command is printed in servo units and radians.

```python
# attach to the simulated arm
arm1 = xarm.Controller('USB')
# the original serial-number and serial-port forms are accepted too
arm2 = xarm.Controller('USB497223563535')
arm3 = xarm.Controller('COM5')
# enable debug output
arm4 = xarm.Controller('COM6', True)        # positional argument
arm5 = xarm.Controller('COM7', debug=True)  # named argument
```

<a id="setposition"></a>
**setPosition**(*servos*__[__, *position=None*, *duration=1000*, *wait=False*__]__)

Moves one or more *servos* to a specified *position* over a *duration* and
optionally *wait*s during the duration.

When *servos* is an *int* value, it represents a servo ID and the *position*
parameter is required.

The *position* parameter may be an *int* to indicate a unit position (0 to
1000) or a *float* to indicate an angle in degrees (-125.0 to 125.0).

Servo IDs follow the arm's wiring order:

| ID | Joint |
|----|-------|
| 1 | gripper (`0` = open, `1000` = closed) |
| 2 | wrist roll |
| 3 | wrist flex |
| 4 | elbow |
| 5 | shoulder lift |
| 6 | shoulder pan |

Only the servos you name are commanded; every other joint holds its current
position.

```python
# Set servo ID 1 to position 500.
arm.setPosition(1, 500)
```

When *servos* is a *Servo* object, the *position* parameter is ignored. The
Servo parameter holds the position and angle.

When *servos* is a *list*, it may contain *Servo* objects or servo ID and
position pairs and the *position* parameter is ignored.

```python
import xarm_sim as xarm

arm = xarm.Controller('USB')

servo1 = xarm.Servo(1)       # assumes default unit position 500
servo2 = xarm.Servo(2, 300)  # unit position 300
servo3 = xarm.Servo(3, 90.0) # angle 90 degrees

# sets servo 1 to unit position 300 and waits the default 1 second
# before returning
arm.setPosition(1, 300, wait=True)

# sets servo 2 to unit position 700 and moves the servo at a
# rate of 2 seconds
arm.setPosition(2, 700, 2000, True)

# sets servo 3 to 45 degrees and waits the default 1 second
arm.setPosition(3, 45.0, wait=True)

# sets servo 2 to position 300 as defined above but continues to
# the next line before completing movement
arm.setPosition(servo2)

# sets servos 1 and 3 as defined and continues without waiting
arm.setPosition([servo1, servo3])

# sets servo 1 to unit position 200 and servo 2 to 90 degrees
arm.setPosition([[1, 200], [2, 90.0]], wait=True)

# Servo object and servo ID/position pairs can be combined
arm.setPosition([servo1, [2, 500], [3, 0.0]], duration=2000)
```

`duration` is in milliseconds, exactly as in the original package.

<a id="getposition"></a>
**getPosition**(*servos*__[__, *degrees=False*__]__)

Returns the current *position* of one or more *servos*, read from the
simulated arm's `/joint_states`.

By default, the *unit position* is returned. When *degrees* is `True`, the
*angle* is returned.

The *servos* parameter may be a servo ID (1 to 6), a *Servo* object, or a
list of one or more *Servo* objects.

```python
import xarm_sim as xarm

arm = xarm.Controller('USB')

servo1 = xarm.Servo(1)
servo2 = xarm.Servo(2)
servo3 = xarm.Servo(3)

# Gets the position of servo 1 in units
position = arm.getPosition(1)
print('Servo 1 position:', position)

# Gets the position of servo 2 as defined above
position = arm.getPosition(servo2)
print('Servo 2 position:', position)

# Gets the position of servo 3 in degrees
position = arm.getPosition(3, True)
print('Servo 3 position (degrees):', position)

# Fills in the position and angle of each Servo object
arm.getPosition([servo1, servo2, servo3])
print('Servo 1 position (degrees):', servo1.angle)
print('Servo 2 position (degrees):', servo2.angle)
print('Servo 3 position (degrees):', servo3.angle)
```

<a id="servooff"></a>
**servoOff**(__[__*servos=None*__]__)

On real hardware this turns off the motor of one or more servos. The
simulated arm has no torque to turn off, so this validates its arguments and
does nothing else.

```python
import xarm_sim as xarm

arm = xarm.Controller('USB')

servo2 = xarm.Servo(2)
servo5 = xarm.Servo(5)
servo6 = xarm.Servo(6)

# Turns off servo motor 1
arm.servoOff(1)

# Turns off servo motor 2
arm.servoOff(servo2)

# Turns off servo motors 3 and 4
arm.servoOff([3, 4])

# Turns off servo motors 5 and 6
arm.servoOff([servo5, servo6])
```

<a id="getbatteryvoltage"></a>
**getBatteryVoltage**()

Returns the simulated battery voltage in volts. The value is a constant
(7.4 by default) and can be changed with the `XARM_SIM_BATTERY_VOLTAGE`
environment variable.

```python
import xarm_sim as xarm

arm = xarm.Controller('USB')

battery_voltage = arm.getBatteryVoltage()
print('Battery voltage (volts):', battery_voltage)
```

---

## Differences from the hardware package

| Feature | Hardware `xarm` | `xarm-sim` |
|---------|-----------------|------------|
| Import | `import xarm` | `import xarm_sim as xarm` |
| Transport | USB HID or serial | ROS 2 `FollowJointTrajectory` action |
| `com_port` | Opens that device | Accepted and ignored; everything targets the simulation |
| `getPosition` | Serial/USB read | Live `/joint_states` feedback |
| `getBatteryVoltage` | Measured | Constant, configurable |
| `servoOff` | Cuts servo torque | No-op |
| Dependencies | `hidapi` / `pyserial` | Only the ROS 2 Python packages already in your environment |

Advanced keywords are also accepted by `Controller`: `node`, `action_name`,
`joint_states_topic`, `timeout` and `grip_inverted`. They default to the
simulation's standard configuration, so most code never needs them.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'rclpy'`**

The ROS 2 environment is not sourced. Run
`source /opt/ros/jazzy/setup.bash` in the same shell, then rerun your script.

**`Could not reach the trajectory action server`**

The simulator is not running, or it is in a different ROS 2 domain. Start it
with `ros2 launch learm_ros2 sim.launch.py`, and make sure both terminals use
the same `ROS_DOMAIN_ID`.

**`The trajectory controller rejected the goal`**

The controller is not active. Check with `ros2 control list_controllers`; the
`joint_trajectory_controller` should be `active`.

**`getPosition` raises `Function 'getPosition' recv error.`**

No `/joint_states` messages have arrived and no command has been sent yet.
Confirm the simulator is running and `ros2 topic echo /joint_states` produces
output.

---

## License

MIT. This package reimplements the public API of
[`ccourson/Hiwonder-xArm1S`](https://github.com/ccourson/Hiwonder-xArm1S),
Copyright (c) 2021 Chris Courson, also MIT licensed. See [LICENSE](LICENSE).
