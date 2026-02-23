"""Shared constants for the ball dropper package."""

import os

ACTUATOR_TRAVEL_TIME = 1.0  # seconds for an actuator to fully open or close

# GPIO (gpiod) configuration.
# RETRACT: pulls actuator back (open). EXTEND: pushes forward (close).
# NEVER assert both pins for the same actuator simultaneously.
# Values are gpiochip line offsets (gpiochip3, J2 header pins).
# Actuator 1: retract=J2-8  (offset 16), extend=J2-10 (offset 17)
# Actuator 2: retract=J2-11 (offset 28), extend=J2-12 (offset 10)
# Actuator 3: retract=J2-13 (offset 29), extend=J2-19 (offset 26)
GPIO_CHIP = 'gpiochip3'
RETRACT_PINS: dict[int, int] = {1: 25, 2: 17, 3: 10}  # J2 pins 8, 11, 13
EXTEND_PINS: dict[int, int] = {1: 29, 2: 16, 3: 28}   # J2 pins 10, 12, 19

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_PKG_DIR, "ball_dropper_state.json")
LOCK_FILE = os.path.join(_PKG_DIR, "ball_dropper.lock")
