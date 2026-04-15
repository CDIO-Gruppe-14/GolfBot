# TODO: Implementer BoldStrategi til at bestemme rækkefølgen af bolde der skal samles op.
#
# Formål:
#   Bestemme hvilken bold robotten skal køre til næst — ikke blot den nærmeste,
#   men ud fra en overordnet strategi der maksimerer point inden for tidsgrænsen.
#
# Regler der påvirker strategien:
#   - 11 bolde i alt (1 orange VIP-bold, 10 hvide)
#   - Orange bold giver 200 bonuspoint HVIS den samles op FØRST
#   - Mål A (lille, 80mm): 150 point/bold
#   - Mål B (stort, 200mm): 100 point/bold
#   - 8 minutter til indsamling
#   - -50 point per berøring af bane/forhindring
#
# Planlagt implementering:
#
#   class BoldStrategi:
#       def __init__(self, ball_detector, field_map):
#           ...
#
#       def vælg_næste_bold(self, alle_bolde, robot_pos, tid_tilbage) -> BallPosition | None:
#           """
#           Returnerer den bold der skal samles op næste gang, baseret på:
#             1. Er orange bold til stede og ikke hentet? → prioritér orange
#             2. Ellers: vælg bold der giver mest point per km kørt
#                (korteste vej til bold + fra bold til mål)
#           """
#           ...
#
# Afhænger af:
#   - src/vision/ball_detector.py  (BallPosition)
#   - src/vision/field_map.py      (pixel → cm)
#   - src/planning/pathfinder.py   (A* — endnu ikke implementeret)
