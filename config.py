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

WHEEL_DIAMETER_CM  = 6.88    # Hjuldiameter i cm  (mål dit hjul med en lineal)
AXLE_TRACK_CM      = 12.0    # Afstand mellem hjulcentrene i cm
MOTOR_SPEED        = 30      # Kørehastighed i procent (0-100)

# Bevægelses-ports
# Brugt i: src/robot/motor_controller.py  (linje 16)
MOTOR_LEFT_PORT  = "B"   # Port for venstre motor
MOTOR_RIGHT_PORT = "D"   # Port for højre motor

# Opsamlingsmotor
# Brugt i: src/robot/test_collector.py
COLLECTOR_MOTOR_PORT = "A" # Port for opsamler (ret til A eller C)
COLLECTOR_SPEED      = 40        # Hastighed i procent (0-100)
COLLECTION_SPEED     = 15        # Langsom koerselshastighed under opsamling (0-100)

# Gyroseensor input-port
# Brugt i: src/robot/main.py  (linje 78)
GYRO_PORT = "2"


# ===========================================================================
# 3. KAMERA
# ===========================================================================
# Brugt i: src/vision/camera.py  (linje 11-14)

CAMERA_INDEX        = 0     # 0 = standard webcam, 1 = ekstern kamera
CAMERA_FRAME_WIDTH  = 640   # Bredde i pixels
CAMERA_FRAME_HEIGHT = 480   # Højde i pixels


# ===========================================================================
# 4. VISION / FARVEDETEKTION
# ===========================================================================
# Brugt i: src/vision/color_detector.py  (linje 23)
# Brugt i: src/vision/hsv_utils.py       (linje 5)

# Minimalt areal i pixels² for at en farvedetektion gælder
COLOR_MIN_AREA = 40

# Sti til mappen med kalibrerede HSV-profiler (.json filer)
# Brugt i: src/vision/hsv_utils.py  (linje 5)
PROFILES_DIR = "color_profiles"

# Hvilke farver der bruges til boldsøgning (rækkefølge = prioritet)
# Brugt i: src/vision/ball_detector.py  (linje 15)
BALL_COLORS = ["orange", "white"]

# Farveprofil-navn for robotmarkøren (sticker/farvet objekt på robotten)
# Brugt i: src/server/main.py  og  src/vision/robot_tracker.py
MARKER_COLOR = "green"

# Sekundær markør på bagsiden af robotten for direkte heading-måling.
# Sæt til None for single-markør mode (heading beregnes fra bevægelse).
# Sæt til f.eks. "blue" når I monterer en anden farvet markør bag på robotten.
MARKER_COLOR_BACK = "blue"

# Morfologi kernel-størrelse til støjreduktion i masker
# Brugt i: src/vision/color_detector.py  (linje 63) og hsv_utils.py  (linje 24)
MORPH_KERNEL_SIZE = 5


# ===========================================================================
# 5. BANE (FieldMap)
# ===========================================================================
# Brugt i: src/vision/field_map.py  (linje 6)

# Banens fysiske mål i cm  (bredde, højde)
FIELD_SIZE_CM = (180, 120 )

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

# Mindste drejningsvinkel der sendes som kommando (grader)
# Drej under denne grænse ignoreres (dead-zone)
MIN_TURN_DEGREES = 2.0

# Mindste afstand der sendes som FORWARD-kommando (cm)
# Stop hvis vi allerede er tæt nok på bolden
MIN_DISTANCE_CM = 3.0

# Ekstra cm robotten kører FORBI boldens position.
# Kompenserer for afstand fra markør til opsamler-åbning.
# Mål afstanden fra den grønne markør til opsamlerens indgang.
COLLECTOR_OFFSET_CM = 1

# Max afstand robotten må køre fremad pr. iteration (cm).
# Forhindrer overshoots og sikrer re-evaluering af retning undervejs.
MAX_STEP_CM = 15.0

# Afstand (cm) hvor præcisions-tilnærmelse aktiveres.
# Sæt denne STØRRE end robottens "blinde vinkel" (afstanden hvor kameraet ikke længere kan se bolden).
APPROACH_DISTANCE_CM = 15

# ===========================================================================
# 7. MÅL OG AFLEVERING (DELIVER)
# ===========================================================================
# Afstand til målet hvor robotten skal stoppe og spytte bolden ud (cm)
DELIVER_DISTANCE_CM = 10

# Standardkoordinater for Mål A og Mål B (bruges hvis calibration/goals.json ikke findes).
# Målt i cm.
GOAL_A_CM = (90.0, 0.0)    # Standard placering top midt
GOAL_B_CM = (90.0, 120.0)  # Standard placering bund midt

