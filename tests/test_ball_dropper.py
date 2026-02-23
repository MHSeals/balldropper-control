"""Unit tests for BallDropper and Actuator (no hardware / no ROS needed)."""

import json
import pytest

# Speed up all actuator transitions
import ball_dropper_control.constants as _c
_c.ACTUATOR_TRAVEL_TIME = 0.0

from ball_dropper_control.actuator import Actuator, ActuatorState
from ball_dropper_control.ball_dropper import BallDropper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _loaded_dropper(tmp_path) -> BallDropper:
    """Return a BallDropper with all actuators closed and counter reset to 0."""
    bd = BallDropper(state_file=str(tmp_path / "state.json"))
    for act in bd.actuators:
        act.state = ActuatorState.CLOSED
    bd.next_to_drop = 0
    return bd


# ---------------------------------------------------------------------------
# Actuator unit tests
# ---------------------------------------------------------------------------

class TestActuator:
    def test_initial_state_is_open(self):
        act = Actuator(1)
        assert act.state == ActuatorState.OPEN

    def test_close_transitions_to_closed(self):
        act = Actuator(1)
        act.close()
        assert act.state == ActuatorState.CLOSED

    def test_open_transitions_to_open(self):
        act = Actuator(1)
        act.close()
        act.open()
        assert act.state == ActuatorState.OPEN

    def test_close_already_closed_is_noop(self):
        act = Actuator(1, ActuatorState.CLOSED)
        act.close()
        assert act.state == ActuatorState.CLOSED

    def test_open_already_open_is_noop(self):
        act = Actuator(1, ActuatorState.OPEN)
        act.open()
        assert act.state == ActuatorState.OPEN

    def test_is_transitioning_false_when_stable(self):
        act = Actuator(1)
        assert not act.is_transitioning()

    def test_serialization_roundtrip(self):
        act = Actuator(2, ActuatorState.CLOSED)
        restored = Actuator.from_dict(act.to_dict())
        assert restored.actuator_id == act.actuator_id
        assert restored.state == act.state


# ---------------------------------------------------------------------------
# BallDropper unit tests
# ---------------------------------------------------------------------------

class TestBallDropperDrop:
    def test_drop_rejected_when_actuators_open(self, tmp_path):
        bd = BallDropper(state_file=str(tmp_path / "state.json"))
        ok, msg = bd.drop_next()
        assert not ok
        assert "not closed" in msg

    def test_drop_full_sequence(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        for expected_ball in range(1, 4):
            ok, msg = bd.drop_next()
            assert ok, msg
            assert bd.next_to_drop == expected_ball

    def test_drop_rejected_when_no_balls_remain(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        for _ in range(3):
            bd.drop_next()
        ok, msg = bd.drop_next()
        assert not ok
        assert "no balls remaining" in msg

    def test_balls_remaining_counts_down(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        assert bd.balls_remaining() == 3
        bd.drop_next()
        assert bd.balls_remaining() == 2
        bd.drop_next()
        assert bd.balls_remaining() == 1
        bd.drop_next()
        assert bd.balls_remaining() == 0

    def test_drop_rejected_while_transitioning(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        bd.actuators[0].state = ActuatorState.TRANSITIONING_OPEN
        ok, msg = bd.drop_next()
        assert not ok
        assert "transitioning" in msg


class TestBallDropperClose:
    def test_close_actuator_succeeds(self, tmp_path):
        bd = BallDropper(state_file=str(tmp_path / "state.json"))
        ok, msg = bd.close_actuator(1)
        assert ok, msg
        assert bd.actuators[0].state == ActuatorState.CLOSED

    def test_close_already_closed_rejected(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        ok, msg = bd.close_actuator(1)
        assert not ok
        assert "already closed" in msg

    def test_close_invalid_id_rejected(self, tmp_path):
        bd = BallDropper(state_file=str(tmp_path / "state.json"))
        ok, msg = bd.close_actuator(99)
        assert not ok
        assert "invalid" in msg

    def test_close_rejected_while_transitioning(self, tmp_path):
        bd = BallDropper(state_file=str(tmp_path / "state.json"))
        bd.actuators[0].state = ActuatorState.TRANSITIONING_OPEN
        ok, msg = bd.close_actuator(2)
        assert not ok
        assert "transitioning" in msg


class TestBallDropperMarkLoaded:
    def test_mark_loaded_resets_counter(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        bd.drop_next()
        assert bd.next_to_drop == 1
        bd.mark_loaded()
        assert bd.next_to_drop == 0


class TestBallDropperPersistence:
    def test_state_persists_across_restart(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        bd = _loaded_dropper(tmp_path)
        bd.state_file = state_file
        bd.drop_next()
        bd.drop_next()

        # Simulate restart
        bd2 = BallDropper(state_file=state_file)
        assert bd2.next_to_drop == 2
        assert bd2.actuators[0].state == ActuatorState.OPEN
        assert bd2.actuators[1].state == ActuatorState.OPEN
        assert bd2.actuators[2].state == ActuatorState.CLOSED

    def test_transitioning_open_settled_to_open_on_restart(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        # Write a state file with a TRANSITIONING_OPEN actuator
        data = {
            "actuators": [
                {"id": 1, "state": "TRANSITIONING_OPEN"},
                {"id": 2, "state": "CLOSED"},
                {"id": 3, "state": "CLOSED"},
            ],
            "next_to_drop": 0,
        }
        with open(state_file, "w") as f:
            json.dump(data, f)

        bd = BallDropper(state_file=state_file)
        assert bd.actuators[0].state == ActuatorState.OPEN

    def test_transitioning_closed_settled_to_closed_on_restart(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        data = {
            "actuators": [
                {"id": 1, "state": "TRANSITIONING_CLOSED"},
                {"id": 2, "state": "CLOSED"},
                {"id": 3, "state": "CLOSED"},
            ],
            "next_to_drop": 0,
        }
        with open(state_file, "w") as f:
            json.dump(data, f)

        bd = BallDropper(state_file=state_file)
        assert bd.actuators[0].state == ActuatorState.CLOSED


class TestBallDropperStatus:
    def test_status_dict_structure(self, tmp_path):
        bd = _loaded_dropper(tmp_path)
        s = bd.status_dict()
        assert "actuators" in s
        assert "next_to_drop" in s
        assert "balls_remaining" in s
        assert len(s["actuators"]) == 3
