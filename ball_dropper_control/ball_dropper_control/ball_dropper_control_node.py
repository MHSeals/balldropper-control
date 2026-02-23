#!/usr/bin/env python3
"""
ROS 2 node for controlling a 3-ball linear-actuator ball dropper.

Physical layout (top → bottom): actuator 1, actuator 2, actuator 3.
Drop order: actuator 1 first, then 2, then 3.
Load order: close 3, then 2, then 1 (see load_dropper.py CLI).

Only one instance of this node may run at a time (singleton via PID lock file).
Actuator state and drop progress are persisted to a JSON file so the node can
resume correctly after a restart.

ROS interfaces
--------------
Publishers:
    ball_dropper/status  (std_msgs/String)  — JSON status, published on every
                                              state change and once per second.
Services:
    ball_dropper/drop_ball          (std_srvs/Trigger) — open next actuator.
    ball_dropper/close_actuator_1   (std_srvs/Trigger) — close actuator 1.
    ball_dropper/close_actuator_2   (std_srvs/Trigger) — close actuator 2.
    ball_dropper/close_actuator_3   (std_srvs/Trigger) — close actuator 3.
    ball_dropper/mark_loaded        (std_srvs/Trigger) — reset drop counter
                                                          after a full load.
"""

import json
import os

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .ball_dropper import BallDropper
from .constants import LOCK_FILE


# ---------------------------------------------------------------------------
# Singleton helper
# ---------------------------------------------------------------------------

def _pid_is_running(pid: int) -> bool:
    """Return True if a process with the given PID is alive (POSIX)."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# ROS 2 node
# ---------------------------------------------------------------------------

class BallDropperControlNode(Node):
    """
    ROS 2 node for the ball dropper. Enforces singleton via PID lock file.
    Must be spun with MultiThreadedExecutor so the 3-second blocking actuator
    calls inside service callbacks do not starve other callbacks.
    """

    def __init__(self):
        super().__init__('ball_dropper_control')
        self._acquire_singleton_lock()
        self.ball_dropper = BallDropper(on_state_change=self._publish_status)

        # Status publisher
        # Use a dedicated callback group so the timer can fire even while a
        # service callback is blocking (e.g. during 3-second actuator travel).
        self._status_cb_group = MutuallyExclusiveCallbackGroup()
        self._status_pub = self.create_publisher(String, 'ball_dropper/status', 10)
        self._status_timer = self.create_timer(
            1.0, self._publish_status, callback_group=self._status_cb_group
        )

        # Drop service
        self._drop_srv = self.create_service(
            Trigger, 'ball_dropper/drop_ball', self._handle_drop
        )

        # Per-actuator close services (used by the load CLI)
        self._close_srvs = [
            self.create_service(
                Trigger,
                f'ball_dropper/close_actuator_{i}',
                lambda req, res, aid=i: self._handle_close(aid, req, res),
            )
            for i in range(1, 4)
        ]

        # Mark-loaded service
        self._mark_loaded_srv = self.create_service(
            Trigger, 'ball_dropper/mark_loaded', self._handle_mark_loaded
        )

        self.get_logger().info('BallDropperControlNode started.')
        self._publish_status()

    # ------------------------------------------------------------------
    # Singleton lock
    # ------------------------------------------------------------------

    def _acquire_singleton_lock(self) -> None:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                existing_pid = int(f.read().strip())
            if _pid_is_running(existing_pid):
                raise RuntimeError(
                    f'BallDropperControlNode is already running (PID {existing_pid}). '
                    'Only one instance is permitted.'
                )
            self.get_logger().warn(
                f'Stale lock file found (PID {existing_pid} not running). Overwriting.'
            )
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))

    def _release_singleton_lock(self) -> None:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

    def destroy_node(self) -> None:
        self._release_singleton_lock()
        super().destroy_node()

    # ------------------------------------------------------------------
    # Status publishing
    # ------------------------------------------------------------------

    def _publish_status(self) -> None:
        msg = String()
        msg.data = json.dumps(self.ball_dropper.status_dict())
        self._status_pub.publish(msg)

    # ------------------------------------------------------------------
    # Service callbacks
    # ------------------------------------------------------------------

    def _handle_drop(self, request, response):
        success, message = self.ball_dropper.drop_next()
        response.success = success
        response.message = message
        self._publish_status()
        self.get_logger().info(f'drop_ball: {message}')
        return response

    def _handle_close(self, actuator_id: int, request, response):
        success, message = self.ball_dropper.close_actuator(actuator_id)
        response.success = success
        response.message = message
        self._publish_status()
        self.get_logger().info(f'close_actuator_{actuator_id}: {message}')
        return response

    def _handle_mark_loaded(self, request, response):
        self.ball_dropper.mark_loaded()
        response.success = True
        response.message = 'Ball dropper marked as fully loaded (drop counter reset).'
        self._publish_status()
        self.get_logger().info('Ball dropper marked as loaded.')
        return response


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    try:
        node = BallDropperControlNode()
    except RuntimeError as e:
        print(f'ERROR: {e}')
        rclpy.shutdown()
        return

    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        print('\rShutting down BallDropperControlNode (KeyboardInterrupt)')
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
