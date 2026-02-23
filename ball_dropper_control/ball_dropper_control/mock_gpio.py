"""
Mock implementation of the odroid.gpio interface.

Used automatically on non-ODroid hardware when the real odroid.gpio library is
not available. All calls are no-ops that print what would have happened on real
hardware, so you can verify correct pin behaviour during development.
"""

import logging

logger = logging.getLogger(__name__)

# Mirror the constants from the real odroid.gpio API
BOARD = 'BOARD'
BCM = 'BCM'

OUT = 'OUT'
IN = 'IN'

HIGH = 1
LOW = 0


def setmode(mode: str) -> None:
    logger.debug(f'[mock GPIO] setmode({mode})')


def setup(pin: int, direction: str, initial: int = LOW) -> None:
    level = 'HIGH' if initial == HIGH else 'LOW'
    logger.debug(f'[mock GPIO] setup(pin={pin}, direction={direction}, initial={level})')


def output(pin: int, value: int) -> None:
    level = 'HIGH' if value == HIGH else 'LOW'
    logger.info(f'[mock GPIO] output(pin={pin}, value={level})')


def input(pin: int) -> int:  # noqa: A001
    logger.debug(f'[mock GPIO] input(pin={pin}) -> LOW (mock always returns LOW)')
    return LOW


def cleanup() -> None:
    logger.debug('[mock GPIO] cleanup()')
