"""
GolfBot — Central Konfigurationsfil
====================================
Alle justerbare variable er samlet her.
Importer det du har brug for i de andre filer:

    from config import MOTOR_SPEED, PORT, FIELD_SIZE_CM

Sektioner:
  1. Netværk / Kommunikation
  2. Motor & Bevægelse
  3. Kamera
  4. Vision / Farvedetektion
  5. Bane (FieldMap)
  6. Navigation / Planlægning
"""

# ===========================================================================
# 1. NETVÆRK / KOMMUNIKATION
# ===========================================================================
# Brugt i: src/communication/connection.py  (linje 5-6)
# Brugt i: src/server/main.py og src/server/test_wifi.py

# IP-adresse på EV3 robotten — SKAL opdateres til jeres netværk!
# Find den ved at køre: ip addr   på EV3'en
ROBOT_IP    = "172.20.10.4"

PORT        = 12345   # TCP-port EV3 lytter på
BUFFER_SIZE = 1024    # Bytes der læses ad gangen fra socket

# Antal genforsoeg når PC prøver at forbinde til EV3
# Brugt i: src/communication/connection.py  (linje 89 — connect_to_robot)
MAX_RETRIES = 5

# Timeout i sekunder mens socket prøver at forbinde
# Brugt i: src/communication/connection.py  (linje 95)
CONNECT_TIMEOUT_SEC = 5.0

# Ventetid i sekunder mellem hvert genforsoeg
# Brugt i: src/communication/connection.py  (linje 102)
RETRY_DELAY_SEC = 2


# ===========================================================================
# 2. MOTOR & BEVÆGELSE
# ===========================================================================
# Brugt i: src/robot/motor_controller.py  (linje 6-9)

WHEEL_DIAMETER_CM  = 7    # Hjuldiameter i cm  (mål dit hjul med en lineal)
AXLE_TRACK_CM      = 19.5    # Afstand mellem hjulcentrene i cm

TURN_SPEED         = 30
MOTOR_SPEED        = 20

# Bevægelses-ports
# Brugt i: src/robot/motor_controller.py  (linje 16)
MOTOR_LEFT_PORT  = "B"   # Port for venstre motor
MOTOR_RIGHT_PORT = "D"   # Port for højre motor

# Opsamlingsmotor
# Brugt i: src/robot/test_collector.py
COLLECTOR_MOTOR_PORT = "A" # Port for opsamler (ret til A eller C)
COLLECTOR_SPEED      = 25        # Hastighed i procent (0-100)

SPEED_UNDER_COLLECTION = 25

# Gyroseensor input-port
# Brugt i: src/robot/main.py  (linje 78)
GYRO_PORT = "2"


# ===========================================================================
# 2b. ROBOT-FOOTPRINT (fysisk stoerrelse ift. ArUco-markoeren)
# ===========================================================================
# Robotten er stoerre end ArUco-markoeren. Disse vaerdier angiver hvor langt
# robottens kant stikker ud fra markoerens CENTER i hver retning (cm).
# FRONT er mod koerselsretningen (robottens naese/opsamler).
#
#              FRONT
#           +---------+
#     LEFT  |   (o)   |  RIGHT      (o) = ArUco-markoerens center
#           +---------+
#              BACK
#
# Maal afstanden fra markoerens midte ud til hver kant med en lineal.
# Brugt til kollision: pathfinding holder HELE robotkroppen fri af forhindringer
# og bander -- ikke kun markoer-centret.
ROBOT_FRONT_CM = 17.0   # markoer-center -> forreste kant (naese/opsamler)
ROBOT_BACK_CM  = 17.0   # markoer-center -> bageste kant
ROBOT_LEFT_CM  = 13.0    # markoer-center -> venstre kant
ROBOT_RIGHT_CM = 13.0    # markoer-center -> hoejre kant

