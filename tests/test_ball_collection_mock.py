import sys
import os

# Sørg for at moduler fra src/ kan importeres
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.communication.connection import PCClient
from src.server.phases.ball_collection import collect_ball
from src.entities.ball import Ball
from config import ROBOT_IP

class MockContext:
    """Et falsk kontekst-objekt til at simulere serverens state under testen."""
    def __init__(self, client):
        self.client = client
        self.iteration = 0

def test_ball_collection_mock():
    """
    Forbinder til EV3 og kører collect_ball() fasen med et fiktivt bold-objekt.
    Dette tillader os at teste opsamlingen og stall-detection logikken direkte
    uden at være afhængig af kameraet.
    """
    print(f"Forbinder til EV3 på {ROBOT_IP}...")
    client = PCClient(ROBOT_IP)
    
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til EV3.")
        return False

    try:
        # Opsæt mock objekter
        ctx = MockContext(client)
        # Vi laver en fiktiv bold på (10, 10)
        dummy_ball = Ball(x=10, y=10, class_name="orange")
        
        print("Kører collect_ball()...")
        print(">>> GØR KLAR TIL AT BLOKERE MOTOREN MED HÅNDEN FOR AT TESTE STALL! <<<")
        print("Vent til du ser '[Opsamling] Venter og tjekker om motoren staller...'\n")
        
        # Kald funktionen fra ball_collection.py som nu indeholder den nye stall logik
        collect_ball(ctx, dummy_ball)
        
        print("\nTest afsluttet. Fasen fuldførte koden som forventet.")
        
    finally:
        client.close()
        print("Forbindelse lukket.")

if __name__ == "__main__":
    test_ball_collection_mock()
