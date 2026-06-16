import cv2
import numpy as np
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hsv_utils import PROFILES_DIR, build_hsv_mask, hsv_bounds


class ColorCalibrator:
    def __init__(self, camera, profile_name="default"):
        self.camera = camera
        self.profile_name = profile_name
        self.picked_hsv = None
        self._last_frame = None

        self.h_tol = 15
        self.s_tol = 60
        self.v_tol = 60

        import os
        os.makedirs(PROFILES_DIR, exist_ok=True)
        self._setup_window()

    def _setup_window(self):
        cv2.namedWindow("Kalibrering")
        cv2.namedWindow("Maske")
        cv2.createTrackbar("H tolerance", "Kalibrering", self.h_tol, 90,  self._on_h)
        cv2.createTrackbar("S tolerance", "Kalibrering", self.s_tol, 127, self._on_s)
        cv2.createTrackbar("V tolerance", "Kalibrering", self.v_tol, 127, self._on_v)
        cv2.setMouseCallback("Kalibrering", self._on_click)

    def _on_h(self, val): self.h_tol = val
    def _on_s(self, val): self.s_tol = val
    def _on_v(self, val): self.v_tol = val

    def _on_click(self, event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN and self._last_frame is not None:
            hsv_frame = cv2.cvtColor(self._last_frame, cv2.COLOR_BGR2HSV)
            x0, y0 = max(x - 2, 0), max(y - 2, 0)
            x1, y1 = min(x + 3, hsv_frame.shape[1]), min(y + 3, hsv_frame.shape[0])
            patch = hsv_frame[y0:y1, x0:x1]
            self.picked_hsv = np.mean(patch, axis=(0, 1)).astype(int)
            print(f"  Valgt HSV: H={self.picked_hsv[0]}  S={self.picked_hsv[1]}  V={self.picked_hsv[2]}")

    def _build_mask(self, hsv_frame):
        if self.picked_hsv is None:
            return np.zeros(hsv_frame.shape[:2], dtype=np.uint8)
        H, S, V = self.picked_hsv
        return build_hsv_mask(hsv_frame, H, S, V, self.h_tol, self.s_tol, self.v_tol)

    def _save_profile(self):
        if self.picked_hsv is None:
            print("  Ingen farve valgt endnu — klik på farven i kameraet først.")
            return
        H, S, V = self.picked_hsv
        lower, upper = hsv_bounds(H, S, V, self.h_tol, self.s_tol, self.v_tol)
        profile = {
            "name": self.profile_name,
            "h": int(H), "s": int(S), "v": int(V),
            "h_tol": self.h_tol, "s_tol": self.s_tol, "v_tol": self.v_tol,
            "lower": lower, "upper": upper,
        }
        import os
        path = os.path.join(PROFILES_DIR, f"{self.profile_name}.json")
        with open(path, "w") as f:
                    
        # Bevar eksisterende formfiltre (f.eks. til orange, hvid eller roed)
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        existing_profile = json.load(f)
                        for key in ["min_circularity", "max_aspect_ratio", "min_area", "max_area"]:
                            if key in existing_profile:
                                profile[key] = existing_profile[key]
                except Exception:
                    pass

        # Særlige standardværdier hvis de ikke findes i forvejen
        if self.profile_name in ["orange", "hvid"] and "min_circularity" not in profile:
            profile["min_circularity"] = 0.5
            profile["max_aspect_ratio"] = 1.5
        elif self.profile_name == "roed" and "min_circularity" not in profile:
            profile["min_circularity"] = None
            profile["max_aspect_ratio"] = None
            json.dump(profile, f, indent=2)
        print(f"  Profil gemt: {path}")

    def run(self):
        print("\n  ── GolfBot Farvekalibrering ──")
        print("  Klik på farven i kameravinduet")
        print("  Justér sliderne så masken ser ren ud")
        print("  's' = gem profil  |  'q' = afslut\n")

        try:
            while True:
                frame = self.camera.get_frame()
                if frame is None:
                    break
                self._last_frame = frame.copy()

                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = self._build_mask(hsv)

                highlight = frame.copy()
                highlight[mask > 0] = [0, 255, 0]
                blended = cv2.addWeighted(frame, 0.6, highlight, 0.4, 0)

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
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    from camera import RobotCamera

    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(f"  Kalibrerer profil: '{name}'")

    camera = RobotCamera()
    try:
        ColorCalibrator(camera, profile_name=name).run()
    finally:
        camera.release()
