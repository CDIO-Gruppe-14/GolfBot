"""
test_height_offset.py
=====================
Tests for the ArUco marker height-offset correction implemented in FieldMap.

Indeholder to dele:

  1. Unit-tests (ingen hardware):
     Tester correct_height_offset() matematisk med kendte inputvaerdier.
     Kan koeres med: python -m pytest tests/test_height_offset.py -v

  2. Hardware-test (kraever kamera + robot paa banen):
     Aabner kameraet, detekterer robotten og udskriver den korrigerede
     cm-position. Sammenlign outputtet med en linealmaaling paa banen.
     Koeres med: RUN_HARDWARE_TESTS=1 python -m pytest tests/test_height_offset.py -s -v
"""

import os
import sys
import math
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    ARUCO_DICT,
    CAMERA_HEIGHT_CM,
    CAMERA_INDEX,
    FIELD_SIZE_CM,
    ROBOT_MARKER_HEIGHT_CM,
    ROBOT_MARKER_ID,
)
from src.vision.aruco_detector import ArucoDetector
from src.vision.camera import RobotCamera
from src.vision.field_map import FieldMap
from src.vision.robot_tracker import RobotTracker
from src.server.helpers.camera_utils import get_fresh_frame
from src.server.phases.detection import detect_robot
from src.planning.command_generator import compute_distance


# ===========================================================================
# Hjaelpefunktion: opret en FieldMap med simpelt, deterministisk koordinatsystem
# ===========================================================================

def _make_simple_field_map(nadir_x_cm, nadir_y_cm):
    """
    Opretter en FieldMap hvis hjorner ligger paa pixel-koordinater svarende
    nojagtig til cm-koordinaterne (1 px = 1 cm), saa pixel_to_cm() er triviel.

    Nadir-cachen saettes manuelt til (nadir_x_cm, nadir_y_cm) saa vi kan
    styre den eksakt i enhedstestene uafhaengigt af CAMERA_FRAME_WIDTH/HEIGHT.
    """
    w, h = FIELD_SIZE_CM
    # Hjorner i pixel-koordinater = cm-koordinater (1:1-mapping)
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    fm = FieldMap(field_corners_px=corners, field_size_cm=(w, h))
    # Saet nadir manuelt saa testen er uafhaengig af den faktiske frame-stoerrelse
    fm._nadir_cm_cache = (nadir_x_cm, nadir_y_cm)
    return fm


# ===========================================================================
# 1. UNIT-TESTS  (ingen hardware)
# ===========================================================================

