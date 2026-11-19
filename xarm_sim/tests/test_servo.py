"""Tests for the Servo class and its exact behavior."""

import pytest

from xarm_sim.servo import Servo
from xarm_sim.util import Util


def test_defaults_to_centre():
    servo = Servo(1)
    assert servo.servo_id == 1
    assert servo.position == 500
    assert servo.angle == 0.0


def test_int_position():
    servo = Servo(1, 300)
    assert servo.servo_id == 1
    assert servo.position == 300
    assert servo.angle == -50.0


def test_float_angle():
    servo = Servo(2, 45.0)
    assert servo.position == Util._angle_to_position(45.0)
    assert servo.angle == 45.0


@pytest.mark.parametrize("angle", [-125.0, -90.0, 0.0, 90.0, 125.0])
def test_angle_position_round_trip(angle):
    servo = Servo(3, angle)
    assert servo.angle == angle
    assert servo.position == Util._angle_to_position(angle)
    assert servo.position == 500 + angle * 4


def test_properties_update_each_other():
    servo = Servo(1)

    servo.position = 0
    assert servo.angle == -125.0

    servo.angle = 0.0
    assert servo.position == 500


def test_position_setter_validates():
    servo = Servo(1)
    with pytest.raises(ValueError):
        servo.position = 1001
    with pytest.raises(ValueError):
        servo.position = -1


def test_angle_setter_validates():
    servo = Servo(1)
    with pytest.raises(ValueError):
        servo.angle = 126.0
    with pytest.raises(ValueError):
        servo.angle = -126.0


@pytest.mark.parametrize("position", [-1, 1001])
def test_rejects_int_out_of_range(position):
    with pytest.raises(ValueError, match="Position paramater"):
        Servo(1, position)


@pytest.mark.parametrize("angle", [-126.0, 126.0])
def test_rejects_float_out_of_range(angle):
    with pytest.raises(ValueError, match="Degrees parameter"):
        Servo(1, angle)


@pytest.mark.parametrize("position", ["500", None])
def test_rejects_unsupported_types(position):
    with pytest.raises(ValueError):
        Servo(1, position)
