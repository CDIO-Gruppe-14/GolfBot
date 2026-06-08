"""
GolfBot — Mål-kalibrering (Goal Calibrator)
===========================================
Klik på midten af Mål A og Mål B på banen for at gemme deres koordinater.

Rækkefølge:
  1. Mål A (lille)
  2. Mål B (stort)

Gemt til: calibration/goals.json

Kørsel:
  python src/vision/goal_calibrator.py
  Klik på de 2 mål → tryk 's' for at gemme → 'q' for at afslutte
  'r' for at nulstille og starte forfra
"""

import cv2
import json
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from camera import RobotCamera
from field_map import FieldMap

CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "calibration", "goals.json"
)

GOAL_LABELS = [
    "1: Mål A (lille)",
    "2: Mål B (stort)",
]
GOAL_COLORS = [
    (0, 165, 255),  # orange (OpenCV is BGR, so orange is approx 0, 165, 255)
    (255, 0, 255),  # magenta
]


class GoalCalibrator:
    def __init__(self, camera, field_map):
        self.camera = camera
        self.field_map = field_map
        self.goals_px = []
        self._last_frame = None

        os.makedirs(os.path.dirname(CALIBRATION_FILE), exist_ok=True)

        cv2.namedWindow("Maal-kalibrering")
        cv2.setMouseCallback("Maal-kalibrering", self._on_click)

    def _on_click(self, event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.goals_px) < 2:
                self.goals_px.append((x, y))
                label = GOAL_LABELS[len(self.goals_px) - 1]
                cm_x, cm_y = self.field_map.pixel_to_cm(x, y)
                print(f"  ✓ {label}: ({x} px, {y} px) -> ({cm_x:.1f} cm, {cm_y:.1f} cm)")

    def _draw(self, frame):
        out = frame.copy()

        # Instruktion øverst
        next_idx = len(self.goals_px)
        if next_idx < 2:
            txt = f"Klik {next_idx + 1}/2: {GOAL_LABELS[next_idx]}"
            cv2.putText(out, txt, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        else:
            cv2.putText(out, "Begge mål valgt! Tryk 's' for at gemme", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

        # Tegn allerede valgte mål
        for i, (cx, cy) in enumerate(self.goals_px):
            color = GOAL_COLORS[i]
            cv2.circle(out, (cx, cy), 15, color, 2)
            cv2.circle(out, (cx, cy), 2, color, -1)
            
            cm_x, cm_y = self.field_map.pixel_to_cm(cx, cy)
            label = f"{GOAL_LABELS[i]} ({cm_x:.1f}, {cm_y:.1f})"
            cv2.putText(out, label, (cx + 20, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Hjælpetekst nederst
        cv2.putText(out, "'r'=nulstil  |  's'=gem  |  'q'=afslut", (10, out.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        return out

    def _save(self):
        if len(self.goals_px) < 2:
            print("  Ikke nok mål valgt endnu.")
            return False
            
        # Konverter til cm for at gemme
        cm_coords = []
        for (px, py) in self.goals_px:
            cx, cy = self.field_map.pixel_to_cm(px, py)
            cm_coords.append((cx, cy))
            
        data = {
            "goals_px": self.goals_px,
            "goals_cm": {
                "A": cm_coords[0],
                "B": cm_coords[1]
            }
        }
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  ✓ Gemt til: {CALIBRATION_FILE}")
        print(f"    Mål A: {cm_coords[0][0]:.1f} cm, {cm_coords[0][1]:.1f} cm")
        print(f"    Mål B: {cm_coords[1][0]:.1f} cm, {cm_coords[1][1]:.1f} cm")
        return True

    def run(self):
        print("\n── GolfBot Mål-kalibrering ──")
        print("Klik på målenes midte på banen:")
        for lbl in GOAL_LABELS:
            print(f"  {lbl}")
        print("\n's' = gem  |  'r' = nulstil  |  'q' = afslut\n")

        try:
            while True:
                frame = self.camera.get_frame()
                if frame is None:
                    continue
                self._last_frame = frame.copy()
                annotated = self._draw(frame)
                cv2.imshow("Maal-kalibrering", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.goals_px = []
                    print("  Nulstillet — klik på de 2 mål igen.")
                elif key == ord('s'):
                    if self._save():
                        break
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    camera = RobotCamera()
    field_map = FieldMap()
    try:
        GoalCalibrator(camera, field_map).run()
    finally:
        camera.release()
