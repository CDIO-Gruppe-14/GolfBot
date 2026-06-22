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
from config import COLLECTOR_MOVEMENT_CM, COLLECTOR_SPEED, SPEED_UNDER_COLLECTION


from src.communication.protocol import encode_command

def check_stall_over_network(client):
    """Spørger EV3'en via netværket, om motoren i øjeblikket sidder fast."""
    if client.send_command(encode_command("COLLECT_IS_STALLED")):
        reply = client.wait_for_reply()
        if reply:
            return reply.strip() == "TRUE"
    return False

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
    print(f"\n [Opsamling] Opsamler bold paa ({ball.x}, {ball.y})")

    # Koer roligt frem over bolden
    # COLLECTION_SPEED bruges til at styre motorhastighed (langsom koersel)
    # TODO: Implementer langsom koersel via separat kommando eller parameter
    
    print("[{}] [Opsamling] Starter motor".format(ctx.iteration))
    
    send_and_verify(ctx.client, "COLLECT_START", COLLECTOR_SPEED)

    print("[{}] [Opsamling] Koerer roligt frem over bolden...".format(ctx.iteration))
    send_and_verify(ctx.client, "FORWARD", SPEED_UNDER_COLLECTION, COLLECTOR_MOVEMENT_CM)
    
    # I stedet for bare at vente 3 sekunder, poller vi for stall.
    print("[{}] [Opsamling] Venter og tjekker om motoren staller...".format(ctx.iteration))
    timeout_time = time.time() + 3.0
    stall_start_time = None
    stalled_detected = False
    
    while time.time() < timeout_time:
        is_stalled = check_stall_over_network(ctx.client)
        if is_stalled:
            if stall_start_time is None:
                stall_start_time = time.time()
                print("[{}] [Opsamling] EV3 melder 'stalled'! Starter timer...".format(ctx.iteration))
            elif time.time() - stall_start_time >= 0.5: # Hvis stalled i 0.5 sekunder
                print("[{}] [Opsamling] Bolden sidder fast! Kører yderligere 5 cm fremad...".format(ctx.iteration))
                send_and_verify(ctx.client, "FORWARD", SPEED_UNDER_COLLECTION, 5.0)
                stalled_detected = True
                # Vent lidt ekstra efter vi er kørt frem, og stop så
                time.sleep(1.0)
                send_and_verify(ctx.client, "FORWARD", SPEED_UNDER_COLLECTION, -5.0)
                break
        else:
            stall_start_time = None
        time.sleep(0.1)

    send_and_verify(ctx.client, "COLLECT_STOP")

    print("[{}] [Opsamling] Bold opsamling afsluttet!".format(ctx.iteration))

