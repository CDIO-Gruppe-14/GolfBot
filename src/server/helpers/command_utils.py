"""
GolfBot -- Kommando-hjaelpefunktioner
=======================================
Send og verificer kommandoer til EV3.
Flyttet fra server/main.py for bedre separation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.communication.protocol import encode_command


def send_and_verify(client, cmd, value=None):
    """Send kommando og verificer svar. Returnerer reply eller None ved fejl."""
    client.send_command(encode_command(cmd, value))
    reply = client.wait_for_reply()
    if reply is None or reply.strip() != "DONE":
        print("FEJL: EV3 svarede '{}' paa kommando {} {}".format(reply, cmd, value))
        return None
    return reply
