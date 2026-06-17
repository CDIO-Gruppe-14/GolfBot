"""
GolfBot Kommunikationsprotokol
==============================
Fælles kommandoformat delt mellem PC (server/) og EV3 (robot/).

Kommandoer PC → EV3:
  FORWARD <cm>      — Kør ligeud et antal centimeter
  TURN <grader>     — Drej (positiv = højre, negativ = venstre)
  HEADING           — Anmod om EV3's aktuelle gyro-heading i grader
  STOP              — Stop og afslut kommando-loop

Svar EV3 → PC:
  DONE              — Kommando udført
  HEADING <grader>  — Svar på HEADING-forespørgsel
  ERROR             — Ukendt eller fejlet kommando
"""

# --- Kommando-konstanter ---
FORWARD = "FORWARD"
TURN    = "TURN"
HEADING = "HEADING"
STOP    = "STOP"

# --- Svar-konstanter ---
DONE  = "DONE"
ERROR = "ERROR"


def encode_command(cmd: str, speed: float = None, value: float = None) -> str:
    """
    Formatter en kommando til afsendelse over socket.

    Eksempler:
        encode_command("FORWARD", 42.5)  →  "FORWARD 42.5\\n"
        encode_command("STOP")           →  "STOP\\n"
        encode_command("HEADING")        →  "HEADING\\n"
    """
    if value is not None:
        return "{} {} {}\n".format(cmd, speed, value)
    return "{}\n".format(cmd)


def decode_command(raw):
    """
    Parser en modtaget streng fra socket.

    Eksempler:
        decode_command("FORWARD 42.5\\n")  →  ("FORWARD", 42.5)
        decode_command("STOP\\n")          →  ("STOP", None)
        decode_command("HEADING 182.3\\n") →  ("HEADING", 182.3)

    Returnerer:
        (kommando, værdi) — værdi er None hvis kommandoen ikke har en talværdi
    """
    parts = raw.strip().split()
    if not parts:
        return (ERROR, None)
    cmd = parts[0].upper()
    try:
        speed = float(parts[1]) if len(parts) > 1 else None
        value = float(parts[2]) if len(parts) > 2 else None
    except (ValueError, IndexError):
        value = None
        speed = None
    return cmd, value, speed
