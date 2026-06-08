"""
GolfBot -- Fase 4: Opsamling af Bold
=======================================
Starter transportbaand, koerer roligt frem over bold,
og markerer bolden som opsamlet i prioritetskoeen.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.command_utils import send_and_verify


def collect_ball(ctx, ball, queue):
    """
    Fase 4: Opsam bolden.

    1. Start motor til transportbaand (COLLECT_START)
    2. Koer roligt frem over bolden
    3. Marker som opsamlet i prioritetskoeen

    Args:
        ctx: GameContext
        ball: (x_cm, y_cm, color) tuple
        queue: BallQueue -- bolden markeres som opsamlet her
    """
    ctx.iteration += 1
    print("\n[{}] [Opsamling] Starter opsamling af {} bold paa ({:.1f}, {:.1f})".format(
        ctx.iteration, ball[2], ball[0], ball[1]))

    # Start transportbaand (opsamling)
    print("[{}] [Opsamling] Starter transportbaand...".format(ctx.iteration))
    send_and_verify(ctx.client, "COLLECT_START")
    time.sleep(0.3)

    # Koer roligt frem over bolden
    # COLLECTION_SPEED bruges til at styre motorhastighed (langsom koersel)
    # TODO: Implementer langsom koersel via separat kommando eller parameter
    print("[{}] [Opsamling] Koerer roligt frem over bolden...".format(ctx.iteration))
    send_and_verify(ctx.client, "FORWARD", 5.0)
    time.sleep(0.5)

    # Marker som opsamlet
    queue.mark_collected(ball)
    print("[{}] [Opsamling] Bold opsamlet! {} bolde tilbage i koeen.".format(
        ctx.iteration, queue.remaining()))