# Konservativ kollisionsradius: afstanden fra markoer-center til robottens
# fjerneste hjoerne. Orienterings-uafhaengig, saa den gaelder uanset hvordan
# robotten er drejet. Udregnes automatisk ud fra de fire vaerdier -- ret ikke i haanden.
import math as _math
ROBOT_RADIUS_CM = max(
    _math.hypot(ROBOT_FRONT_CM, ROBOT_LEFT_CM),
    _math.hypot(ROBOT_FRONT_CM, ROBOT_RIGHT_CM),
    _math.hypot(ROBOT_BACK_CM, ROBOT_LEFT_CM),
    _math.hypot(ROBOT_BACK_CM, ROBOT_RIGHT_CM),
)


# ===========================================================================
# 3. KAMERA
# ===========================================================================
# Brugt i: src/vision/camera.py  (linje 11-14)

CAMERA_INDEX        = 1     # 0 = standard webcam, 1 = ekstern kamera
CAMERA_FRAME_WIDTH  = 1920   # Bredde i pixels
CAMERA_FRAME_HEIGHT = 1080   # Højde i pixels

# Fysisk kamerahøjde over baneoverfladen i cm.
# Brugt i: src/vision/field_map.py (correct_height_offset)
CAMERA_HEIGHT_CM = 155.0

# Højde af ArUco-markørens centrum over baneoverfladen i cm.
# Brugt i: src/vision/field_map.py (correct_height_offset)
ROBOT_MARKER_HEIGHT_CM = 30.0


# ===========================================================================
# 4. VISION / FARVEDETEKTION
# ===========================================================================
# Brugt i: src/vision/color_detector.py  (linje 23)
# Brugt i: src/vision/hsv_utils.py       (linje 5)

# Minimalt areal i pixels² for at en farvedetektion gælder
COLOR_MIN_AREA = 40

# Formfilter til bolddetektion — frasorterer ikke-runde konturer (fx LEGO-klodser).
# Gælder som default for alle farveprofiler; en profil kan opte ud med null
# (se color_profiles/roed.json, der detekterer den rektangulære bane-ramme).
MIN_CIRCULARITY = 0.80        # 4π·areal/omkreds²: 1.0 = perfekt cirkel, firkant ≈ 0.785
MAX_ASPECT_RATIO = 1.4        # max(bredde/højde, højde/bredde) — afviser aflange former

# Sti til mappen med kalibrerede HSV-profiler (.json filer)
# Brugt i: src/vision/hsv_utils.py  (linje 5)
PROFILES_DIR = "color_profiles"

# Brugt i: src/vision/ball_detector.py  (linje 15)
BALL_COLORS = ["orange", "white"]

# Morfologi kernel-størrelse til støjreduktion i masker
# Brugt i: src/vision/color_detector.py  (linje 63) og hsv_utils.py  (linje 24)
MORPH_KERNEL_SIZE = 5


# ===========================================================================
# 5. BANE (FieldMap)
# ===========================================================================
# Brugt i: src/vision/field_map.py  (linje 6)

# Banens fysiske mål i cm  (bredde, højde)
FIELD_SIZE_CM = (167.0, 121.0 )

# Banens hjørner i pixelkoordinater — FALLBACK-VÆRDIER!
# Disse bruges KUN hvis calibration/field_corners.json ikke findes.
# Kør 'python src/vision/field_calibrator.py' for præcis kalibrering →
# den gemmer til calibration/field_corners.json som altid bruges først.
# Format: [(top_left), (top_right), (bottom_right), (bottom_left)]
FIELD_CORNERS_PX = [
    (50,  30),   # top-venstre
    (590, 30),   # top-højre
    (590, 450),  # bund-højre
    (50,  450),  # bund-venstre
]


# ===========================================================================
# 6. NAVIGATION / PLANLÆGNING
# ===========================================================================
# Brugt i: src/planning/command_generator.py  (linje 30 og 34)

# Mindste drejningsvinkel i grader (dead-zone).
# Drejninger mindre end dette ignoreres for at undgaa oscillering.
# Brugt i: src/server/phases/drive_to_ball.py og drive_to_goal.py
MIN_TURN_DEGREES = 10.0