class TestCorrectHeightOffsetMath(unittest.TestCase):
    """
    Tester correct_height_offset() rent matematisk — ingen kamera eller robot.

    Vi placerer nadir i feltets centrum og verificerer korrektionens retning,
    stoerrelse og graensetilfaelde.
    """

    def setUp(self):
        self.w, self.h = FIELD_SIZE_CM          # (180, 120)
        self.nx = self.w / 2.0                  # 90 cm — nadir x
        self.ny = self.h / 2.0                  # 60 cm — nadir y
        self.fm = _make_simple_field_map(self.nx, self.ny)
        self.H = CAMERA_HEIGHT_CM               # 161 cm
        self.h_marker = ROBOT_MARKER_HEIGHT_CM  # 30 cm
        self.scale = self.h_marker / self.H     # ≈ 0.1863

    # ------------------------------------------------------------------
    # 1a. Robot i nadir-punktet — ingen korrektion
    # ------------------------------------------------------------------
    def test_at_nadir_no_correction_is_applied(self):
        """Robot direkte under kameraet skal ikke flyttes."""
        x_corr, y_corr = self.fm.correct_height_offset(
            self.nx, self.ny, self.H, self.h_marker
        )
        self.assertAlmostEqual(x_corr, self.nx, places=10)
        self.assertAlmostEqual(y_corr, self.ny, places=10)

    # ------------------------------------------------------------------
    # 1b. Korrektionen traekkker position mod nadir
    # ------------------------------------------------------------------
    def test_correction_moves_position_toward_nadir(self):
        """En position vaek fra nadir skal rykke NAERMERE nadir efter korrektion."""
        x_raw, y_raw = 10.0, 10.0   # toep-venstre hjorne — langt fra nadir
        x_corr, y_corr = self.fm.correct_height_offset(
            x_raw, y_raw, self.H, self.h_marker
        )
        dist_before = compute_distance(x_raw,  y_raw,  self.nx, self.ny)
        dist_after  = compute_distance(x_corr, y_corr, self.nx, self.ny)
        self.assertLess(
            dist_after, dist_before,
            "Korrigeret position skal vaere naermere nadir end den ukorigerede."
        )

    # ------------------------------------------------------------------
    # 1c. Korrektionens stoerrelse matcher formlen eksakt
    # ------------------------------------------------------------------
    def test_correction_magnitude_matches_formula(self):
        """
        Formel: corrected = raw + (nadir - raw) * (h / H)
        Tester hjorne (0, 0) som giver maksimal korrektion.
        """
        x_raw, y_raw = 0.0, 0.0
        x_corr, y_corr = self.fm.correct_height_offset(
            x_raw, y_raw, self.H, self.h_marker
        )
        x_expected = x_raw + (self.nx - x_raw) * self.scale
        y_expected = y_raw + (self.ny - y_raw) * self.scale

        self.assertAlmostEqual(x_corr, x_expected, places=10)
        self.assertAlmostEqual(y_corr, y_expected, places=10)

    # ------------------------------------------------------------------
    # 1d. Nul markoehoejde = ingen korrektion
    # ------------------------------------------------------------------
    def test_zero_marker_height_gives_no_correction(self):
        """marker_height_cm = 0 betyder markoeren er paa baneplanet — ingen korrektion."""
        x_raw, y_raw = 10.0, 100.0
        x_corr, y_corr = self.fm.correct_height_offset(
            x_raw, y_raw, self.H, marker_height_cm=0.0
        )
        self.assertAlmostEqual(x_corr, x_raw, places=10)
        self.assertAlmostEqual(y_corr, y_raw, places=10)

    # ------------------------------------------------------------------
    # 1e. Markoehoejde = kamerahoejde → position kollapser til nadir
    # ------------------------------------------------------------------
    def test_marker_at_camera_height_collapses_to_nadir(self):
        """Hvis markoeren er i kamerahojde skal alle positioner ende i nadir."""
        x_raw, y_raw = 30.0, 110.0
        x_corr, y_corr = self.fm.correct_height_offset(
            x_raw, y_raw,
            camera_height_cm=self.H,
            marker_height_cm=self.H,   # scale = 1
        )
        self.assertAlmostEqual(x_corr, self.nx, places=10)
        self.assertAlmostEqual(y_corr, self.ny, places=10)

    # ------------------------------------------------------------------
    # 1f. Korrektionen er storre mod kanterne end mod midten
    # ------------------------------------------------------------------
    def test_correction_grows_with_distance_from_nadir(self):
        """Fejlen vokser mod kanterne — korrektionen skal vaere stoerre for hjornepunkter."""
        x_near, y_near = self.nx + 5,  self.ny + 5    # taet paa nadir
        x_far,  y_far  = self.nx + 40, self.ny + 40   # langt fra nadir

        near_corr = self.fm.correct_height_offset(x_near, y_near, self.H, self.h_marker)
        far_corr  = self.fm.correct_height_offset(x_far,  y_far,  self.H, self.h_marker)

        shift_near = compute_distance(x_near, y_near, near_corr[0], near_corr[1])
        shift_far  = compute_distance(x_far,  y_far,  far_corr[0],  far_corr[1])

        self.assertGreater(
            shift_far, shift_near,
            "Korrektionen skal vaere stoerre for en position laengere fra nadir."
        )

    # ------------------------------------------------------------------
    # 1g. Korrektionen er symmetrisk om nadir
    # ------------------------------------------------------------------
    def test_correction_is_symmetric_around_nadir(self):
        """En position spejlet om nadir skal give en spejlet korrigeret position."""
        dx, dy = 35.0, 25.0
        x_a, y_a = self.nx + dx, self.ny + dy
        x_b, y_b = self.nx - dx, self.ny - dy

        xa_corr, ya_corr = self.fm.correct_height_offset(x_a, y_a, self.H, self.h_marker)
        xb_corr, yb_corr = self.fm.correct_height_offset(x_b, y_b, self.H, self.h_marker)

        # Midtpunktet af de to korrigerede positioner skal vaere nadir
        mid_x = (xa_corr + xb_corr) / 2.0
        mid_y = (ya_corr + yb_corr) / 2.0
        self.assertAlmostEqual(mid_x, self.nx, places=10)
        self.assertAlmostEqual(mid_y, self.ny, places=10)

    # ------------------------------------------------------------------
    # 1h. Konfigurationsvaerdier er fysisk fornuftige
    # ------------------------------------------------------------------
    def test_config_values_are_physically_sensible(self):
        """Marker-hoejden skal vaere positiv og mindre end kamera-hoejden."""
        self.assertGreater(CAMERA_HEIGHT_CM, 0,
                           "CAMERA_HEIGHT_CM skal vaere positiv")
        self.assertGreater(ROBOT_MARKER_HEIGHT_CM, 0,
                           "ROBOT_MARKER_HEIGHT_CM skal vaere positiv")
        self.assertLess(ROBOT_MARKER_HEIGHT_CM, CAMERA_HEIGHT_CM,
                        "Markoeren kan ikke vaere hoejere end kameraet")

    # ------------------------------------------------------------------
    # 1i. Nadir-cache er deterministisk (kald to gange giver samme svar)
    # ------------------------------------------------------------------
    def test_nadir_cache_is_deterministic(self):
        """_nadir_cm skal returnere identisk vaerdi ved gentagne kald."""
        n1 = self.fm._nadir_cm
        n2 = self.fm._nadir_cm
        self.assertEqual(n1, n2)


