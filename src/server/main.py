"""
GolfBot — PC Server / Orchestrator
====================================
Hovedprogram der kører på den eksterne PC.
Binder kamera, detektion, navigationsberegning og WiFi-kommunikation sammen.

Konfiguration:
  ROBOT_IP     — IP-adressen på EV3 robotten
  MARKER_COLOR — Farveprofil-navn for robotmarkøren
  Banehjørner  — Indlæses automatisk fra calibration/field_corners.json

Start:
  python src/server/main.py
"""

import sys
import os

# src/ mappen (til relative imports inden i src/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Projekt-rod (til 'from src.vision...' og 'from config import...')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.camera import RobotCamera
from src.vision.color_detector import ColorDetector
from src.vision.robot_tracker import RobotTracker
from src.vision.ball_detector import BallDetector
from src.vision.field_map import FieldMap
from src.communication.connection import PCClient
from src.communication.protocol import encode_command, decode_command
from src.planning.command_generator import compute_navigation

from config import ROBOT_IP, MARKER_COLOR


def main():
    # --- Initialisér moduler ---
    camera    = RobotCamera()
    detector  = ColorDetector()
    detector.load_all_profiles()
    tracker   = RobotTracker(detector, marker_color=MARKER_COLOR)
    ball_det  = BallDetector(detector)
    field_map = FieldMap()  # auto-indlæser fra calibration/field_corners.json
    client    = PCClient(ROBOT_IP)

    print("Forbinder til EV3...")
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til robotten. Afslutter.")
        return

    print("Forbundet! Starter navigationsloop.\n")

    try:
        while True:
            # 1. Hent gyro-heading fra EV3
            client.send_command(encode_command("HEADING"))
            raw_heading = client.wait_for_reply()
            if raw_heading is None:
                print("Ingen heading-svar — tjek forbindelsen.")
                break
            _, heading = decode_command(raw_heading)  # fx "HEADING 182.3" → 182.3

            # 2. Tag billede og find robot + bold
            frame = camera.get_frame()
            if frame is None:
                continue

            robot = tracker.locate(frame)
            ball  = ball_det.find_nearest_ball(frame, robot_pos=(robot.x, robot.y) if robot else None)

            if robot is None:
                print("Robot ikke fundet i billedet...")
                continue
            if ball is None:
                print("Ingen bold fundet — scanning...")
                continue

            # 3. Konverter pixel-koordinater til cm
            rx, ry = field_map.pixel_to_cm(robot.x, robot.y)
            bx, by = field_map.pixel_to_cm(ball.x, ball.y)

            print(f"Robot: ({rx:.1f}, {ry:.1f}) cm  |  Bold: ({bx:.1f}, {by:.1f}) cm  |  Heading: {heading:.1f}°")

            # 4. Beregn næste kommando
            commands = compute_navigation(rx, ry, heading, bx, by)

            if not commands:
                print("Bold nået!")
                client.send_command(encode_command("COLLECT"))
                client.wait_for_reply()
                continue  # find næste bold

            # 5. Send første kommando og vent på DONE
            cmd, val = commands[0]
            print(f"→ Sender: {cmd} {val}")
            client.send_command(encode_command(cmd, val))
            reply = client.wait_for_reply()
            print(f"← Svar: {reply}")

    except KeyboardInterrupt:
        print("\nAfbrudt af bruger.")
    finally:
        client.send_command(encode_command("STOP"))
        client.close()
        camera.release()
        print("Server afsluttet.")


if __name__ == "__main__":
    main()
