#!/usr/bin/env python3
import time
import sys
import os

# Sørg for at imports virker på tværs af mapper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from motor_controller import MotorController
from collector import BallCollector

def main():
    print("--- INTEGRATIONSTEST: KØR + OPSAML ---")
    
    # Initialiser hardware-klasserne
    try:
        mc = MotorController()
        collector = BallCollector()
    except Exception as e:
        print("Fejl under initialisering af hardware:", e)
        return

    # Lille nedtælling så I kan nå at sætte robotten på gulvet foran bolden
    print("Testen starter om 3 sekunder... Gør bolden klar på gulvet!")
    time.sleep(3)

    # 1. Start opsamlingsbåndet (suger ind)
    print("\n[1/3] Starter opsamlingsbåndet...")
    collector.start_collection()
    time.sleep(0.5) # Lad båndet få omdrejninger inden kørsel

    # 2. Kør ligeud henover bolden
    # Værdien (f.eks. 50 cm) kan I justere, så det passer med jeres testbane
    afstand_cm = 50
    print(f"[2/3] Kører {afstand_cm} cm ligeud...")
    mc.move_forward(afstand_cm)

    # 3. Kørslen blokerer koden, så når vi når hertil, er de 50 cm kørt færdig.
    # Vi lader båndet køre i 1 sekund ekstra for at sikre, bolden er helt inde.
    print("[3/3] Kørsel færdig. Venter 1 sekund på slutfaser...")
    time.sleep(5)

    # 4. Ryd op og stop alt
    print("Stopper alle motorer. Test fuldført!")
    collector.stop()
    mc.stop()

if __name__ == "__main__":
    main()