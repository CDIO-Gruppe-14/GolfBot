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

# --- Bane- og kørselsparametre (juster efter kalibrering) ---
FIELD_WIDTH_CM   = 100   # banens bredde  (1 m)
FIELD_HEIGHT_CM  = 100   # banens dybde   (1 m)
STRIP_WIDTH_CM   = 20    # bredde pr. stribe (5 striber i alt)
TURN_ARC_CM      = 50    # længde af hvert bløde kvart-sving
TURN_CONNECT_CM  = 0     # lille lige stykke mellem de to sving


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

def run_lawnmower_pattern() -> None:
    """Kør det fulde græsslåmaskine-mønster over banen."""
    mc = MotorController()

    num_strips = int(FIELD_HEIGHT_CM / STRIP_WIDTH_CM)  # antal striber = 5

    for i in range(num_strips):
        # Kør én hel stribe på tværs af banen
        mc.move_forward(FIELD_WIDTH_CM)

        # Hvis det ikke er den sidste stribe: lav et U-sving ned
        if i < num_strips - 1:
            if i % 2 == 0:
                # Lige striber (0, 2, 4, ...): retning → højre  →  U-sving til højre
                _uturn_right(mc)
            else:
                # Ulige striber (1, 3, ...): retning ← venstre  →  U-sving til venstre
                _uturn_left(mc)

    mc.stop()
    print("Rute afsluttet.")


if __name__ == "__main__":
    run_lawnmower_pattern()
