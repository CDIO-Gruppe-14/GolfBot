"""
test_camera_distance.py
=======================
Interaktiv hardware-test der maaler afstanden mellem to punkter i kamera-billedet
og konverterer den til centimeter via FieldMap's perspektiv-transformation.

Brug:
    RUN_HARDWARE_TESTS=1 python -m pytest tests/test_camera_distance.py -s -v

    eller direkte:
    RUN_HARDWARE_TESTS=1 python tests/test_camera_distance.py

Fremgangsmaade:
    1. Et live kamera-preview aabnes.
    2. Klik paa det FOERSTE punkt (markeret med en roed cirkel).
    3. Klik paa det ANDET punkt (markeret med en blaa cirkel).
    4. Den beregnede afstand (pixels og cm) vises i konsollen og som overlay.
    5. Tryk 'r' for at nulstille og maale igen, eller 'q' / ESC for at afslutte.

Hvad testen validerer:
    - Kameraet leverer et gyldigt frame (via get_fresh_frame).
    - FieldMap.pixel_to_cm() kan konvertere pixelkoordinater til cm.
    - compute_distance() giver en afstand der stemmer med den fysisk maalte afstand.
      Brug en lineal paa banen og sammenlign med det rapporterede cm-tal.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

from config import ARUCO_DICT, CAMERA_INDEX, FIELD_SIZE_CM
from src.vision.aruco_detector import ArucoDetector
from src.vision.camera import RobotCamera
from src.vision.field_map import FieldMap
from src.planning.command_generator import compute_distance
from src.server.helpers.camera_utils import get_fresh_frame


# ---------------------------------------------------------------------------
# Hjælpefunktioner  (delegerer til systemets egne metoder)
# ---------------------------------------------------------------------------

def _pixel_distance(p1, p2):
    """Pixel-afstand via systemets compute_distance()."""
    return compute_distance(p1[0], p1[1], p2[0], p2[1])


def _cm_distance(field_map, p1, p2):
    """Cm-afstand: konverterer via FieldMap.pixel_to_cm() og maaler med compute_distance()."""
    x1_cm, y1_cm = field_map.pixel_to_cm(*p1)
    x2_cm, y2_cm = field_map.pixel_to_cm(*p2)
    return compute_distance(x1_cm, y1_cm, x2_cm, y2_cm)


def _draw_overlay(frame, points, px_dist=None, cm_dist=None):
    """Tegner prikker, linje og maalingsresultat oven paa frame (in-place)."""
    colors = [(0, 0, 255), (255, 0, 0)]   # roed foerste punkt, blaa andet punkt
    labels = ["P1", "P2"]

    for i, pt in enumerate(points):
        cv2.circle(frame, pt, 8, colors[i], -1)
        cv2.circle(frame, pt, 10, (255, 255, 255), 2)
        cv2.putText(
            frame, labels[i],
            (pt[0] + 12, pt[1] - 12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, colors[i], 2,
        )

    if len(points) == 2:
        cv2.line(frame, points[0], points[1], (0, 255, 0), 2)

        if px_dist is not None and cm_dist is not None:
            mid = (
                (points[0][0] + points[1][0]) // 2,
                (points[0][1] + points[1][1]) // 2,
            )
            label = f"{px_dist:.1f} px  |  {cm_dist:.2f} cm"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
            cv2.rectangle(
                frame,
                (mid[0] - 4, mid[1] - th - 6),
                (mid[0] + tw + 4, mid[1] + 4),
                (0, 0, 0), -1,
            )
            cv2.putText(
                frame, label,
                (mid[0], mid[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2,
            )

    # Instruktions-banner
    instructions = (
        "Klik P1 -> P2 for at maale | r: nulstil | q/ESC: afslut"
        if len(points) < 2
        else "Maaling faerdig | r: nulstil | q/ESC: afslut"
    )
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 30), (30, 30, 30), -1)
    cv2.putText(
        frame, instructions,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1,
    )


# ---------------------------------------------------------------------------
# Global tilstand brugt af mouse-callback
# ---------------------------------------------------------------------------
_state = {"points": [], "px_dist": None, "cm_dist": None}


def _mouse_callback(event, x, y, flags, param):
    """Registrerer klik og beregner afstand naar to punkter er valgt."""
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    field_map = param["field_map"]
    pts = _state["points"]

    if len(pts) >= 2:
        return  # Vent paa 'r' for nulstilling

    pts.append((x, y))
    print(f"[DistanceTest] Punkt klikket: P{len(pts)} = ({x}, {y})")

    if len(pts) == 2:
        px = _pixel_distance(pts[0], pts[1])
        cm = _cm_distance(field_map, pts[0], pts[1])
        _state["px_dist"] = px
        _state["cm_dist"] = cm

        scale = cm / px if px > 0 else 0.0
        print(
            f"\n[DistanceTest] Maaling udfoert:"
            f"\n  P1 (px): {pts[0]}"
            f"\n  P2 (px): {pts[1]}"
            f"\n  Afstand i pixels   : {px:.2f} px"
            f"\n  Afstand i cm       : {cm:.4f} cm"
            f"\n  Skala              : {scale:.6f} cm/px"
            f"\n  (Sammenlign cm-vaerdien med en fysisk linealmaaling paa banen)\n"
        )



# ---------------------------------------------------------------------------
# Unittest-klasse
# ---------------------------------------------------------------------------

@unittest.skipUnless(
    os.getenv("RUN_HARDWARE_TESTS") == "1",
    "Hardware-test: saet RUN_HARDWARE_TESTS=1 for at koere den interaktivt paa banen.",
)
class TestCameraDistance(unittest.TestCase):
    """
    Interaktiv test der maaler pixel- og cm-afstanden mellem to klik-punkter.

    Validerer at kamera-til-cm-konverteringen (FieldMap.pixel_to_cm) er korrekt
    kalibreret, saa afstandsbaserede kommandoer (FORWARD, TURN) er praecise.
    """

    @classmethod
    def setUpClass(cls):
        cls.camera = RobotCamera()
        aruco = ArucoDetector(ARUCO_DICT)
        cls.field_map = FieldMap(aruco_detector=aruco)

        print(f"[DistanceTest] Initialiserer FieldMap...")
        print(f"[DistanceTest] Banens fysiske mål (config.py): {FIELD_SIZE_CM} cm")

        # Forsøg live ArUco-kalibrering fra et friskt frame (get_fresh_frame
        # flusher kamera-bufferen saa vi ikke faar et forældet billede)
        frame = get_fresh_frame(cls.camera)
        if frame is None:
            cls.camera.release()
            raise AssertionError(
                f"Kameraet (index {CAMERA_INDEX}) leverede intet frame. "
                "Tjek at kameraet er tilsluttet."
            )

        if cls.field_map.calibrate_from_aruco(frame):
            print("[DistanceTest] Live ArUco bane-kalibrering udført med succes!")
        else:
            print(
                "[DistanceTest] Ingen live ArUco-markører fundet — "
                "bruger gemt/fallback kalibrering."
            )

        print(f"[DistanceTest] Aktuelle pixel-hjørner brugt til homografi:")
        for idx, pt in enumerate(cls.field_map.corners):
            print(f"  Hjørne {idx+1}: {pt}")
        print(f"[DistanceTest] Disse hjørner transformeres til: (0,0) -> {FIELD_SIZE_CM}")


    @classmethod
    def tearDownClass(cls):
        camera = getattr(cls, "camera", None)
        if camera:
            camera.release()

    # ------------------------------------------------------------------
    # Enhedstest 1: kameraet leverer et gyldigt frame
    # ------------------------------------------------------------------
    def test_01_camera_delivers_frame(self):
        """get_fresh_frame() skal levere et gyldigt, friskt frame fra kameraet."""
        frame = get_fresh_frame(self.camera)
        self.assertIsNotNone(
            frame,
            f"get_fresh_frame() (index {CAMERA_INDEX}) leverede intet frame.",
        )
        h, w = frame.shape[:2]
        self.assertGreater(w, 0, "Frame-bredde er 0")
        self.assertGreater(h, 0, "Frame-hoejde er 0")
        print(f"[DistanceTest] Frame OK: {w}x{h} px")

    # ------------------------------------------------------------------
    # Enhedstest 2: FieldMap kan konvertere pixels til cm
    # ------------------------------------------------------------------
    def test_02_pixel_to_cm_conversion_is_consistent(self):
        """
        FieldMap.pixel_to_cm() og compute_distance() skal vaere konsistente:
        - Samme punkt skal give samme koordinat.
        - Bane-diagonalen beregnet via compute_distance() maa ikke afvige
          mere end 20 % fra den fysiske diagonal (FIELD_SIZE_CM).
        """
        fm = self.field_map
        w_cm, h_cm = FIELD_SIZE_CM

        # Hent et friskt frame for at faa faktiske frame-dimensioner
        frame = get_fresh_frame(self.camera)
        self.assertIsNotNone(frame, "Intet frame til konverterings-test")
        fh, fw = frame.shape[:2]

        # Test: samme pixel -> samme cm-koordinat (determinisme)
        cx, cy = fw // 2, fh // 2
        cm1 = fm.pixel_to_cm(cx, cy)
        cm2 = fm.pixel_to_cm(cx, cy)
        self.assertAlmostEqual(cm1[0], cm2[0], places=5)
        self.assertAlmostEqual(cm1[1], cm2[1], places=5)

        # Test: bane-diagonalen via _cm_distance (bruger compute_distance internt)
        px1 = fm.corners[0]  # top-venstre hjørne
        px2 = fm.corners[2]  # bund-højre hjørne (diagonalt modsatte)
        dist_cm = _cm_distance(fm, px1, px2)

        # Forventet diagonal beregnet med systemets compute_distance()
        diag_expected = compute_distance(0, 0, w_cm, h_cm)

        print(
            f"[DistanceTest] Diagonal bane-afstand:"
            f" {dist_cm:.2f} cm  (forventet ~{diag_expected:.2f} cm)"
        )

        # Diagonalen maa ikke afvige mere end 20 % fra den fysiske banediagonal
        self.assertAlmostEqual(
            dist_cm, diag_expected, delta=diag_expected * 0.20,
            msg=(
                f"Diagonal afstand ({dist_cm:.2f} cm) afviger mere end 20 % "
                f"fra forventet {diag_expected:.2f} cm. "
                "Tjek at bane-kalibreringen er korrekt."
            ),
        )

    # ------------------------------------------------------------------
    # Enhedstest 3: interaktiv manuel maaling (klik to punkter)
    # ------------------------------------------------------------------
    def test_03_interactive_distance_measurement(self):
        """
        Aabner et live kamera-preview.
        Klik paa to punkter for at maale afstanden i pixels og cm.
        Sammenlign cm-vaerdien med en fysisk linealmaaling paa banen.

        Testen bestaar ALTID — resultaterne er til manuel validering.
        Tryk 'q' eller ESC for at afslutte.
        """
        window = "GolfBot — Afstandsmaaling (klik P1 -> P2)"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window, 1280, 720)
        cv2.setMouseCallback(
            window, _mouse_callback, param={"field_map": self.field_map}
        )

        # Nulstil global tilstand
        _state["points"].clear()
        _state["px_dist"] = None
        _state["cm_dist"] = None

        print(
            "\n[DistanceTest] Interaktivt preview aabnet."
            "\n  Klik paa to punkter paa banen for at maale afstanden."
            "\n  Brug en lineal paa banen og sammenlign med cm-resultatet."
            "\n  Tryk 'r' for at nulstille, 'q' eller ESC for at afslutte.\n"
        )

        while True:
            frame = self.camera.get_frame()
            if frame is None:
                print("[DistanceTest] Intet frame — afslutter preview.")
                break

            display = frame.copy()
            _draw_overlay(
                display,
                list(_state["points"]),
                _state["px_dist"],
                _state["cm_dist"],
            )

            cv2.imshow(window, display)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):   # 'q' eller ESC
                break
            if key == ord("r"):         # Nulstil maaling
                _state["points"].clear()
                _state["px_dist"] = None
                _state["cm_dist"] = None
                print("[DistanceTest] Nulstillet — klik igen for ny maaling.")

        cv2.destroyWindow(window)

        # Testen er informativ; ingen hard assertion paa de interaktive resultater.
        # Fejl opdages ved at sammenligne cm-outputtet med en linealmaaling.
        self.assertTrue(True, "Interaktiv maaling afsluttet.")


# ---------------------------------------------------------------------------
# Direkte koersel
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    os.environ.setdefault("RUN_HARDWARE_TESTS", "1")
    unittest.main(verbosity=2)
