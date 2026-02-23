"""Actuator state machine and Actuator class."""

import time
from enum import Enum

from .constants import ACTUATOR_TRAVEL_TIME, EXTEND_PINS, RETRACT_PINS

# odroid.gpio is only available on hardware. When running off-board (dev/test)
# the mock library is used instead so all pin activity is logged to stdout.
try:
    import odroid.gpio as GPIO
except ImportError:
    from . import mock_gpio as GPIO  # type: ignore[no-redef]

GPIO.setmode(GPIO.BOARD)


class ActuatorState(Enum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    TRANSITIONING_OPEN = 'TRANSITIONING_OPEN'
    TRANSITIONING_CLOSED = 'TRANSITIONING_CLOSED'


class Actuator:
    """Represents a single linear actuator with its current state."""

    def __init__(self, actuator_id: int, state: ActuatorState = ActuatorState.OPEN):
        self.actuator_id = actuator_id
        self.state = state
        GPIO.setup(RETRACT_PINS[actuator_id], GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(EXTEND_PINS[actuator_id], GPIO.OUT, initial=GPIO.LOW)

    def open(self) -> None:
        """Open the actuator. Blocks for ACTUATOR_TRAVEL_TIME seconds."""
        if self.state == ActuatorState.OPEN:
            return
        self.state = ActuatorState.TRANSITIONING_OPEN
        GPIO.output(RETRACT_PINS[self.actuator_id], GPIO.HIGH)
        time.sleep(ACTUATOR_TRAVEL_TIME)
        GPIO.output(RETRACT_PINS[self.actuator_id], GPIO.LOW)  # limit switch stops travel
        self.state = ActuatorState.OPEN

    def close(self) -> None:
        """Close the actuator. Blocks for ACTUATOR_TRAVEL_TIME seconds."""
        if self.state == ActuatorState.CLOSED:
            return
        self.state = ActuatorState.TRANSITIONING_CLOSED
        GPIO.output(EXTEND_PINS[self.actuator_id], GPIO.HIGH)
        time.sleep(ACTUATOR_TRAVEL_TIME)
        GPIO.output(EXTEND_PINS[self.actuator_id], GPIO.LOW)  # limit switch stops travel
        self.state = ActuatorState.CLOSED

    def is_transitioning(self) -> bool:
        return self.state in (
            ActuatorState.TRANSITIONING_OPEN,
            ActuatorState.TRANSITIONING_CLOSED,
        )

    def to_dict(self) -> dict:
        return {'id': self.actuator_id, 'state': self.state.value}

    @classmethod
    def from_dict(cls, data: dict) -> 'Actuator':
        return cls(data['id'], ActuatorState(data['state']))
