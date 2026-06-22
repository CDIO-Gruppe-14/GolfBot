import sys
import os
import time

# Sørg for at moduler fra src/ kan importeres
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.main import setup
from src.server.phases.detection import detect_balls
from src.server.phases.ball_collection import collect_ball

def test_ball_collection_phase():
    """
    Kører fuld setup, detekterer en rigtig bold med kameraet
    og tester opsamlingsfasen direkte for at se om stall-logikken virker.
    """
    print("Kører fuldt setup (Starter Kamera, ArUco, og EV3 Forbindelse)...")
    ctx = setup()
    
    if not ctx:
        print("Setup fejlede. Tjek kamera og EV3 forbindelse.")
        return False

    try:
        print("\n=== SETUP FÆRDIG ===")
        print("Læg venligst en bold foran robotten.")
        time.sleep(2)
        
        # Forsøg at finde en bold via computer vision
        balls = None
        for i in range(5):
            print(f"Leder efter bold (forsøg {i+1}/5)...")
            balls = detect_balls(ctx)
            if balls and len(balls) > 0:
                break
            time.sleep(1)
            
        if not balls:
            print("\nFandt ingen bolde. Prøv at justere lys/placering og kør testen igen.")
            return False
            
        target_ball = balls[0]
        print(f"\n✅ Bold fundet!")
        print(f"Farve: {target_ball.class_name}")
        print(f"Koordinater: ({target_ball.x:.1f}, {target_ball.y:.1f})")
        
        print("\n>>> GØR KLAR TIL AT BLOKERE MOTOREN MED HÅNDEN FOR AT TESTE STALL! <<<")
        print("Starter collect_ball() om 3 sekunder...")
        time.sleep(3)
        
        # Kør opsamlingsfasen på den bold vi rent faktisk fandt
        collect_ball(ctx, target_ball)
        
        print("\nTest afsluttet. Fasen fuldførte koden som forventet.")
        
    finally:
        print("Lukker server og frigiver kamera...")
        if ctx.client:
            ctx.client.close()
        if ctx.camera:
            ctx.camera.release()

if __name__ == "__main__":
    test_ball_collection_phase()
