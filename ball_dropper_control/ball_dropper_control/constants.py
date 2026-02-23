"""Shared constants for the ball dropper package."""

import os

ACTUATOR_TRAVEL_TIME = 3.0  # seconds for an actuator to fully open or close

# GPIO pin numbers using ODroid BOARD numbering.
# Retract (drop): pulls actuator back, opening the mechanism.
# Extend (reset): pushes actuator forward, closing the mechanism.
# NEVER assert both pins for the same actuator simultaneously.
RETRACT_PINS: dict[int, int] = {1: 2, 2: 4, 3: 6}  # IN1R, IN2R, IN3R
EXTEND_PINS: dict[int, int] = {1: 3, 2: 5, 3: 7}   # IN1E, IN2E, IN3E

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_PKG_DIR, 'ball_dropper_state.json')
LOCK_FILE = os.path.join(_PKG_DIR, 'ball_dropper.lock')
