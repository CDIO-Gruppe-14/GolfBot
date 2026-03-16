import math
from ev3dev2.motor import LargeMotor, OUTPUT_B, OUTPUT_C, MoveTank, SpeedPercent

# --- Kalibreringskonstanter ---
WHEEL_DIAMETER_CM  = 5.6                                  # hjuldiameter i cm
WHEEL_CIRCUMFERENCE_CM = math.pi * WHEEL_DIAMETER_CM      # ~17.59 cm
AXLE_TRACK_CM      = 12.0   # afstand mellem hjulcentrene
MOTOR_SPEED        = 30     # hastighed i procent (0-100)


class MotorController:
    """Styrer EV3-tankdrevet (venstre motor: PORT B, højre motor: PORT C)."""

    def __init__(self):
        self.tank = MoveTank(OUTPUT_B, OUTPUT_C)

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
            SpeedPercent(MOTOR_SPEED // 3),  # fx 10% hvis MOTOR_SPEED=30
            rotations
        )

    def soft_turn_left(self, distance_cm: float) -> None:
        """Blødt venstresving: højre hjul hurtigere end venstre hjul."""
        rotations = distance_cm / WHEEL_CIRCUMFERENCE_CM
        self.tank.on_for_rotations(
            SpeedPercent(MOTOR_SPEED // 3),
            SpeedPercent(MOTOR_SPEED),
            rotations
        )

    def stop(self) -> None:
        """Stop begge motorer."""
        self.tank.off()
