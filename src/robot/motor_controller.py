#!/usr/bin/env python3
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import ( WHEEL_DIAMETER_CM, AXLE_TRACK_CM, MOTOR_LEFT_PORT, MOTOR_RIGHT_PORT)

from ev3dev2.motor import LargeMotor, MoveTank, SpeedPercent

# --- Beregnede konstanter (afledt af config) ---
WHEEL_CIRCUMFERENCE_CM = math.pi * WHEEL_DIAMETER_CM      # ~21,6 cm


class MotorController:
    """Styrer EV3-tankdrevet (venstre motor: PORT B, hoejre motor: PORT D)."""

    def __init__(self):
        self.tank = MoveTank(MOTOR_LEFT_PORT, MOTOR_RIGHT_PORT)

    # ------------------------------------------------------------------
    # Grundlaeggende bevaegelser
    # ------------------------------------------------------------------

    def move_forward(self, speed, distance_cm):
        """Koer ligeud den angivne afstand i cm."""
        rotations = distance_cm / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(speed),
            SpeedPercent(speed),
            rotations
        )


    def turn(self, speed, degrees):
        """Drej en vilkaarlig vinkel paa stedet. Positiv=hoejre, negativ=venstre."""
        arc_length = abs(degrees) / 360.0 * math.pi * AXLE_TRACK_CM
        rotations  = arc_length / WHEEL_CIRCUMFERENCE_CM
        print("TURN {:.1f} grader | speed {}% | rotations {:.3f}".format(
            degrees, speed, rotations))
        if degrees > 0:
            self.tank.on_for_rotations(
                SpeedPercent(speed), SpeedPercent(-speed), rotations)
        else:
            self.tank.on_for_rotations(
                SpeedPercent(-speed), SpeedPercent(speed), rotations)

    def stop(self):
        """Stop begge motorer."""
        self.tank.off()
