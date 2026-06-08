# GolfBot — Autonom Boldindsamler

> CDIO-Projekt: Autonom robot der indsamler bordtennisbolde på en driving range-prototype.

## Oversigt

GolfBot er et to-delt system:

1. **Eye in the Sky** — Et USB-kamera monteret på stativ over banen, tilsluttet en ekstern PC, der håndterer computer vision og navigation.
2. **EV3 Robot** — En LEGO Mindstorm EV3-robot der modtager kommandoer via WiFi og udfører bevægelse og boldopsamling.

## Arkitektur

```
USB Kamera → OpenCV (PC) → Navigation (PC) → WiFi (TCP) → EV3 Robot
```

## Projektstruktur

```
GolfBot/
├── config.py                # Central konfigurationsfil (deles af PC og EV3)
├── requirements.txt         # Python dependencies (PC)
├── ev3_requirements.txt     # Python dependencies (EV3)
├── src/
│   ├── vision/              # Bolddetektion, farvegenkendelse, robot-tracking, banekalibrering
│   ├── planning/            # Kommando-generering (vinkel/afstand), strategi (stub), pathfinding (stub)
│   ├── communication/       # Protokol og WiFi-forbindelse (TCP sockets)
│   ├── robot/               # EV3 motorstyring, opsamlermekanisme, testscripts
│   └── server/              # Hovedprogram (orchestrator) på ekstern PC
├── calibration/             # Gemte bane-hjørner (field_corners.json)
├── color_profiles/          # Kalibrerede HSV-farveprofiler (.json)
├── tests/                   # Unit tests (test_field.py)
└── docs/                    # Dokumentation
```

## Kom i gang (første gang efter clone/pull)

### 1. Klon repository

```bash
git clone <repository-url>
cd GolfBot
```

### 2. Installer dependencies (Ekstern PC)

```bash
pip install -r requirements.txt
```

Dette installerer:
- **opencv-python** — Computer vision (bolddetektion, kamera)
- **numpy** — Numeriske beregninger

### 3. Kør PC-serveren

```bash
python src/server/main.py
```

### 4. EV3-opsætning (via SD-kort)

1. Flash **ev3dev OS** til det udleverede SD-kort ([guide](https://www.ev3dev.org/docs/getting-started/))
2. Sæt SD-kortet i din PC og kopier `src/robot/` og `src/communication/` samt `config.py` til kortet
3. Installer dependencies på EV3 (første gang):
   ```bash
   pip3 install -r ev3_requirements.txt
   ```
4. Kør robot-programmet:
   ```bash
   python3 src/robot/main.py
   ```

> **Bemærk:** `python-ev3dev2` kan kun installeres på EV3 med ev3dev OS — ikke på din PC.
> For hurtigere iteration kan man også bruge SSH over WiFi i stedet for at flytte SD-kortet.

Se `docs/kalibrering-og-kørsel.md` for en komplet step-by-step guide inkl. farvekalibrering og banekalibrering.

## Implementeringsstatus

| Modul | Status |
|---|---|
| Vision (bolddetektion, robot-tracking, banekort) | Implementeret |
| Farvekalibrering (HSV-profiler) | Implementeret |
| Banekalibrering (felt-hjørner) | Implementeret |
| WiFi-kommunikation (TCP sockets) | Implementeret |
| Motor-styring (FORWARD, TURN) | Implementeret |
| Kamera-baseret navigation (server-loop) | Implementeret |
| Dobbelt-markør heading | Implementeret |
| Boldopsamling (collector) | Delvist — `BallCollector`-klasse eksisterer, men er ikke integreret i `robot/main.py` |
| A*-pathfinding | Ikke implementeret (`pathfinder.py` er tom) |
| Boldstrategi (VIP-prioritering) | Ikke implementeret (`strategy.py` er en stub) |
| Forhindringsdetektion | Ikke implementeret i navigations-loopet |

## Konkurrenceregler

- 11 bordtennisbolde (1 orange VIP-bold)
- 180 x 120 cm bane med kryds-forhindring
- 8 minutter til indsamling
- Mål A (80mm, 150 pt/bold) | Mål B (200mm, 100 pt/bold)
- 200 bonuspoint for orange bold først
- -50 pt for berøring af bane/forhindring

## Team

CDIO Projektgruppe — 2026