# ===========================================================================
# 2. HARDWARE-TEST  (kraever kamera + robot paa banen)
# ===========================================================================

@unittest.skipUnless(
    os.getenv("RUN_HARDWARE_TESTS") == "1",
    "Hardware-test: saet RUN_HARDWARE_TESTS=1 for at koere paa banen.",
)
class TestRobotPositionCm(unittest.TestCase):
    """
    Placeer robotten et KENDT sted paa banen (maal med lineal) og kjoer testen.
    Sammenlign det udskrevne cm-resultat med din linealmaaling.

    Testen detekterer robotten N gange og rapporterer:
      - Gennemsnitsposition (cm)
      - Standardafvigelse (spredning)
      - Korrigeret vs. ukorrigeret position
    """

    SAMPLES = 10          # Antal frames der middelvaerdidannes over
    POSITION_TOLERANCE_CM = 5.0  # Accepteret afvigelse fra fysisk maaling

    @classmethod
    def setUpClass(cls):
        cls.camera = RobotCamera()
        aruco = ArucoDetector(ARUCO_DICT)
        cls.field_map = FieldMap(aruco_detector=aruco)
        cls.tracker = RobotTracker(aruco, ROBOT_MARKER_ID)

        frame = get_fresh_frame(cls.camera)
        if frame is None:
            cls.camera.release()
            raise AssertionError(
                f"Kameraet (index {CAMERA_INDEX}) leverede intet frame. "
                "Tjek at kameraet er tilsluttet."
            )

        if cls.field_map.calibrate_from_aruco(frame):
            print("[HeightOffsetTest] Live ArUco bane-kalibrering brugt.")
        else:
            print(
                "[HeightOffsetTest] Ingen live ArUco-markorer fundet — "
                "bruger gemt/fallback kalibrering."
            )

    @classmethod
    def tearDownClass(cls):
        camera = getattr(cls, "camera", None)
        if camera:
            camera.release()

    def _detect_once(self):
        """
        Returnerer (x_raw_cm, y_raw_cm, x_corr_cm, y_corr_cm) for et enkelt frame,
        eller None hvis robotten ikke kan detekteres.
        """
        frame = get_fresh_frame(self.camera)
        if frame is None:
            return None

        robot = self.tracker.locate(frame)
        if robot is None:
            return None

        # Ukorrigeret position (hvad vi fik foer implementeringen)
        x_raw, y_raw = self.field_map.pixel_to_cm(robot.x, robot.y)

        # Korrigeret position (det nye correct_height_offset())
        x_corr, y_corr = self.field_map.correct_height_offset(
            x_raw, y_raw,
            camera_height_cm=CAMERA_HEIGHT_CM,
            marker_height_cm=ROBOT_MARKER_HEIGHT_CM,
        )

        return x_raw, y_raw, x_corr, y_corr

    # ------------------------------------------------------------------
    # Hardware-test 1: robotten detekteres og rapporterer cm-position
    # ------------------------------------------------------------------
    def test_01_robot_detected_and_position_reported(self):
        """
        Placeer robotten paa et KENDT sted paa banen.
        Testen detekterer positionen og udskriver:
          - Ukorrigeret position (fra pixel_to_cm direkte)
          - Korrigeret position  (efter correct_height_offset)
          - Forskel mellem de to
        Sammenlign den korrigerede position med din linealmaaling.
        """
        results = []
        failures = 0
        for _ in range(self.SAMPLES):
            reading = self._detect_once()
            if reading is None:
                failures += 1
            else:
                results.append(reading)

        self.assertGreater(
            len(results), 0,
            f"Robotten blev ikke detekteret i nogen af {self.SAMPLES} frames. "
            f"Tjek at robot-markoer ID {ROBOT_MARKER_ID} er synlig for kameraet."
        )

        # Beregn gennemsnit og spredning
        raw_xs  = [r[0] for r in results]
        raw_ys  = [r[1] for r in results]
        corr_xs = [r[2] for r in results]
        corr_ys = [r[3] for r in results]

        avg_raw_x  = sum(raw_xs)  / len(raw_xs)
        avg_raw_y  = sum(raw_ys)  / len(raw_ys)
        avg_corr_x = sum(corr_xs) / len(corr_xs)
        avg_corr_y = sum(corr_ys) / len(corr_ys)

        std_x = math.sqrt(sum((v - avg_corr_x) ** 2 for v in corr_xs) / len(corr_xs))
        std_y = math.sqrt(sum((v - avg_corr_y) ** 2 for v in corr_ys) / len(corr_ys))

        shift = compute_distance(avg_raw_x, avg_raw_y, avg_corr_x, avg_corr_y)

        print(
            f"\n[HeightOffsetTest] Resultat ({len(results)}/{self.SAMPLES} frames OK):"
            f"\n  Ukorrigeret position : ({avg_raw_x:.2f}, {avg_raw_y:.2f}) cm"
            f"\n  Korrigeret position  : ({avg_corr_x:.2f}, {avg_corr_y:.2f}) cm"
            f"\n  Korrektion (forskyd) : {shift:.2f} cm mod nadir"
            f"\n  Spredning (std)      : x={std_x:.2f} cm  y={std_y:.2f} cm"
            f"\n"
            f"\n  Maal robottens faktiske position paa banen med en lineal"
            f"\n  og sammenlign med den KORRIGEREDE position ovenfor."
        )

        # Spredningen maa ikke vaere for stor (ustabil detektion)
        self.assertLess(
            std_x, 3.0,
            f"For stor spredning i x-retning ({std_x:.2f} cm). "
            "Tjek at kameraet ikke rystes og at markoeren sidder fast."
        )
        self.assertLess(
            std_y, 3.0,
            f"For stor spredning i y-retning ({std_y:.2f} cm). "
            "Tjek at kameraet ikke rystes og at markoeren sidder fast."
        )

    # ------------------------------------------------------------------
    # Hardware-test 2: korrigeret position er indenfor banens graeenser
    # ------------------------------------------------------------------
    def test_02_corrected_position_is_within_field_bounds(self):
        """Den korrigerede robot-position skal ligge indenfor banens cm-graeenser."""
        reading = self._detect_once()
        self.assertIsNotNone(
            reading,
            f"Robotten (markoer ID {ROBOT_MARKER_ID}) blev ikke fundet i frame."
        )

        _, _, x_corr, y_corr = reading
        w_cm, h_cm = FIELD_SIZE_CM

        margin = 10.0   # Lille margin for kalibrerings-unojagtig hed

        self.assertGreater(x_corr, -margin,
                           f"Korrigeret x ({x_corr:.1f} cm) er udenfor banen (venstre kant)")
        self.assertLess   (x_corr, w_cm + margin,
                           f"Korrigeret x ({x_corr:.1f} cm) er udenfor banen (hoejre kant)")
        self.assertGreater(y_corr, -margin,
                           f"Korrigeret y ({y_corr:.1f} cm) er udenfor banen (ovre kant)")
        self.assertLess   (y_corr, h_cm + margin,
                           f"Korrigeret y ({y_corr:.1f} cm) er udenfor banen (nedre kant)")

        print(
            f"[HeightOffsetTest] Robot indenfor banen: "
            f"({x_corr:.2f}, {y_corr:.2f}) cm  "
            f"(felt: {w_cm}x{h_cm} cm)"
        )

    # ------------------------------------------------------------------
    # Hardware-test 3: detect_robot() i ctx-pipeline giver korrigeret position
    # ------------------------------------------------------------------
    def test_03_detect_robot_via_ctx_pipeline_gives_corrected_position(self):
        """
        Tester at det fulde ctx-pipeline (detect_robot) returnerer den
        korrigerede position — dvs. at correct_height_offset() rent faktisk
        kaldes i detection.py og ikke kun i den isolerede _detect_once helper.
        """
        from src.entities.robot import Robot

        ctx = SimpleNamespace(
            camera=self.camera,
            tracker=self.tracker,
            field_map=self.field_map,
            robot=Robot(),
        )

        found = detect_robot(ctx)
        self.assertTrue(
            found,
            f"detect_robot() fandt ikke robotten (markoer ID {ROBOT_MARKER_ID})."
        )

        # Sammenlign ctx.robot.x/y med hvad _detect_once ville give
        reading = self._detect_once()
        self.assertIsNotNone(reading, "Intet sammenlignings-frame tilgaengeligt.")
        _, _, x_corr_expected, y_corr_expected = reading

        # Tillad lille afvigelse (robotten kan have rykket sig en smule)
        self.assertAlmostEqual(
            ctx.robot.x, x_corr_expected,
            delta=self.POSITION_TOLERANCE_CM,
            msg=(
                f"ctx.robot.x ({ctx.robot.x:.2f}) stemmer ikke med forventet "
                f"korrigeret x ({x_corr_expected:.2f}) indenfor "
                f"{self.POSITION_TOLERANCE_CM} cm."
            ),
        )
        self.assertAlmostEqual(
            ctx.robot.y, y_corr_expected,
            delta=self.POSITION_TOLERANCE_CM,
            msg=(
                f"ctx.robot.y ({ctx.robot.y:.2f}) stemmer ikke med forventet "
                f"korrigeret y ({y_corr_expected:.2f}) indenfor "
                f"{self.POSITION_TOLERANCE_CM} cm."
            ),
        )

        print(
            f"[HeightOffsetTest] ctx-pipeline OK: "
            f"robot paa ({ctx.robot.x:.2f}, {ctx.robot.y:.2f}) cm"
        )


# ===========================================================================
# Direkte koersel
# ===========================================================================
if __name__ == "__main__":
    os.environ.setdefault("RUN_HARDWARE_TESTS", "1")
    unittest.main(verbosity=2)
