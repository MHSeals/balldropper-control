"""Actuator state machine and Actuator class."""

import logging
import time
from enum import Enum

import gpiod

from .constants import ACTUATOR_TRAVEL_TIME, EXTEND_PINS, GPIO_CHIP, RETRACT_PINS

log = logging.getLogger(__name__)


def _pulse(offset: int, seconds: float) -> None:
    """Assert *offset* HIGH for *seconds*, then LOW. No-op if chip unavailable."""
    try:
        with gpiod.Chip(GPIO_CHIP) as chip:
            line = chip.get_line(offset)
            line.request(consumer='ball_dropper', type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
            line.set_value(1)
            time.sleep(seconds)
            line.set_value(0)
    except Exception as exc:
        log.warning('[mock GPIO] offset=%d would pulse %.1fs (%s)', offset, seconds, exc)


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

    def open(self, on_transitioning=None) -> None:
        """Open the actuator. Blocks for ACTUATOR_TRAVEL_TIME seconds."""
        if self.state == ActuatorState.OPEN:
            return
        self.state = ActuatorState.TRANSITIONING_OPEN
        if on_transitioning is not None:
            on_transitioning()
        _pulse(RETRACT_PINS[self.actuator_id], ACTUATOR_TRAVEL_TIME)  # limit switch stops travel
        self.state = ActuatorState.OPEN

    def close(self, on_transitioning=None) -> None:
        """Close the actuator. Blocks for ACTUATOR_TRAVEL_TIME seconds."""
        if self.state == ActuatorState.CLOSED:
            return
        self.state = ActuatorState.TRANSITIONING_CLOSED
        if on_transitioning is not None:
            on_transitioning()
        _pulse(EXTEND_PINS[self.actuator_id], ACTUATOR_TRAVEL_TIME)  # limit switch stops travel
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
