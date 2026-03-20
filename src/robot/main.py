"""
GolfBot – statisk græsslåmaskine-rute
======================================
Banen er 1 x 1 meter.  Robotten starter i øverste venstre hjørne,
kører til højre over hele banen, drejer ned, kører til venstre,
drejer ned, kører til højre – osv., præcis som en græsslåmaskine.

Mønster (set oppefra):
    → → → → →
              ↓
    ← ← ← ← ←
    ↓
    → → → → →
              ↓
    ← ← ← ← ←
    ...
"""

from motor_controller import MotorController
from stop_server import StopServer

# --- Bane- og kørselsparametre (juster efter kalibrering) ---
FIELD_WIDTH_CM   = 100   # banens bredde  (1 m)
FIELD_HEIGHT_CM  = 100   # banens dybde   (1 m)
STRIP_WIDTH_CM   = 20    # bredde pr. stribe (5 striber i alt)
TURN_ARC_CM      = 50    # længde af hvert bløde kvart-sving
TURN_90_CM       = 35    # længde af hvert hårde 90 graders sving
TURN_CONNECT_CM  = 0     # lille lige stykke mellem de to sving
STEP_CM          = 5     # hvor langt robotten bevæger sig i hver "move_forward" kommando (skal være mindre end TURN_ARC_CM for at sikre glatte sving)

# kun en 90 graders drejning på stedet
def _turn_right(mc: MotorController) -> None:
    """Blødt kvart-sving mod højre til næste stribe."""
    mc.soft_turn_right(TURN_90_CM)
    # mc.move_forward(TURN_CONNECT_CM)
    # mc.soft_turn_right(TURN_ARC_CM)

def _turn_left(mc: MotorController) -> None:
    """Blødt kvart-sving mod venstre til næste stribe."""
    mc.soft_turn_left(TURN_90_CM)
    # mc.move_forward(TURN_CONNECT_CM)
    # mc.soft_turn_left(TURN_ARC_CM)

# uvendinger!
def _uturn_right(mc: MotorController) -> None:
    """Blødt U-sving mod højre til næste stribe."""
    mc.soft_turn_right(TURN_ARC_CM)
    # mc.move_forward(TURN_CONNECT_CM)
    # mc.soft_turn_right(TURN_ARC_CM)

def _uturn_left(mc: MotorController) -> None:
    """Blødt U-sving mod venstre til næste stribe."""
    mc.soft_turn_left(TURN_ARC_CM)
    # mc.move_forward(TURN_CONNECT_CM)
    # mc.soft_turn_left(TURN_ARC_CM)

def move_forward_interruptible(mc: MotorController, stop_server: StopServer, distance_cm: int):
    remaining = distance_cm

    while remaining > 0:
        if stop_server.stop_requested:
            mc.stop()
            print("Robot stoppet pga. forhindring")
            return False

        step = min(STEP_CM, remaining)
        mc.move_forward(step)
        remaining -= step

    return True

def run_lawnmower_pattern() -> None:
    mc = MotorController()
    stop_server = StopServer()
    stop_server.start()

    num_strips = int(FIELD_HEIGHT_CM / STRIP_WIDTH_CM)

    for i in range(num_strips):
        ok = move_forward_interruptible(mc, stop_server, FIELD_WIDTH_CM)
        
        if not ok: # hvis der er en forhindring så er ok=false og så kører vi dodge.obstacle manøvren
            mc.dodge_obstacle()
            stop_server.reset()
            ok = True
            continue # fortsætter som normalt efter dodge manøvren

        if i < num_strips - 1:
            if i % 2 == 0:
                _uturn_right(mc)
            else:
                _uturn_left(mc)
    
    mc.stop()
    print("Ruten fuldført")


if __name__ == "__main__":
    run_lawnmower_pattern()
