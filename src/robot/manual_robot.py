#!/usr/bin/env python3
"""
GolfBot -- Manuel EV3 Robot
==============================
Et selvstændigt script der KUN bruges til manuel styring.
Kør dette på EV3'en i stedet for main.py, når du vil styre via WASD.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from communication.connection import RobotServer
from motor_controller import MotorController
from config import MOTOR_SPEED
from ev3dev2.motor import SpeedPercent

try:
    try:
        from collector import BallCollector
    except ImportError:
        from robot.collector import BallCollector
except ImportError as e:
    BallCollector = None


def main():
    server = RobotServer()
    mc = MotorController()
    collector = BallCollector() if BallCollector else None

    print("=====================================")
    print("  GolfBot EV3 - MANUEL STYRING       ")
    print("=====================================")
    print("Venter paa forbindelse fra PC...")
    server.wait_for_connection()

    try:
        while True:
            raw = server.receive_message()
            if raw is None:
                print("Forbindelse mistet. Stopper motorer.")
                break

            cmd = raw.strip().upper()
            
            if cmd == "FWD":
                mc.tank.on(SpeedPercent(MOTOR_SPEED), SpeedPercent(MOTOR_SPEED))
            elif cmd == "BWD":
                mc.tank.on(SpeedPercent(-MOTOR_SPEED), SpeedPercent(-MOTOR_SPEED))
            elif cmd == "LEFT":
                mc.tank.on(SpeedPercent(-MOTOR_SPEED), SpeedPercent(MOTOR_SPEED))
            elif cmd == "RIGHT":
                mc.tank.on(SpeedPercent(MOTOR_SPEED), SpeedPercent(-MOTOR_SPEED))
            elif cmd == "STOP":
                mc.tank.off()
            elif cmd == "COLLECT_FWD":
                if collector: collector.start_collection()
            elif cmd == "COLLECT_BWD":
                if collector: collector.eject_ball()
            elif cmd == "COLLECT_STOP":
                if collector: collector.stop()
            elif cmd == "EXIT":
                mc.tank.off()
                if collector: collector.stop()
                server.send_reply("DONE\n")
                break
            else:
                pass # Ignorerer ukendte
                
            # Send et simpelt svar tilbage, så PC'en ved at kommandoen er modtaget
            server.send_reply("OK\n")

    finally:
        mc.stop()
        if collector:
            collector.stop()
        server.close()
        print("Manuel robot afsluttet.")

if __name__ == "__main__":
    main()
