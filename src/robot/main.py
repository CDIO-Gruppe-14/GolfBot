#!/usr/bin/env python3
"""
GolfBot — EV3 Kommando-lytter
==============================
Lytter på WiFi-kommandoer fra PC'en og udfører dem via MotorController.

Kommandoer der håndteres:
  FORWARD <cm>  — Kør ligeud
  TURN <grader> — Drej vilkårlig vinkel (positiv=højre, negativ=venstre)
  HEADING       — Svar med gyro-sensor vinkel
  STOP          — Stop og luk loop
  COLLECT       — (stub — collector ikke implementeret endnu)
"""

import sys
import os

# Gør src-roden tilgængelig for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor_controller import MotorController
from src.communication.connection import RobotServer
from src.communication.protocol import decode_command, encode_command, DONE, ERROR

# Gyro-sensor fra ev3dev2
from ev3dev2.sensor.lego import GyroSensor
from ev3dev2.sensor import INPUT_2


def command_loop(server, mc, gyro):
    """
    Hoved-loop: modtager kommandoer fra PC'en og udfører dem.

    :param server: RobotServer instans (WiFi-forbindelse)
    :param mc:     MotorController instans
    :param gyro:   GyroSensor instans
    """
    print("Klar — venter på kommandoer...")

    while True:
        raw = server.receive_message()
        if raw is None:
            print("Forbindelse mistet.")
            break

        cmd, value = decode_command(raw)
        print(f"Modtog: {cmd!r} | Værdi: {value}")

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
            # TODO: implementér collector.collect() når collector.py er færdig
            server.send_reply(DONE)

        else:
            print(f"Ukendt kommando: {cmd!r}")
            server.send_reply(ERROR)


def main():
    server = RobotServer()
    mc     = MotorController()
    gyro   = GyroSensor(INPUT_2)
    gyro.mode = 'GYRO-ANG'
    gyro.reset()  # nulstil heading ved opstart

    print("GolfBot EV3 — venter på forbindelse...")
    server.wait_for_connection()

    try:
        command_loop(server, mc, gyro)
    finally:
        mc.stop()
        server.close()
        print("Robot afsluttet.")


if __name__ == "__main__":
    main()
