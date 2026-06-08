# TODO: Implementer ObstacleDetector til detektion af røde kryds-forhindringer på banen.
#
# Formål:
#   Detektere placeringen af det røde kryds (cross-forhindring) på banen,
#   så pathfinderen (A*) kan undgå det under ruteplanlægning.
#
# Planlagt implementering:
#   - Brug ColorDetector med en kalibreret "red" HSV-profil
#   - Returnér en liste af ObstacleZone(x, y, radius) i pixels
#   - Pathfinderen markerer disse zoner som ikke-fremkommelige felter i sit grid
#
# Afhænger af:
#   - src/vision/color_detector.py  (ColorDetector)
#   - src/planning/pathfinder.py    (A* — endnu ikke implementeret)
#   - color_profiles/red.json       (skal kalibreres med color_calibrator.py)
#
# Eksempel på fremtidig API:
#
#   @dataclass
#   class ObstacleZone:
#       x: float       # pixels
#       y: float       # pixels
#       radius: float  # pixels — sikkerhedszone rundt om forhindringen
#
#   class ObstacleDetector:
#       def __init__(self, color_detector, obstacle_color="red"):
#           ...
#
#       def detect(self, frame) -> list[ObstacleZone]:
#           """Returnerer liste af detekterede forhindringszoner."""
#           ...
