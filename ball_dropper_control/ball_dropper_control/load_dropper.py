#!/usr/bin/env python3
"""
Interactive CLI for loading the ball dropper.

Run this script WHILE the ball_dropper_control node is running:

    ros2 run ball_dropper_control load_dropper

Physical loading sequence:
    0. Open all actuators              →  dropper cleared / ready to receive balls
    1. Drop a ball into the open tube  →  close actuator 3  (catches ball at bottom)
    2. Drop a ball into the tube       →  close actuator 2  (catches ball in middle)
    3. Drop a ball into the tube       →  close actuator 1  (catches ball at top)

After all three actuators are closed the node's drop counter is reset to 0
so subsequent drop_ball calls start from actuator 1 again.

Prerequisites
-------------
- All three actuators must be open (the dropper must be empty) before starting.
- The ball_dropper_control node must be running and reachable over ROS.
"""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

# Loading sequence: (actuator_id, user-facing prompt)
_LOAD_STEPS: list[tuple[int, str]] = [
    (3, 'Step 1/3 — Drop a ball into the tube (it will fall to the bottom, caught by actuator 3).'),
    (2, 'Step 2/3 — Drop the next ball into the tube (caught by actuator 2).'),
    (1, 'Step 3/3 — Drop the final ball into the tube (caught by actuator 1 at the top).'),
]


class LoadDropperCLI(Node):
    """
    Minimal ROS 2 node that acts as a service client for the loading sequence.
    All interactive prompting and stdin handling runs here so the main node
    never has to block its executor on keyboard input.
    """

    _SERVICE_TIMEOUT = 5.0  # seconds to wait for a service to become available

    def __init__(self):
        super().__init__('load_dropper_cli')

        self._open_clients: dict[int, rclpy.client.Client] = {
            i: self.create_client(Trigger, f'ball_dropper/open_actuator_{i}')
            for i in (1, 2, 3)
        }
        self._close_clients: dict[int, rclpy.client.Client] = {
            i: self.create_client(Trigger, f'ball_dropper/close_actuator_{i}')
            for i in (1, 2, 3)
        }
        self._mark_loaded_client = self.create_client(
            Trigger, 'ball_dropper/mark_loaded'
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_trigger(self, client, description: str) -> bool:
        """
        Wait for *client* to be available, call it, and return whether it
        succeeded.  Prints an error message on failure.
        """
        if not client.wait_for_service(timeout_sec=self._SERVICE_TIMEOUT):
            print(
                f'\nERROR: Service not available after {self._SERVICE_TIMEOUT}s. '
                'Is the ball_dropper_control node running?'
            )
            return False

        future = client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future)

        result = future.result()
        if result is None:
            print(f'\nERROR: {description} — no response received.')
            return False
        if not result.success:
            print(f'\nERROR: {description} — {result.message}')
            return False

        print(f'  OK: {result.message}')
        return True

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_load_sequence(self) -> None:
        """Run the interactive loading sequence. Blocks until complete or aborted."""
        print()
        print('=== Ball Dropper — Loading Sequence ===')
        print('Press Ctrl-C at any time to abort.')
        input('>> Press ENTER to open all actuators and start loading...')

        # Step 0: open all actuators
        for actuator_id in (1, 2, 3):
            print(f'  Please wait — opening actuator {actuator_id}...')
            if not self._call_trigger(
                self._open_clients[actuator_id],
                f'open_actuator_{actuator_id}',
            ):
                print('\nLoading aborted.')
                return

        print()

        # Steps 1-3: load each ball then close its actuator
        for actuator_id, prompt in _LOAD_STEPS:
            print(prompt)
            input('  >> Press ENTER once the ball is in the tube...')
            print(f'  Please wait — closing actuator {actuator_id}...')

            if not self._call_trigger(
                self._close_clients[actuator_id],
                f'close_actuator_{actuator_id}',
            ):
                print('\nLoading aborted.')
                return

            print()  # blank line between steps

        print('Resetting drop counter...')
        if not self._call_trigger(self._mark_loaded_client, 'mark_loaded'):
            print('WARNING: Drop counter was not reset. Run manually if needed.')
            return

        print('\nLoading complete — all 3 balls loaded. Dropper is ready.\n')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = LoadDropperCLI()
    try:
        node.run_load_sequence()
    except KeyboardInterrupt:
        print('\nLoading cancelled by user.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
