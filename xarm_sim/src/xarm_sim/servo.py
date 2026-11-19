"""The :class:`Servo` class, matching the original ``xarm.Servo`` API."""

from .util import Util


class Servo:
    """Holds a servo's position in units (0-1000) and angle (-125..125).

    ``position`` may be an ``int`` in the range 0-1000, or a ``float`` angle
    in degrees in the range -125.0 to 125.0. Floats are rounded to the
    nearest 0.25 degree, giving four servo units per degree.
    """

    def __init__(self, servo_id, position=500):
        self.servo_id = servo_id

        if isinstance(position, int):
            if position < 0 or position > 1000:
                raise ValueError(
                    "Position paramater must be between 0 and 1000"
                )
            self.__set_position(position)
        elif isinstance(position, float):
            if position < -125.0 or position > 125.0:
                raise ValueError(
                    "Degrees parameter must be between -125.0 and 125.0"
                )
            self.__set_angle(position)
        else:
            raise ValueError(
                "Position paramater must be an int between 0 and 1000 or a "
                "float between -125.0 and 125.0"
            )

    def __get_position(self):
        return self.__position

    def __set_position(self, position):
        self.__position = int(position)
        self.__angle = Util._position_to_angle(self.__position)

    def __get_angle(self):
        return self.__angle

    def __set_angle(self, degrees):
        self.__angle = float(degrees)
        self.__position = Util._angle_to_position(self.__angle)

    position = property(__get_position, __set_position)
    angle = property(__get_angle, __set_angle)