# Ekstra cm robotten kører FORBI boldens position.
# Kompenserer for afstand fra markør til opsamler-åbning.
# Mål afstanden fra den grønne markør til opsamlerens indgang.
COLLECTOR_MOVEMENT_CM = 18

# Max afstand robotten må køre fremad pr. iteration (cm).
# Forhindrer overshoots og sikrer re-evaluering af retning undervejs.
MAX_STEP_CM = 50.0

# Afstand (cm) hvor robotten stopper foran bolden og erklærer den "nået".
# Brugt i: src/server/phases/drive_to_ball.py
DISTANCE_TO_BALL = 10.0

STOP_DISTANCE_CM = 6.0

# Mindste drejningsvinkel i præcisions-zone (tæt på bold).
# Brugt i: src/server/phases/drive_to_ball.py
PRECISION_MIN_TURN_DEGREES = 3
PRECISION_TURN_SPEED = 20

# ===========================================================================
# 7. MÅL OG AFLEVERING (DELIVER)
# ===========================================================================
# Afstand til målet hvor robotten skal stoppe og spytte bolden ud (cm)
DELIVER_DISTANCE_CM = 15

# Afstand til waypoint hvor robotten skifter til direkte mål-kørsel (cm)
# Brugt i: src/server/phases/drive_to_goal.py
WAYPOINT_REACHED_CM = 10

# Standardkoordinater for Mål A og Mål B (bruges hvis calibration/goals.json ikke findes).
# Målt i cm.
GOAL_A_CM = (90.0, 0.0)    # Standard placering top midt
GOAL_B_CM = (90.0, 120.0)  # Standard placering bund midt

# ===========================================================================
# 8. ARUCO MARKØRER
# ===========================================================================
try:
    import cv2
    ARUCO_DICT = cv2.aruco.DICT_4X4_50
except ImportError:
    ARUCO_DICT = 0  # Fallback: cv2.aruco.DICT_4X4_50 is 0

# Robot-markør
ROBOT_MARKER_ID = 42

# Rotations-kompensation hvis markøren er monteret skævt (grader).
# 0 = top-kanten peger mod robottens front (standard).
# 90 = markøren er roteret 90° med uret, osv.
ROBOT_MARKER_ROTATION_OFFSET = -90

# Bane-hjørne-markører (rækkefølge: TL, TR, BR, BL)
FIELD_MARKER_IDS = [0, 1, 2, 3]

# Mål-markører  
GOAL_A_MARKER_ID = 10
GOAL_B_MARKER_ID = 11

# ===========================================================================
# 9. FORHINDRINGER
# ===========================================================================
# Sikkerhedsafstand (cm) omkring forhindringer. Bruges både til A* stifinding
# og til at bestemme afstanden til vores "Approach Point" når en bold samles op.
OBSTACLE_SAFE_RADIUS_CM = 8
# Afstand (cm) fra banden hvor en bold regnes som "kant-bold", og robotten i
# stedet koerer til et approach-punkt langs vaegnormalen (vinkelret indefra),
# saa den ikke rammer banden under opsamling. Brugt i drive_to_ball (#3).
WALL_SAFE_RADIUS_CM = 15.0
# Margin (pixels) som ROI'en krympes indad fra Aruco-banehjørnerne — lille
# sikkerhedsmargin der holder detektion klar af den røde bande.
FIELD_BORDER_MARGIN_PX = 30
# Mindste areal (pixels) for at en rød klat anerkendes som det Røde Kryds
OBSTACLE_MIN_AREA_PX = 150
# Epsilon (cm) for kontur-forenkling via cv2.approxPolyDP.
# Lavere = flere polygon-punkter = mere praecis form.
# Hoejere = faerre punkter = hurtigere pathfinding.
OBSTACLE_CONTOUR_SIMPLIFY_CM = 1.0
