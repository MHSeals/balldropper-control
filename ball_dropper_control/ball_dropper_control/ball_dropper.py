"""
BallDropper — manages the 3-actuator ball dropper state, persistence, and commands.

Thread safety: all public methods acquire self._lock before mutating state.
"""

import json
import os
import threading

from .actuator import Actuator, ActuatorState
from .constants import STATE_FILE


class BallDropper:
    NUM_ACTUATORS = 3

    def __init__(self, state_file: str = STATE_FILE, on_state_change=None):
        """
        *on_state_change* is an optional zero-argument callable invoked
        whenever an actuator state changes (including TRANSITIONING states).
        Useful for publishing status updates immediately on each transition.
        """
        self.state_file = state_file
        self._on_state_change = on_state_change or (lambda: None)
        self._lock = threading.Lock()

        if os.path.exists(state_file):
            self._load_state()
        else:
            # Default: all actuators open, dropper empty
            self.actuators = [Actuator(i + 1) for i in range(self.NUM_ACTUATORS)]
            self.next_to_drop = 0  # 0-based index into self.actuators

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        with open(self.state_file, 'r') as f:
            data = json.load(f)
        self.actuators = [Actuator.from_dict(a) for a in data['actuators']]
        self.next_to_drop = data['next_to_drop']
        # If the node was killed mid-transition, settle conservatively:
        # TRANSITIONING_OPEN  → OPEN
        # TRANSITIONING_CLOSED → CLOSED
        for act in self.actuators:
            if act.state == ActuatorState.TRANSITIONING_OPEN:
                act.state = ActuatorState.OPEN
            elif act.state == ActuatorState.TRANSITIONING_CLOSED:
                act.state = ActuatorState.CLOSED

    def _save_state(self) -> None:
        """Persist current state to disk. Must be called while holding self._lock."""
        data = {
            'actuators': [a.to_dict() for a in self.actuators],
            'next_to_drop': self.next_to_drop,
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_any_transitioning(self) -> bool:
        return any(a.is_transitioning() for a in self.actuators)

    def balls_remaining(self) -> int:
        return self.NUM_ACTUATORS - self.next_to_drop

    def status_dict(self) -> dict:
        return {
            'actuators': [a.to_dict() for a in self.actuators],
            'next_to_drop': self.next_to_drop,
            'balls_remaining': self.balls_remaining(),
        }

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def drop_next(self) -> tuple[bool, str]:
        """
        Open the next actuator in FIFO order to release a ball.
        Blocks for ACTUATOR_TRAVEL_TIME while the actuator travels.
        Returns (success, message).
        """
        with self._lock:
            if self.is_any_transitioning():
                return False, 'Rejected: an actuator is currently transitioning.'
            if self.next_to_drop >= self.NUM_ACTUATORS:
                return False, 'Rejected: no balls remaining.'
            actuator = self.actuators[self.next_to_drop]
            if actuator.state != ActuatorState.CLOSED:
                return (
                    False,
                    f'Rejected: actuator {actuator.actuator_id} is not closed '
                    f'(state={actuator.state.value}).',
                )
            def _on_transitioning():
                self._save_state()
                self._on_state_change()

            actuator.open(on_transitioning=_on_transitioning)
            self.next_to_drop += 1
            self._save_state()
            return True, f'Ball {self.next_to_drop} dropped via actuator {actuator.actuator_id}.'

    def open_actuator(self, actuator_id: int) -> tuple[bool, str]:
        """
        Open a specific actuator by 1-based ID.
        Used by the loading CLI to open all actuators before loading.
        Blocks for ACTUATOR_TRAVEL_TIME while the actuator travels.
        Returns (success, message).
        """
        with self._lock:
            if self.is_any_transitioning():
                return False, 'Rejected: an actuator is currently transitioning.'
            idx = actuator_id - 1
            if idx < 0 or idx >= self.NUM_ACTUATORS:
                return False, f'Rejected: invalid actuator ID {actuator_id}.'
            actuator = self.actuators[idx]
            if actuator.state == ActuatorState.OPEN:
                return True, f'Actuator {actuator_id} is already open.'
            def _on_transitioning():
                self._save_state()
                self._on_state_change()

            actuator.open(on_transitioning=_on_transitioning)
            self._save_state()
            return True, f'Actuator {actuator_id} opened.'

    def close_actuator(self, actuator_id: int) -> tuple[bool, str]:
        """
        Close a specific actuator by 1-based ID.
        Used by the loading CLI.
        Blocks for ACTUATOR_TRAVEL_TIME while the actuator travels.
        Returns (success, message).
        """
        with self._lock:
            if self.is_any_transitioning():
                return False, 'Rejected: an actuator is currently transitioning.'
            idx = actuator_id - 1
            if idx < 0 or idx >= self.NUM_ACTUATORS:
                return False, f'Rejected: invalid actuator ID {actuator_id}.'
            actuator = self.actuators[idx]
            if actuator.state == ActuatorState.CLOSED:
                return False, f'Rejected: actuator {actuator_id} is already closed.'
            def _on_transitioning():
                self._save_state()
                self._on_state_change()

            actuator.close(on_transitioning=_on_transitioning)
            self._save_state()
            return True, f'Actuator {actuator_id} closed.'

    def mark_loaded(self) -> None:
        """
        Reset the drop counter to 0 after a complete loading sequence.
        Called by the load CLI once all 3 actuators are closed and loaded.
        """
        with self._lock:
            self.next_to_drop = 0
            self._save_state()
