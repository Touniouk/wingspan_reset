"""
Run a LEGO Mindstorms NXT motor continuously at a set speed.

Requires the nxt-python library and PyBluez for Bluetooth support:
    pip install nxt-python pybluez

Pair the NXT brick with your Mac's Bluetooth first (System Settings > Bluetooth),
then set BRICK_HOST below to its Bluetooth MAC address before running.
"""

import signal
import sys
import time

import nxt.locator
from nxt.motor import Port

# --- Configuration ---
MOTOR_PORT = Port.A       # Port.A, Port.B, or Port.C
POWER = 75                # Speed/power, range -127 (full reverse) to 127 (full forward)
BRICK_HOST = None         # Bluetooth MAC address of the brick, e.g. "00:16:53:01:02:03"
                          # (leave as None to discover nearby paired bricks)


def main():
    print("Looking for NXT brick over Bluetooth...")
    brick = nxt.locator.find(backends=["bluetooth"], host=BRICK_HOST)
    print("Connected:", brick.get_device_info()[0])

    motor = brick.get_motor(MOTOR_PORT)

    def stop_and_exit(signum=None, frame=None):
        print("\nStopping motor...")
        motor.brake()
        brick.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop_and_exit)

    print(f"Running motor on port {MOTOR_PORT} at power {POWER}. Press Ctrl+C to stop.")
    motor.run(power=POWER)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
