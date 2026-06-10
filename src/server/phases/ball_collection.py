"""
GolfBot -- Fase 4: Opsamling af Bold
=======================================
Koerer roligt frem over bold og markerer som opsamlet.
Transportbaandet koerer allerede fra opstart (startet i main.py).
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.command_utils import send_and_verify
from src.entities.ball import Ball


def collect_ball(ctx, ball):
    """
    Fase 4: Opsam bolden.

    Transportbaandet koerer allerede (startet i main.py ved opstart).
    1. Koer roligt frem over bolden
    2. Marker som opsamlet i prioritetskoeen

    Args:
        ctx: GameContext
        ball: Ball-objekt fra køen
        queue: deque med resterende bolde
    """
    ctx.iteration += 1
    print("\n [Opsamling] Opsamler bold paa ({ball.x}, {ball.y})")

    # Koer roligt frem over bolden
    # COLLECTION_SPEED bruges til at styre motorhastighed (langsom koersel)
    # TODO: Implementer langsom koersel via separat kommando eller parameter
    print("[{}] [Opsamling] Koerer roligt frem over bolden...".format(ctx.iteration))
    send_and_verify(ctx.client, "FORWARD", 5.0)
    time.sleep(0.5)

    print("[{}] [Opsamling] Bold opsamling afsluttet!")

