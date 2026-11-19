"""Tests for Controller argument handling, using a fake ROS bridge."""

import math

import pytest

import xarm_sim
import xarm_sim.controller as controller_module
from xarm_sim.controller import Controller
from xarm_sim.servo import Servo
from xarm_sim.util import Util


class FakeBridge:
    """Records commands instead of talking to ROS."""

    def __init__(self):
        self.sent = []
        self.joint_positions = {}
        self.off = []
        self.voltage = 7.4

    def send(self, targets, duration, wait=False, timeout=1.0):
        self.sent.append(
            {
                "targets": dict(targets),
                "duration": duration,
                "wait": wait,
                "timeout": timeout,
            }
        )

    def read_positions(self, joint_names, timeout=1.0):
        return {
            name: self.joint_positions[name]
            for name in joint_names
            if name in self.joint_positions
        }

    def servo_off(self, servo_ids):
        self.off.append(list(servo_ids))

    def battery_voltage(self):
        return self.voltage


@pytest.fixture
def bridge(monkeypatch):
    fake = FakeBridge()
    monkeypatch.setattr(controller_module, "get_bridge", lambda **kwargs: fake)
    return fake


def test_package_exports_the_original_api():
    assert xarm_sim.VERSION == xarm_sim.__version__
    assert xarm_sim.Controller is Controller
    assert xarm_sim.Servo is Servo
    assert xarm_sim.Util is Util


@pytest.mark.parametrize("com_port", ["USB", "USB497223563535", "COM5", "SIM"])
def test_accepts_hardware_port_names(bridge, com_port):
    Controller(com_port)


@pytest.mark.parametrize("com_port", ["/dev/ttyUSB0", "ttyUSB0", "", None, 123])
def test_rejects_unknown_port_names(bridge, com_port):
    with pytest.raises(ValueError, match="com_port"):
        Controller(com_port)


def test_set_position_with_id(bridge):
    arm = Controller("USB")
    arm.setPosition(2, 700)

    assert len(bridge.sent) == 1
    command = bridge.sent[0]
    assert command["targets"] == {"wrist_roll": pytest.approx(0.2 * math.pi)}
    assert command["duration"] == 1.0
    assert command["wait"] is False


def test_set_position_duration_is_milliseconds(bridge):
    arm = Controller("USB")
    arm.setPosition(2, 700, 2000)

    assert bridge.sent[0]["duration"] == 2.0


def test_set_position_wait_is_forwarded(bridge):
    arm = Controller("USB")
    arm.setPosition(2, 700, wait=True)

    assert bridge.sent[0]["wait"] is True


def test_set_position_float_is_degrees(bridge):
    arm = Controller("USB")
    arm.setPosition(2, 90.0)

    position = Util._angle_to_position(90.0)
    expected = (position - 500.0) * math.pi / 1000.0
    assert bridge.sent[0]["targets"]["wrist_roll"] == pytest.approx(expected)


def test_set_position_with_servo_object(bridge):
    arm = Controller("USB")
    arm.setPosition(Servo(3, 250))

    assert bridge.sent[0]["targets"] == {
        "wrist_flex": pytest.approx((250 - 500.0) * math.pi / 1000.0)
    }


def test_set_position_with_pairs(bridge):
    arm = Controller("USB")
    arm.setPosition([[1, 200], [2, 90.0]])

    targets = bridge.sent[0]["targets"]
    assert targets["grip_left"] == pytest.approx(-0.2 * math.pi / 2.0)
    position = Util._angle_to_position(90.0)
    assert targets["wrist_roll"] == pytest.approx(
        (position - 500.0) * math.pi / 1000.0
    )


def test_set_position_with_mixed_list(bridge):
    arm = Controller("USB")
    arm.setPosition([Servo(4, 500), [5, 500], (6, 500)])

    assert set(bridge.sent[0]["targets"]) == {
        "elbow",
        "shoulder_lift",
        "shoulder_pan",
    }


def test_set_position_only_commands_named_servos(bridge):
    arm = Controller("USB")
    arm.setPosition(1, 100)

    assert list(bridge.sent[0]["targets"]) == ["grip_left"]


def test_gripper_direction(bridge):
    arm = Controller("USB")

    arm.setPosition(1, 0)
    assert bridge.sent[-1]["targets"]["grip_left"] == pytest.approx(0.0)

    arm.setPosition(1, 1000)
    assert bridge.sent[-1]["targets"]["grip_left"] == pytest.approx(
        -math.pi / 2
    )


