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
    print("--- INTEGRATIONSTEST: KoeR + OPSAML ---")
    
    # Initialiser hardware-klasserne
    try:
        mc = MotorController()
        collector = BallCollector()
    except Exception as e:
        print("Fejl under initialisering af hardware:", e)
        return

    # Lille nedtaelling saa I kan naa at saette robotten paa gulvet foran bolden
    print("Testen starter om 3 sekunder... Goer bolden klar paa gulvet!")
    time.sleep(3)

    # 1. Start opsamlingsbaandet (suger ind)
    print("\n[1/3] Starter opsamlingsbaandet...")
    collector.start_collection()
    time.sleep(0.5) # Lad baandet fae omdrejninger inden koersel

    # 2. Koer ligeud henover bolden
    # Vaerdien (f.eks. 50 cm) kan I justere, saa det passer med jeres testbane
    afstand_cm = 50
    print("[2/3] Korer {} cm ligeud...".format(afstand_cm))
    mc.move_forward(afstand_cm)

    # 3. Koerslen blokerer koden, saa naar vi naar hertil, er de 50 cm koert faerdig.
    # Vi lader baandet koere i 1 sekund ekstra for at sikre, bolden er helt inde.
    print("[3/3] Korsel faerdig. Venter 1 sekund paa slutfaser...")
    time.sleep(5)

    # 4. Ryd op og stop alt
    print("Stopper alle motorer. Test fuldfoert!")
    collector.stop()
    mc.stop()

if __name__ == "__main__":
    main()