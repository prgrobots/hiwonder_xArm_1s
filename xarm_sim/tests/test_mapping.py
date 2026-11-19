"""Tests for the servo-ID to joint mapping used by the simulation."""

import math

import pytest

from xarm_sim._bridge import (
    JOINT_TO_SERVO,
    SERVO_TO_JOINT,
    joint_radians_to_servo,
    servo_to_joint_radians,
)


def test_servo_order_matches_the_arm():
    assert SERVO_TO_JOINT == {
        1: "grip_left",
        2: "wrist_roll",
        3: "wrist_flex",
        4: "elbow",
        5: "shoulder_lift",
        6: "shoulder_pan",
    }
    assert JOINT_TO_SERVO["shoulder_pan"] == 6


@pytest.mark.parametrize("servo_id", range(2, 7))
def test_joint_centre_and_limits(servo_id):
    assert servo_to_joint_radians(servo_id, 500) == pytest.approx(0.0)
    assert servo_to_joint_radians(servo_id, 0) == pytest.approx(-math.pi / 2)
    assert servo_to_joint_radians(servo_id, 1000) == pytest.approx(math.pi / 2)


def test_gripper_opens_at_zero():
    assert servo_to_joint_radians(1, 0) == pytest.approx(0.0)
    assert servo_to_joint_radians(1, 1000) == pytest.approx(-math.pi / 2)


def test_gripper_can_be_inverted():
    assert servo_to_joint_radians(1, 0, grip_inverted=True) == pytest.approx(
        -math.pi / 2
    )
    assert servo_to_joint_radians(1, 1000, grip_inverted=True) == pytest.approx(
        0.0
    )


@pytest.mark.parametrize("servo_id", range(1, 7))
@pytest.mark.parametrize("grip_inverted", [False, True])
def test_position_round_trip(servo_id, grip_inverted):
    for position in range(1001):
        radians = servo_to_joint_radians(
            servo_id, position, grip_inverted=grip_inverted
        )
        assert (
            joint_radians_to_servo(
                servo_id, radians, grip_inverted=grip_inverted
            )
            == position
        )
