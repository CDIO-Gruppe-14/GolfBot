import cv2
import numpy as np
import json
import os
import sys


PROFILES_DIR = "color_profiles"


class ColorCalibrator:
    def __init__(self, camera_index=0, profile_name="default"):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.profile_name = profile_name
        self.picked_hsv = None  # HSV-værdi fra klik

        # Tolerance-værdier (justeres med slidere)
        self.h_tol = 15
        self.s_tol = 60
        self.v_tol = 60

        os.makedirs(PROFILES_DIR, exist_ok=True)
        self._setup_window()

    def _setup_window(self):
        cv2.namedWindow("Kalibrering")
        cv2.namedWindow("Maske")

        cv2.createTrackbar("H tolerance", "Kalibrering", self.h_tol, 90,  self._on_h)
        cv2.createTrackbar("S tolerance", "Kalibrering", self.s_tol, 127, self._on_s)
        cv2.createTrackbar("V tolerance", "Kalibrering", self.v_tol, 127, self._on_v)

        cv2.setMouseCallback("Kalibrering", self._on_click)

    # ── Slider callbacks ──────────────────────────────────────
    def _on_h(self, val): self.h_tol = val
    def _on_s(self, val): self.s_tol = val
    def _on_v(self, val): self.v_tol = val

    # ── Muse-klik: pick HSV fra pixel ────────────────────────
    def _on_click(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and self._last_frame is not None:
            hsv_frame = cv2.cvtColor(self._last_frame, cv2.COLOR_BGR2HSV)
            # Tag gennemsnit af 5x5 pixels omkring klikpunktet (mere robust)
            x0, y0 = max(x - 2, 0), max(y - 2, 0)
            x1, y1 = min(x + 3, hsv_frame.shape[1]), min(y + 3, hsv_frame.shape[0])
            patch = hsv_frame[y0:y1, x0:x1]
            self.picked_hsv = np.mean(patch, axis=(0, 1)).astype(int)
            print(f"  Valgt HSV: H={self.picked_hsv[0]}  S={self.picked_hsv[1]}  V={self.picked_hsv[2]}")

    # ── Byg HSV-maske ud fra picked + tolerance ───────────────
    def _build_mask(self, hsv_frame):
        if self.picked_hsv is None:
            return np.zeros(hsv_frame.shape[:2], dtype=np.uint8)

        H, S, V = self.picked_hsv

        lower = np.array([max(H - self.h_tol, 0),
                          max(S - self.s_tol, 0),
                          max(V - self.v_tol, 0)])
        upper = np.array([min(H + self.h_tol, 179),
                          min(S + self.s_tol, 255),
                          min(V + self.v_tol, 255)])

        mask = cv2.inRange(hsv_frame, lower, upper)

        # Hue wraparound (rød-toner spænder over H=0/179)
        if H - self.h_tol < 0:
            lower2 = np.array([H - self.h_tol + 180, lower[1], lower[2]])
            upper2 = np.array([179, upper[1], upper[2]])
            mask |= cv2.inRange(hsv_frame, lower2, upper2)
        if H + self.h_tol > 179:
            lower2 = np.array([0, lower[1], lower[2]])
            upper2 = np.array([H + self.h_tol - 180, upper[1], upper[2]])
            mask |= cv2.inRange(hsv_frame, lower2, upper2)

        # Let morfologi for at fjerne støj
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    # ── Gem profil som JSON ───────────────────────────────────
    def _save_profile(self):
        if self.picked_hsv is None:
            print("  Ingen farve valgt endnu — klik på farven i kameraet først.")
            return

        H, S, V = self.picked_hsv
        profile = {
            "name":    self.profile_name,
            "h":       int(H),
            "s":       int(S),
            "v":       int(V),
            "h_tol":   self.h_tol,
            "s_tol":   self.s_tol,
            "v_tol":   self.v_tol,
            "lower":   [max(int(H - self.h_tol), 0),
                        max(int(S - self.s_tol), 0),
                        max(int(V - self.v_tol), 0)],
            "upper":   [min(int(H + self.h_tol), 179),
                        min(int(S + self.s_tol), 255),
                        min(int(V + self.v_tol), 255)],
        }
        path = os.path.join(PROFILES_DIR, f"{self.profile_name}.json")
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)
        print(f"  Profil gemt: {path}")

    # ── Hoved-loop ────────────────────────────────────────────
    def run(self):
        self._last_frame = None
        print("\n  ── GolfBot Farvekalibrering ──")
        print("  Klik på farven i kameravinduet")
        print("  Justér sliderne så masken ser ren ud")
        print("  's' = gem profil  |  'q' = afslut\n")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            self._last_frame = frame.copy()

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = self._build_mask(hsv)

            # Grøn highlight af detekterede pixels
            highlight = frame.copy()
            highlight[mask > 0] = [0, 255, 0]
            blended = cv2.addWeighted(frame, 0.6, highlight, 0.4, 0)

            # Vis info
            if self.picked_hsv is not None:
                H, S, V = self.picked_hsv
                txt = f"HSV: ({H}, {S}, {V})   tol H:{self.h_tol} S:{self.s_tol} V:{self.v_tol}"
                cv2.putText(blended, txt, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(blended, "Klik pa farve | 's'=gem | 'q'=afslut", (10, 460),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
            else:
                cv2.putText(blended, "Klik pa farven du vil kalibrere", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

            cv2.imshow("Kalibrering", blended)
            cv2.imshow("Maske", mask)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                self._save_profile()

        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(f"  Kalibrerer profil: '{name}'")
    print(f"  Kør med:  python src/vision/color_calibrator.py <profilnavn>")
    ColorCalibrator(profile_name=name).run()
