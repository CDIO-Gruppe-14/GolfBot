"""
GolfBot — Bane-kalibrering
===========================
Klik de 4 hjørner af banen i rækkefølge for at gemme koordinaterne.

Rækkefølge:
  1. Øverst-venstre
  2. Øverst-højre
  3. Nederst-højre
  4. Nederst-venstre

Gemt til: calibration/field_corners.json

Kørsel:
  python src/vision/field_calibrator.py
  Klik 4 hjørner → tryk 's' for at gemme → 'q' for at afslutte
  'r' for at nulstille og starte forfra
"""

import cv2
import json
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from camera import RobotCamera

CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "calibration", "field_corners.json"
)

CORNER_LABELS = [
    "1: Øverst-venstre",
    "2: Øverst-højre",
    "3: Nederst-højre",
    "4: Nederst-venstre",
]
CORNER_COLORS = [
    (0, 255, 0),    # grøn
    (255, 0, 0),    # blå
    (0, 0, 255),    # rød
    (0, 255, 255),  # gul
]


class FieldCalibrator:
    def __init__(self, camera):
        self.camera = camera
        self.corners = []
        self._last_frame = None

        os.makedirs(os.path.dirname(CALIBRATION_FILE), exist_ok=True)

        cv2.namedWindow("Bane-kalibrering")
        cv2.setMouseCallback("Bane-kalibrering", self._on_click)

    def _on_click(self, event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.corners) < 4:
                self.corners.append((x, y))
                label = CORNER_LABELS[len(self.corners) - 1]
                print(f"  ✓ {label}: ({x}, {y})")

    def _draw(self, frame):
        out = frame.copy()

        # Instruktion øverst
        next_idx = len(self.corners)
        if next_idx < 4:
            txt = f"Klik hjørne {next_idx + 1}/4: {CORNER_LABELS[next_idx]}"
            cv2.putText(out, txt, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        else:
            cv2.putText(out, "Alle 4 hjørner valgt! Tryk 's' for at gemme", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

        # Tegn allerede valgte hjørner
        for i, (cx, cy) in enumerate(self.corners):
            color = CORNER_COLORS[i]
            cv2.circle(out, (cx, cy), 8, color, -1)
            cv2.putText(out, CORNER_LABELS[i], (cx + 10, cy - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Tegn polygon hvis alle 4 er valgt
        if len(self.corners) == 4:
            pts = [list(c) for c in self.corners]
            cv2.polylines(out, [np.array(pts, dtype='int32')],
                          isClosed=True, color=(0, 255, 0), thickness=2)

        # Hjælpetekst nederst
        cv2.putText(out, "'r'=nulstil  |  's'=gem  |  'q'=afslut", (10, out.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        return out

    def _save(self):
        if len(self.corners) < 4:
            print("  Ikke nok hjørner valgt endnu.")
            return False
        data = {"corners": self.corners}
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  ✓ Gemt til: {CALIBRATION_FILE}")
        print(f"    Hjørner: {self.corners}")
        return True

    def run(self):
        print("\n── GolfBot Bane-kalibrering ──")
        print("Klik de 4 hjørner i rækkefølge:")
        for lbl in CORNER_LABELS:
            print(f"  {lbl}")
        print("\n's' = gem  |  'r' = nulstil  |  'q' = afslut\n")

        try:
            while True:
                frame = self.camera.get_frame()
                if frame is None:
                    continue
                self._last_frame = frame.copy()
                annotated = self._draw(frame)
                cv2.imshow("Bane-kalibrering", annotated)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.corners = []
                    print("  Nulstillet — klik 4 hjørner igen.")
                elif key == ord('s'):
                    if self._save():
                        break
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    camera = RobotCamera()
    try:
        FieldCalibrator(camera).run()
    finally:
        camera.release()
