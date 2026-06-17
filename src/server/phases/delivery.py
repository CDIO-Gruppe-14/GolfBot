"""
GolfBot -- Fase 6: Aflevering
================================
Saetter transportbaand i reverse for at aflevere bolde i maalet.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.command_utils import send_and_verify

from config import COLLECTOR_SPEED


def deliver_balls(ctx):
    """
    Fase 6: Aflever bolde i maalet.

    1. Saet transportbaand i reverse (COLLECT_EJECT)
    2. Vent 3 sekunder mens transportbaandet koerer i reverse
    3. Koer 6 cm frem og 6 cm tilbage mens transportbaandet stadig koerer i reverse
    4. Bak vaek fra maalet

    Args:
        ctx: GameContext
    """
    ctx.iteration += 1
    print("\n" + "=" * 60)
    print("[{}] [Aflevering] Starter aflevering af bolde".format(ctx.iteration))

    # Saet transportbaand i reverse
    print("[{}] [Aflevering] Saetter transportbaand i reverse (EJECT)...".format(
        ctx.iteration))
    send_and_verify(ctx.client, "COLLECT_EJECT", COLLECTOR_SPEED)

    # Vent paa at boldene triller ud
    print("[{}] [Aflevering] Venter 3 sekunder paa at boldene triller ud...".format(
        ctx.iteration))
    time.sleep(3.0)

    # Rok robotten frem og tilbage mens transportbaandet stadig koerer i reverse
    print("[{}] [Aflevering] Koerer 6 cm frem mens transportbaandet koerer reverse...".format(
        ctx.iteration))
    send_and_verify(ctx.client, "FORWARD",30, 6.0)

    print("[{}] [Aflevering] Koerer 6 cm tilbage mens transportbaandet koerer reverse...".format(
        ctx.iteration))
    send_and_verify(ctx.client, "FORWARD",30 , -6.0)

    # Bak vaek fra maalet
    print("[{}] [Aflevering] Bakker 10 cm vaek fra maalet...".format(ctx.iteration))
    send_and_verify(ctx.client, "FORWARD", 30, -10.0)
    time.sleep(1.0)

    print("[{}] [Aflevering] Aflevering faerdig!".format(ctx.iteration))

    # Stop aflevringsmotor (klar til naeste runde)
    print("[{}] [Aflevering] Stopper aflevringsmotor...".format(ctx.iteration))
    send_and_verify(ctx.client, "COLLECT_STOP")
