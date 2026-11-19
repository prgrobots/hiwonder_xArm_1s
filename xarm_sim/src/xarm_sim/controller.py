"""Drop-in replacement for ``xarm.Controller`` backed by the ROS 2 simulation."""

from ._bridge import (
    SERVO_TO_JOINT,
    get_bridge,
    joint_radians_to_servo,
    servo_to_joint_radians,
)
from .servo import Servo
from .util import Util


class Controller:
    """Controls the simulated xArm/LeArm.

    The public methods match the original ``xarm.Controller`` exactly.
    ``com_port`` accepts the same values as the hardware version (``"USB"``,
    ``"USB<serial>"`` and ``"COMx"``); they are ignored because the arm is
    simulated. ``"SIM"`` is also accepted as a more descriptive alias.
    """

    SIGNATURE = 0x55
    CMD_SERVO_MOVE = 0x03
    CMD_GET_BATTERY_VOLTAGE = 0x0F
    CMD_SERVO_STOP = 0x14
    CMD_GET_SERVO_POSITION = 0x15

    def __init__(
        self,
        com_port,
        debug=False,
        *,
        node=None,
        action_name=None,
        joint_states_topic=None,
        timeout=1.0,
        grip_inverted=False,
    ):
        if not isinstance(com_port, str) or not (
            com_port.startswith("COM")
            or com_port.startswith("USB")
            or com_port == "SIM"
        ):
            raise ValueError("com_port parameter incorrect.")

        self.debug = debug
        self._timeout = float(timeout)
        self._grip_inverted = bool(grip_inverted)
        self._last_positions = {}
        self._input_report = []
        self._usb_recv_event = False
        self._device = None
        self._is_serial = False

        self._bridge = get_bridge(
            action_name=action_name,
            joint_states_topic=joint_states_topic,
            node=node,
        )

        if self.debug:
            print("Connected to simulated xArm via", repr(com_port))

    # ------------------------------------------------------------------
    # setPosition
    # ------------------------------------------------------------------

    def setPosition(self, servos, position=None, duration=1000, wait=False):
        """Move one or more servos to a position over ``duration`` milliseconds.

        Accepts the same argument forms as the original package: a servo ID
        plus position, a :class:`Servo`, or a list of ``Servo`` objects and
        ``[id, position]`` pairs. ``duration`` is in milliseconds.
        """
        pairs = self._parse_set_position(servos, position)

        targets = {}
        commanded = {}
        for servo_id, servo_position in pairs:
            self._validate_servo_id(servo_id)
            targets[SERVO_TO_JOINT[servo_id]] = servo_to_joint_radians(
                servo_id, servo_position, self._grip_inverted
            )
            commanded[servo_id] = servo_position

        if self.debug:
            print(
                "setPosition:",
                [(servo_id, servo_position) for servo_id, servo_position in pairs],
                "duration(ms):",
                duration,
            )

        if not targets:
            return

        self._bridge.send(
            targets, duration / 1000.0, wait=wait, timeout=self._timeout
        )
        self._last_positions.update(commanded)

    def _parse_set_position(self, servos, position):
        if isinstance(servos, int):
            if position is None:
                raise ValueError("Parameter 'position' missing.")
            return [(servos, self._coerce_position(position))]

        if isinstance(servos, Servo):
            return [(servos.servo_id, servos.position)]

        if isinstance(servos, list):
            pairs = []
            for servo in servos:
                if isinstance(servo, Servo):
                    pairs.append((servo.servo_id, servo.position))
                elif (
                    isinstance(servo, (list, tuple))
                    and len(servo) == 2
                    and isinstance(servo[0], int)
                ):
                    pairs.append((servo[0], self._coerce_position(servo[1])))
                else:
                    raise ValueError("Parameter list 'servos' is not valid.")
            return pairs

        raise ValueError("Parameter 'servos' is not valid.")

    @staticmethod
    def _coerce_position(position):
        if isinstance(position, int):
            if position < 0 or position > 1000:
                raise ValueError(
                    "Parameter 'position' must be between 0 and 1000."
                )
            return position

        if isinstance(position, float):
            if position < -125.0 or position > 125.0:
                raise ValueError(
                    "Parameter 'position' must be between -125.0 and 125.0."
                )
            return Util._angle_to_position(position)

        raise ValueError(
            "Parameter 'position' must be an int between 0 and 1000 or a "
            "float between -125.0 and 125.0."
        )

    @staticmethod
    def _validate_servo_id(servo_id):
        if not isinstance(servo_id, int) or not 1 <= servo_id <= 6:
            raise ValueError("servo_id must be an integer between 1 and 6")

    # ------------------------------------------------------------------
    # getPosition
    # ------------------------------------------------------------------

    def getPosition(self, servos, degrees=False):
        """Return the current position of one or more servos.

        With a servo ID or :class:`Servo` the position is returned. With a
        list of ``Servo`` objects their ``position`` attributes are updated
        and ``None`` is returned, matching the original package.
        """
        if isinstance(servos, int):
            servo_ids = [servos]
            single = True
        elif isinstance(servos, Servo):
            servo_ids = [servos.servo_id]
            single = True
        elif isinstance(servos, list) and all(
            isinstance(servo, Servo) for servo in servos
        ):
            servo_ids = [servo.servo_id for servo in servos]
            single = False
        else:
            raise ValueError("Parameter 'servos' is not valid.")

        if not servo_ids:
            return None

        for servo_id in servo_ids:
            self._validate_servo_id(servo_id)

        joint_names = [SERVO_TO_JOINT[servo_id] for servo_id in servo_ids]
        joint_positions = self._bridge.read_positions(
            joint_names, timeout=self._timeout
        )

        positions = []
        for servo_id, joint_name in zip(servo_ids, joint_names):
            if joint_name in joint_positions:
                position = joint_radians_to_servo(
                    servo_id,
                    joint_positions[joint_name],
                    self._grip_inverted,
                )
            elif servo_id in self._last_positions:
                position = self._last_positions[servo_id]
            else:
                raise Exception("Function 'getPosition' recv error.")
            positions.append(position)

        if single:
            position = positions[0]
            if self.debug:
                print("getPosition:", servo_ids[0], position)
            return Util._position_to_angle(position) if degrees else position

        for servo, position in zip(servos, positions):
            servo.position = position

        if self.debug:
            print(
                "getPosition:",
                [(servo.servo_id, position) for servo, position in zip(
                    servos, positions
                )],
            )
        return None

    # ------------------------------------------------------------------
    # servoOff / getBatteryVoltage
    # ------------------------------------------------------------------

    def servoOff(self, servos=None):
        """Turn off one or more servo motors.

        The simulated arm has no torque to turn off, so this only validates
        the arguments.
        """
        if isinstance(servos, int):
            servo_ids = [servos]
        elif isinstance(servos, Servo):
            servo_ids = [servos.servo_id]
        elif isinstance(servos, list):
            servo_ids = []
            for servo in servos:
                if isinstance(servo, int):
                    servo_ids.append(servo)
                elif isinstance(servo, Servo):
                    servo_ids.append(servo.servo_id)
        elif servos is None:
            servo_ids = [1, 2, 3, 4, 5, 6]
        else:
            raise ValueError("servos parameter incorrect.")

        for servo_id in servo_ids:
            self._validate_servo_id(servo_id)

        self._bridge.servo_off(servo_ids)

    def getBatteryVoltage(self):
        """Return the simulated battery voltage in volts."""
        return self._bridge.battery_voltage()

    def usb_event_handler(self, data, event_type):
        """Provided for compatibility with the USB transport; does nothing."""
        del event_type
        self._input_report = data
        self._usb_recv_event = True
