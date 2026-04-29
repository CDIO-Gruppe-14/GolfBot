#!/usr/bin/env python3
import time
import sys
import os

# Tilføj roden af projektet til sys.path så vi kan importere config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import COLLECTOR_MOTOR_PORT, COLLECTOR_SPEED

from ev3dev2.motor import MediumMotor, SpeedPercent

def test_collector():
    print("Initialiserer opsamlingsmotor på port:", COLLECTOR_MOTOR_PORT)
    try:
        # Hvis I bruger en stor motor til opsamleren, så ret MediumMotor til LargeMotor
        collector = MediumMotor(COLLECTOR_MOTOR_PORT)
    except Exception as e:
        print("Kunne ikke finde motoren. Tjek at den er tilsluttet port", COLLECTOR_MOTOR_PORT)
        print("Fejl:", e)
        return

    print(f"Koerer forlaens i 10 sekunder med {COLLECTOR_SPEED}% hastighed...")
    collector.on(SpeedPercent(COLLECTOR_SPEED))
    time.sleep(10)
    
    print("Stopper motoren...")
    collector.off()
    time.sleep(1)

    print(f"Koerer baglaens i 10 sekunder med {COLLECTOR_SPEED}% hastighed...")
    # Sætter minus foran hastigheden for at køre baglæns
    collector.on(SpeedPercent(-COLLECTOR_SPEED))
    time.sleep(10)

    print("Stopper motoren...")
    collector.off()
    print("Test afsluttet!")

if __name__ == "__main__":
    test_collector()
