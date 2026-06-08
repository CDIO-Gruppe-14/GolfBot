#!/usr/bin/env python3
from ev3dev2.motor import MediumMotor, SpeedPercent
from config import COLLECTOR_MOTOR_PORT, COLLECTOR_SPEED

class BallCollector:
    """Håndterer opsamlingsbåndet på GolfBot (indføring og udspyvning)."""
    
    def __init__(self):
        try:
            self.motor = MediumMotor(COLLECTOR_MOTOR_PORT)
            print("BallCollector initialiseret på port:", COLLECTOR_MOTOR_PORT)
        except Exception as e:
            print(f"FEJL: Kunne ikke finde opsamlingsmotor på {COLLECTOR_MOTOR_PORT}: {e}")
            self.motor = None

    def start_collection(self):
        """Starter båndet, så det suger bolden IND i robotten."""
        if self.motor:
            # Hvis jeres test viste at minus kører fremad:
            self.motor.on(SpeedPercent(-COLLECTOR_SPEED))
            print("Opsamlingsbånd kører: SLYNGER IND")

    def eject_ball(self):
        """Kører båndet baglæns, så bolden spyttes UD."""
        if self.motor:
            # Modsat fortegn for at køre baglæns og spytte ud
            self.motor.on(SpeedPercent(COLLECTOR_SPEED))
            print("Opsamlingsbånd kører baglæns: SPYTTER UD")

    def stop(self):
        """Stopper transportbåndet helt."""
        if self.motor:
            self.motor.off()
            print("Opsamlingsbånd stoppet.")