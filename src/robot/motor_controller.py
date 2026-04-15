#!/usr/bin/env python3
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import WHEEL_DIAMETER_CM, AXLE_TRACK_CM, MOTOR_SPEED

from ev3dev2.motor import LargeMotor, OUTPUT_B, OUTPUT_D, MoveTank, SpeedPercent

# --- Beregnede konstanter (afledt af config) ---
WHEEL_CIRCUMFERENCE_CM = math.pi * WHEEL_DIAMETER_CM      # ~21,6 cm


class MotorController:
    """Styrer EV3-tankdrevet (venstre motor: PORT B, højre motor: PORT D)."""

    def __init__(self):
        self.tank = MoveTank(OUTPUT_B, OUTPUT_D)

    # ------------------------------------------------------------------
    # Grundlæggende bevægelser
    # ------------------------------------------------------------------

    def move_forward(self, distance_cm: float) -> None:
        """Kør ligeud den angivne afstand i cm."""
        rotations = distance_cm / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(MOTOR_SPEED),
            SpeedPercent(MOTOR_SPEED),
            rotations
        )

    def turn_right_90(self) -> None:
        """Drej 90 grader til højre på stedet (pivot-drej)."""
        # Arc = (pi/4) * akselbredde  =>  begge hjul drejer modsatte veje
        rotations = (math.pi * AXLE_TRACK_CM / 4) / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(MOTOR_SPEED),   # venstre hjul fremad
            SpeedPercent(-MOTOR_SPEED),  # højre hjul bagud
            rotations
        )

    def turn_left_90(self) -> None:
        """Drej 90 grader til venstre på stedet (pivot-drej)."""
        rotations = (math.pi * AXLE_TRACK_CM / 4) / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(-MOTOR_SPEED),  # venstre hjul bagud
            SpeedPercent(MOTOR_SPEED),   # højre hjul fremad
            rotations
        )

    def soft_turn_right(self, distance_cm: float) -> None:
        """Blødt højresving: venstre hjul hurtigere end højre hjul."""
        rotations = distance_cm / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(MOTOR_SPEED),
            SpeedPercent(MOTOR_SPEED // 6),  # fx 10% hvis MOTOR_SPEED=30
            rotations
        )

    def soft_turn_left(self, distance_cm: float) -> None:
        """Blødt venstresving: højre hjul hurtigere end venstre hjul."""
        rotations = distance_cm / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(MOTOR_SPEED // 6),
            SpeedPercent(MOTOR_SPEED),
            rotations
        )

    def turn(self, degrees: float) -> None:
        """Drej en vilkårlig vinkel på stedet. Positiv=højre, negativ=venstre."""
        arc_length = abs(degrees) / 360.0 * math.pi * AXLE_TRACK_CM
        rotations  = arc_length / WHEEL_CIRCUMFERENCE_CM
        if degrees > 0:
            self.tank.on_for_rotations(
                SpeedPercent(MOTOR_SPEED), SpeedPercent(-MOTOR_SPEED), rotations)
        else:
            self.tank.on_for_rotations(
                SpeedPercent(-MOTOR_SPEED), SpeedPercent(MOTOR_SPEED), rotations)

    def stop(self) -> None:
        """Stop begge motorer."""
        self.tank.off()
