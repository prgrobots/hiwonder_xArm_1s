"""Unit tests for the servo-string parsing and conversion helpers."""

import math

import pytest

from learm_ros2.sim_commands import (
    command_to_positions,
    parse_command,
    servo_to_rad,
)


def test_parse_valid():
    assert parse_command("12/23/56/78/89/100") == [12, 23, 56, 78, 89, 100]


def test_parse_allows_whitespace_and_other_separators():
    assert parse_command(" 500 / 500 / 500 / 500 / 500 / 500 ") == [500] * 6
    assert parse_command("500,500,500,500,500,500") == [500] * 6
    assert parse_command("500;500;500;500;500;500") == [500] * 6


def test_parse_rejects_wrong_count():
    with pytest.raises(ValueError):
        parse_command("1/2/3")
    with pytest.raises(ValueError):
        parse_command("1/2/3/4/5/6/7")


def test_parse_rejects_out_of_range():
    with pytest.raises(ValueError):
        parse_command("0/0/0/0/0/1001")
    with pytest.raises(ValueError):
        parse_command("-1/0/0/0/0/0")


def test_parse_rejects_non_integers():
    with pytest.raises(ValueError):
        parse_command("a/b/c/d/e/f")
    with pytest.raises(ValueError):
        parse_command("500.0/500/500/500/500/500")


def test_servo_to_rad():
    assert servo_to_rad(500) == pytest.approx(0.0)
    assert servo_to_rad(0) == pytest.approx(-math.pi / 2.0)
    assert servo_to_rad(1000) == pytest.approx(math.pi / 2.0)


def test_command_to_positions_order_and_grip():
    positions = command_to_positions([0, 500, 500, 500, 500, 500])

    # grip is fully open, every other joint is centred.
    assert positions[0] == pytest.approx(0.0)
    assert positions[1:] == pytest.approx([0.0] * 5)

    closed = command_to_positions([1000, 500, 500, 500, 500, 500])
    assert closed[0] == pytest.approx(-math.pi / 2.0)


def test_grip_can_be_inverted():
    positions = command_to_positions([0, 500, 500, 500, 500, 500], grip_inverted=True)
    assert positions[0] == pytest.approx(-math.pi / 2.0)
