import time
import sys
import os

# Tilføj rodmappen til sys.path, så vi kan importere src/ moduler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.communication.connection import PCClient
from config import ROBOT_IP
from src.server.helpers.command_utils import send_and_verify

def check_stall_over_network(client):
    """Spørger EV3'en via netværket, om motoren i øjeblikket sidder fast."""
    if client.send_command("COLLECT_IS_STALLED"):
        reply = client.wait_for_reply()
        if reply:
            return reply.strip() == "TRUE"
    return False

def test_remote_motor_stall():
    """
    Forbinder til EV3'en via PCClient.
    Sender eject-kommandoen og poller staten over netværket i et loop.
    Returnerer True hvis den er stalled uafbrudt i mere end 2 sekunder.
    """
    print(f"Forbinder til EV3 på {ROBOT_IP}...")
    client = PCClient(ROBOT_IP)
    
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til EV3.")
        return False

    try:
        print("Sender eject kommando: 'COLLECT_EJECT'...")
        success = send_and_verify(client, "COLLECT_EJECT")
        
        if not success:
            print("Fejl: Robotten bekræftede ikke COLLECT_EJECT.")
            return False
            
        print("Robotten kører eject. Prøv at blokere motoren nu!")
        
        # Sætter en timeout på 15 sekunder for hele testen
        timeout_time = time.time() + 15.0
        
        # Holder styr på hvor længe den uafbrudt har været stalled
        stall_start_time = None
        
        while time.time() < timeout_time:
            is_stalled = check_stall_over_network(client)
            
            if is_stalled:
                if stall_start_time is None:
                    # Første gang vi ser den stalled
                    stall_start_time = time.time()
                    print("EV3 melder 'stalled'! Starter timer...")
                
                # Tjekker om den har været stalled længe nok
                elif time.time() - stall_start_time >= 2.0:
                    print("Test bestået: Motoren har været stalled i mere end 2 sekunder!")
                    send_and_verify(client, "COLLECT_STOP")
                    return True
            else:
                if stall_start_time is not None:
                    print("EV3 melder ikke længere 'stalled'. Timer nulstillet.")
                    stall_start_time = None
                    
            time.sleep(0.1) # Undgå at spamme netværket for meget

        print("Test afsluttet: Motoren blev ikke blokeret længe nok (timeout efter 15 sek).")
        send_and_verify(client, "COLLECT_STOP")
        return False

    finally:
        client.close()

if __name__ == "__main__":
    test_remote_motor_stall()
