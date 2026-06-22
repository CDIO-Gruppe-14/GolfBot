#!/usr/bin/env python3
from ev3dev2.motor import MediumMotor, SpeedPercent
from config import COLLECTOR_MOTOR_PORT, COLLECTOR_SPEED

class BallCollector:
    """Haandterer opsamlingsbaandet paa GolfBot (indfoering og udspyvning)."""
    
    def __init__(self):
        try:
            self.motor = MediumMotor(COLLECTOR_MOTOR_PORT)
            print("BallCollector initialiseret paa port:", COLLECTOR_MOTOR_PORT)
        except Exception as e:
            # Undgaa non-ASCII i print-statements da EV3 terminal kan vaere ASCII-only
            err_msg = "FEJL: Kunne ikke finde opsamlingsmotor paa {}: {}".format(COLLECTOR_MOTOR_PORT, str(e))
            print(err_msg.encode('ascii', 'replace').decode('ascii'))
            self.motor = None

    def start_collection(self):
        """Starter baandet, saa det suger bolden IND i robotten."""
        if self.motor:
            # Hvis jeres test viste at minus koerer fremad:
            self.motor.on(SpeedPercent(-COLLECTOR_SPEED))
            print("Opsamlingsbaand koerer: SLYNGER IND")

    def eject_ball(self):
        """Koerer baandet baglaens, saa bolden spyttes UD."""
        if self.motor:
            # Modsat fortegn for at koere baglaens og spytte ud
            self.motor.on(SpeedPercent(COLLECTOR_SPEED))
            print("Opsamlingsbaand koerer baglaens: SPYTTER UD")

    def stop(self):
        """Stopper transportbaandet helt."""
        if self.motor:
            self.motor.off()
            print("Opsamlingsbaand stoppet.")

    def is_stalled(self):
        """Tjekker om motoren sidder fast."""
        if self.motor:
            return 'stalled' in self.motor.state
        return False