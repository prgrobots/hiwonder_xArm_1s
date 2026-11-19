"""Compare xarm_sim against a vendored copy of the original xarm package."""

from xarm_sim.servo import Servo
from xarm_sim.util import Util
from tests.reference.servo import Servo as ReferenceServo
from tests.reference.util import Util as ReferenceUtil


def test_servo_matches_for_every_position():
    for position in range(1001):
        ours = Servo(1, position)
        reference = ReferenceServo(1, position)
        assert ours.servo_id == reference.servo_id
        assert ours.position == reference.position
        assert ours.angle == reference.angle


def test_servo_matches_for_every_quarter_degree():
    for i in range(-500, 501):
        angle = i / 4
        ours = Servo(1, angle)
        reference = ReferenceServo(1, angle)
        assert ours.position == reference.position
        assert ours.angle == reference.angle


def test_angle_conversion_matches():
    for i in range(-12500, 12501):
        angle = i / 100
        assert Util._angle_to_position(angle) == (
            ReferenceUtil._angle_to_position(angle)
        )


def test_position_conversion_matches():
    for position in range(1001):
        assert Util._position_to_angle(position) == (
            ReferenceUtil._position_to_angle(position)
        )


def test_rounding_matches():
    for i in range(-1000, 1001):
        value = i / 1000
        assert Util._x_round(value) == ReferenceUtil._x_round(value)
