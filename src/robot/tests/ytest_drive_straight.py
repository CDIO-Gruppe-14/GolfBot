#!/usr/bin/env python3
import time
import sys
import os
import math

# Gør roden af projektet tilgængelig
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motor_controller import MotorController
from config import WHEEL_DIAMETER_CM, MOTOR_LEFT_PORT, MOTOR_RIGHT_PORT

# Beregn omkreds
WHEEL_CIRCUMFERENCE_CM = math.pi * WHEEL_DIAMETER_CM

def test_drive_accuracy(target_distance_cm=10.0):
    print("\n================================================")
    print(f" STARTER VERIFIKATIONSTEST: LIGEUD KØRSEL")
    print("================================================")
    
    try:
        mc = MotorController()
    except Exception as e:
        print("Fejl ved initialisering af MotorController:", e)
        return

    # Tilpas formatet DIREKTE her (Laver f.eks. "B" om til "ev3-ports:outB")
    try:
        left_motor = mc.tank.motors[f"ev3-ports:out{MOTOR_LEFT_PORT.upper()}"]
        right_motor = mc.tank.motors[f"ev3-ports:out{MOTOR_RIGHT_PORT.upper()}"]
    except KeyError:
        # Sikkerhedshegn hvis jeres version af MoveTank har mappet dem anderledes
        left_motor = mc.tank.left_motor
        right_motor = mc.tank.right_motor

    # 1. Aflæs startpositioner
    start_left = left_motor.position
    start_right = right_motor.position
    print(f"[STATUS] Start-encodere -> Venstre: {start_left}°, Højre: {start_right}°")

    # 2. Udfør kørsel
    print(f"\n[ACTION] Sender kommando: Kør {target_distance_cm} cm...")
    mc.move_forward(target_distance_cm)
    
    # Lille pause for at sikre at motorerne står helt stille
    time.sleep(0.5)

    # 3. Aflæs slutpositioner
    end_left = left_motor.position
    end_right = right_motor.position
    print(f"[STATUS] Slut-encodere  -> Venstre: {end_left}°, Højre: {end_right}°")

    # 4. Beregn faktisk kørte grader
    degrees_left = abs(end_left - start_left)
    degrees_right = abs(end_right - start_right)

    # 5. Omregn kørte grader til centimeter
    dist_left_cm = (degrees_left / 360.0) * WHEEL_CIRCUMFERENCE_CM
    dist_right_cm = (degrees_right / 360.0) * WHEEL_CIRCUMFERENCE_CM
    
    avg_dist_cm = (dist_left_cm + dist_right_cm) / 2.0
    error_margin = avg_dist_cm - target_distance_cm

    # 6. Udskriv den endelige testrapport
    print("\n================================================")
    print(" TESTRAPPORT & FEEDBACK")
    print("================================================")
    print(f"Kommanderet afstand:  {target_distance_cm:.2f} cm")
    print(f"Hjul Venstre målt:    {dist_left_cm:.2f} cm ({degrees_left}°)")
    print(f"Hjul Højre målt:      {dist_right_cm:.2f} cm ({degrees_right}°)")
    print(f"Gennemsnitlig kørsel: {avg_dist_cm:.2f} cm")
    print("------------------------------------------------")
    print(f"INTERN FEJLMARGIN:    {error_margin:+.2f} cm")
    print("================================================\n")

    if abs(error_margin) <= 0.5:
        print("✅ KONKLUSION: Hardware udførte kommandoen acceptabelt.")
    else:
        print("⚠️ KONKLUSION: Stor afvigelse! Tjek slør i gearene eller hjuldiameter.")

if __name__ == "__main__":
    test_drive_accuracy(10.0)