#!/usr/bin/env python3
"""
GolfBot -- EV3 Kommando-lytter
==============================
Lytter paa WiFi-kommandoer fra PC'en og udfoerer dem via MotorController.

Kommandoer der haandteres:
  FORWARD <cm>  -- Koer ligeud
  TURN <grader> -- Drej vilkaarlig vinkel (positiv=hoejre, negativ=venstre)
  HEADING       -- Svar med gyro-sensor vinkel
  STOP          -- Stop og luk loop
  COLLECT       -- (stub -- collector ikke implementeret endnu)
"""

import sys
import os

# Goer src-roden tilgaengelig for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # src/robot/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # CDIO/

from motor_controller import MotorController
from communication.connection import RobotServer
from communication.protocol import decode_command, encode_command, DONE, ERROR
try:
    try:
        from collector import BallCollector
    except ImportError:
        from robot.collector import BallCollector
except ImportError as e:
    print("ADVARSEL: Kunne ikke importere BallCollector (hvis du koerer på PC er dette normalt):")
    import traceback
    traceback.print_exc()
    BallCollector = None


def command_loop(server, mc, collector=None):
    """
    Hoved-loop: modtager kommandoer fra PC'en og udfoerer dem.

    :param server: RobotServer instans (WiFi-forbindelse)
    :param mc:     MotorController instans
    """
    print("Klar -- venter paa kommandoer...")

    while True:
        raw = server.receive_message()
        if raw is None:
            print("Forbindelse mistet.")
            break

        cmd, value, speed  = decode_command(raw)
        print("Modtog: {!r} | Vaerdi: {}".format(cmd, value))

        if cmd == "FORWARD":
            mc.move_forward(speed, value)
            server.send_reply(DONE)

        elif cmd == "TURN":
            mc.turn(speed, value)
            server.send_reply(DONE)

        elif cmd == "HEADING":
            server.send_reply(DONE)

        elif cmd == "STOP":
            mc.stop()
            server.send_reply(DONE)
            break

        elif cmd == "COLLECT_START":
            print("-> Modtog COLLECT_START. Er collector initialiseret?", collector is not None)
            if collector:
                collector.start_collection()
            else:
                print("FEJL: Opsamleren (BallCollector) kunne ikke startes, da objektet er None!")
            server.send_reply(DONE)

        elif cmd == "COLLECT_STOP":
            print("-> Modtog COLLECT_STOP.")
            if collector:
                collector.stop()
            server.send_reply(DONE)

        elif cmd == "COLLECT_EJECT":
            print("-> Modtog COLLECT_EJECT.")
            if collector:
                collector.eject_ball()
            server.send_reply(DONE)

        elif cmd == "COLLECT_IS_STALLED":
            if collector and collector.is_stalled():
                server.send_reply("TRUE")
            else:
                server.send_reply("FALSE")

        elif cmd == "COLLECT":
            # Stubbed full collect sequence if needed later
            print("-> Modtog COLLECT.")
            if collector:
                collector.start_collection()
            server.send_reply(DONE)

        else:
            print("Ukendt kommando: {!r}".format(cmd))
            server.send_reply(ERROR)


def main():
    server = RobotServer()
    mc     = MotorController()
    collector = BallCollector() if BallCollector else None

    print("GolfBot EV3 -- venter paa forbindelse...")
    server.wait_for_connection()

    try:
        command_loop(server, mc, collector)
    finally:
        mc.stop()
        if collector:
            collector.stop()
        server.close()
        print("Robot afsluttet.")


if __name__ == "__main__":
    main()
