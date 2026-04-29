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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import GYRO_PORT
from motor_controller import MotorController
from communication.connection import RobotServer
from communication.protocol import decode_command, encode_command, DONE, ERROR

# Gyro-sensor fra ev3dev2
from ev3dev2.sensor.lego import GyroSensor


def command_loop(server, mc, gyro):
    """
    Hoved-loop: modtager kommandoer fra PC'en og udfoerer dem.

    :param server: RobotServer instans (WiFi-forbindelse)
    :param mc:     MotorController instans
    :param gyro:   GyroSensor instans
    """
    print("Klar -- venter paa kommandoer...")

    while True:
        raw = server.receive_message()
        if raw is None:
            print("Forbindelse mistet.")
            break

        cmd, value = decode_command(raw)
        print("Modtog: {!r} | Vaerdi: {}".format(cmd, value))

        if cmd == "FORWARD":
            mc.move_forward(value)
            server.send_reply(DONE)

        elif cmd == "TURN":
            mc.turn(value)
            server.send_reply(DONE)

        elif cmd == "HEADING":
            heading = gyro.angle
            server.send_reply(encode_command("HEADING", heading))

        elif cmd == "STOP":
            mc.stop()
            server.send_reply(DONE)
            break

        elif cmd == "COLLECT":
            # TODO: implementer collector.collect() naar collector.py er faerdig
            server.send_reply(DONE)

        else:
            print("Ukendt kommando: {!r}".format(cmd))
            server.send_reply(ERROR)


def main():
    server = RobotServer()
    mc     = MotorController()
    gyro   = GyroSensor(GYRO_PORT)
    gyro.mode = 'GYRO-ANG'
    gyro.reset()  # nulstil heading ved opstart

    print("GolfBot EV3 -- venter paa forbindelse...")
    server.wait_for_connection()

    try:
        command_loop(server, mc, gyro)
    finally:
        mc.stop()
        server.close()
        print("Robot afsluttet.")


if __name__ == "__main__":
    main()