def test_gripper_can_be_inverted(bridge):
    arm = Controller("USB", grip_inverted=True)
    arm.setPosition(1, 0)

    assert bridge.sent[-1]["targets"]["grip_left"] == pytest.approx(
        -math.pi / 2
    )


@pytest.mark.parametrize(
    "args, message",
    [
        ((1,), "Parameter 'position' missing."),
        ((1, 1001), "between 0 and 1000."),
        ((1, -1), "between 0 and 1000."),
        ((1, 200.0), "between -125.0 and 125.0."),
        ((7, 500), "servo_id"),
        (([[1, 200, 300]],), "Parameter list 'servos' is not valid."),
        (([1, 2],), "Parameter list 'servos' is not valid."),
        (("nope",), "Parameter 'servos' is not valid."),
    ],
)
def test_set_position_validates(bridge, args, message):
    arm = Controller("USB")
    with pytest.raises(ValueError, match=message):
        arm.setPosition(*args)

    assert bridge.sent == []


def test_set_position_rejects_unsupported_position_type(bridge):
    arm = Controller("USB")
    with pytest.raises(ValueError, match="must be an int"):
        arm.setPosition(1, "500")


def test_get_position_returns_units(bridge):
    bridge.joint_positions = {"wrist_roll": 0.0}
    arm = Controller("USB")

    assert arm.getPosition(2) == 500
    assert arm.getPosition(Servo(2)) == 500


def test_get_position_returns_degrees(bridge):
    bridge.joint_positions = {"wrist_roll": 0.0}
    arm = Controller("USB")

    assert arm.getPosition(2, True) == 0.0


def test_get_position_converts_the_gripper(bridge):
    bridge.joint_positions = {"grip_left": -math.pi / 2}
    arm = Controller("USB")

    assert arm.getPosition(1) == 1000


def test_get_position_updates_a_list_of_servos(bridge):
    bridge.joint_positions = {"grip_left": 0.0, "wrist_roll": 0.0}
    arm = Controller("USB")
    servos = [Servo(1), Servo(2)]

    assert arm.getPosition(servos) is None
    assert [servo.position for servo in servos] == [0, 500]
    assert [servo.angle for servo in servos] == [-125.0, 0.0]


def test_get_position_falls_back_to_the_last_command(bridge):
    arm = Controller("USB")
    arm.setPosition(2, 800)

    bridge.joint_positions = {}

    assert arm.getPosition(2) == 800


def test_get_position_raises_without_any_data(bridge):
    arm = Controller("USB")

    with pytest.raises(Exception, match="getPosition"):
        arm.getPosition(1)


def test_get_position_rejects_invalid_arguments(bridge):
    arm = Controller("USB")

    with pytest.raises(ValueError, match="Parameter 'servos'"):
        arm.getPosition("nope")
    with pytest.raises(ValueError, match="Parameter 'servos'"):
        arm.getPosition([1, 2])
    with pytest.raises(ValueError, match="servo_id"):
        arm.getPosition(7)


def test_get_position_accepts_an_empty_list(bridge):
    arm = Controller("USB")
    assert arm.getPosition([]) is None


def test_servo_off_forms(bridge):
    arm = Controller("USB")

    arm.servoOff()
    arm.servoOff(3)
    arm.servoOff(Servo(4))
    arm.servoOff([5, Servo(6)])

    assert bridge.off == [[1, 2, 3, 4, 5, 6], [3], [4], [5, 6]]


def test_servo_off_validates(bridge):
    arm = Controller("USB")

    with pytest.raises(ValueError, match="servos parameter"):
        arm.servoOff("nope")
    with pytest.raises(ValueError, match="servo_id"):
        arm.servoOff(7)


def test_battery_voltage(bridge):
    arm = Controller("USB")
    assert arm.getBatteryVoltage() == 7.4

    bridge.voltage = 8.1
    assert arm.getBatteryVoltage() == 8.1


def test_usb_event_handler_is_accepted(bridge):
    arm = Controller("USB")
    arm.usb_event_handler([1, 2, 3], None)

    assert arm._input_report == [1, 2, 3]
    assert arm._usb_recv_event is True
