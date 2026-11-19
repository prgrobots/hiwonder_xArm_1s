"""Tests for the angle/position helpers, comparing against the original."""

import pytest

from xarm_sim.util import Util
from tests.reference.util import Util as ReferenceUtil


def test_lerp_and_invlerp():
    assert Util._lerp(0, 1000, 0.5) == 500.0
    assert Util._lerp(-125.0, 125.0, 0.0) == -125.0
    assert Util._invlerp(-125.0, 125.0, 0.0) == 0.5


def test_goes_round_trip():
    assert Util._angle_to_position(0.0) == 500
    assert Util._angle_to_position(-125.0) == 0
    assert Util._angle_to_position(125.0) == 1000
    assert Util._position_to_angle(0) == -125.0
    assert Util._position_to_angle(500) == 0.0
    assert Util._position_to_angle(1000) == 125.0


def test_rounds_to_quarter_degrees():
    assert Util._x_round(0.0) == 0.0
    assert Util._x_round(0.1) == 0.0
    assert Util._x_round(0.2) == 0.25
    assert Util._x_round(-0.1) == 0.0
    assert Util._x_round(-0.2) == -0.25


def test_matches_reference_over_the_whole_range():
    for position in range(1001):
        assert Util._position_to_angle(position) == (
            ReferenceUtil._position_to_angle(position)
        )

    for i in range(-12500, 12501):
        angle = i / 100
        assert Util._angle_to_position(angle) == (
            ReferenceUtil._angle_to_position(angle)
        )


@pytest.mark.parametrize("value", [0, 1, -1, 126, "1", None])
def test_angle_to_position_rejects_non_floats(value):
    with pytest.raises(ValueError):
        Util._angle_to_position(value)
    with pytest.raises(ValueError):
        ReferenceUtil._angle_to_position(value)


@pytest.mark.parametrize("value", [-1, 1001, 0.0, "1", None])
def test_position_to_angle_rejects_invalid_ints(value):
    with pytest.raises(ValueError):
        Util._position_to_angle(value)
    with pytest.raises(ValueError):
        ReferenceUtil._position_to_angle(value)
