"""Simulated version of the Hiwonder xArm / LeArm Python API.

The public interface is a drop-in replacement for the ``xarm`` package from
PyPI, but instead of talking to a USB-connected arm it drives the ROS 2
simulation in this repository::

    import xarm_sim as xarm

    arm = xarm.Controller("USB")
    arm.setPosition([[1, 0], [2, 500], [3, 500], [4, 500], [5, 500], [6, 500]])

``Controller`` accepts the same ``"USB"``, ``"USB<serial>"`` and ``"COMx"``
values as the original package. They are ignored because no hardware is used.
"""

from .controller import Controller
from .servo import Servo
from .util import Util

__version__ = "0.1.0"

VERSION = __version__

__all__ = ["Controller", "Servo", "Util", "VERSION", "__version__"]
