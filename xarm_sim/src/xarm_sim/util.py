"""Angle/position conversions used by :class:`xarm_sim.Servo`.

These helpers are intentionally identical to the ones in the original
``xarm`` package, including the exact error messages, so that code which
depends on their behavior keeps working unchanged.
"""


class Util:
    """Static helpers mirroring ``xarm.util.Util``."""

    @staticmethod
    def _lerp(i, j, k):
        return float((1 - k) * i + j * k)

    @staticmethod
    def _invlerp(i, j, k):
        return float((k - i) / (j - i))

    @staticmethod
    def _x_round(x):
        return float(round(x * 4) / 4)

    @staticmethod
    def _angle_to_position(degrees):
        if not isinstance(degrees, float) or degrees < -125.0 or degrees > 125.0:
            # Message kept verbatim for compatibility with the original xarm.
            raise ValueError(
                "Parameter 'degrees' must be a float value between "
                "-125.0 and 125.0"
            )
        x = Util._x_round(degrees)
        y = Util._invlerp(-125.0, 125.0, x)
        return int(Util._lerp(0, 1000, y))

    @staticmethod
    def _position_to_angle(position):
        if not isinstance(position, int) or position < 0 or position > 1000:
            # Message kept verbatim for compatibility with the original xarm.
            raise ValueError(
                "Parameter 'position' must be and int value between 0 and 1000"
            )

        return Util._lerp(-125.0, 125.0, position / 1000)
