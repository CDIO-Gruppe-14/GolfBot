# GolfBot — Software-arkitektur & Repository-opsætning

## Projektresumé

Autonom robot (LEGO Mindstorm EV3) der indsamler 11 bordtennisbolde på en 180×120 cm bane med et kryds som forhindring. Systemet består af to dele: **EV3-robotten** og et **eksternt "Eye in the Sky"-kamera** med en tilhørende computer.

---

## Anbefalet Software-stack

### Oversigt

| Komponent | Teknologi | Begrundelse |
|---|---|---|
| **EV3 OS** | [ev3dev](https://www.ev3dev.org/) (Debian Linux) | Giver fuld Python-adgang til EV3-motorér og sensorer |
| **EV3 sprog** | Python 3 + `python-ev3dev2` | Velunderstøttet, nemt at debugge, hurtig iteration |
| **Computer Vision** | Python 3 + OpenCV (`cv2`) på **ekstern PC** | EV3's 300 MHz CPU er for langsom til billedbehandling |
| **Kommunikation** | Bluetooth (RFCOMM/SPP) eller WiFi (TCP sockets) | ev3dev understøtter begge; WiFi giver lavere latency |
| **Path Planning** | A* eller BFS på grid-baseret kort | Velegnet til det kendte, rektangulære bane-layout |
| **Versionskontrol** | Git + GitHub | Standard for samarbejde i teams |

### Arkitektur-diagram

```
┌─────────────────────────────────────────────────────────┐
│                    EKSTERN PC (Laptop)                   │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │  USB Kamera   │───▶│  OpenCV       │──▶│  Path      │  │
│  │  (Eye in Sky) │    │  Bolddetekt.  │   │  Planner   │  │
│  └──────────────┘    │  + Banekort   │   │  (A*)      │  │
│                      └──────────────┘   └─────┬──────┘  │
│                                               │         │
│                                        Kommandoer       │
│                                         (BT/WiFi)       │
└─────────────────────────────────────┬───────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────┐
│                    LEGO EV3 BRICK                        │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │  Kommando-    │───▶│  Motor-       │──▶│  Motorér   │  │
│  │  modtager     │    │  controller   │   │  & Samler  │  │
│  │  (BT/WiFi)   │    │  (ev3dev)     │   │            │  │
│  └──────────────┘    └──────────────┘   └────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Software-komponenternes ansvar

### 1. Vision-modul (Ekstern PC)

- **Kamera-feed**: Læser frames fra USB-kamera via `cv2.VideoCapture`
- **Bolddetektion**: HSV farve-segmentering til at finde hvide og orange bolde
- **Forhindringsdetektion**: Detekterer krydset og banekanter
- **Robot-tracking**: Detekterer robottens position og orientering
- **Bane-kortlægning**: Opbygger et 2D grid-kort over banen med boldpositioner

### 2. Path Planning-modul (Ekstern PC)

- **A\*-pathfinding**: Finder optimal rute fra robot → bold → mål
- **Strategi**: Prioriterer orange VIP-bold først (200 ekstra point)
- **Kollisionsundgåelse**: Planlægger ruter der undgår kryds og kanter
- **Kommando-generering**: Oversætter rute til motorkommandoer (fremad, drej)

### 3. Kommunikationsmodul

- **Protocol**: Simpel tekst-baseret protokol over Bluetooth/WiFi socket
- **Kommandoer**: `FORWARD <cm>`, `TURN <grader>`, `STOP`, `COLLECT`, `STATUS`
- **Feedback**: EV3 sender sensordata/status tilbage til PC

### 4. Robot-controller (EV3)

- **Motor-styring**: Modtager kommandoer og styrer hjulmotorer + opsamler
- **Sensor-input**: Kan supplere med EV3's egne sensorer (ultralyd, farve)
- **Nødstop**: Stopper ved kollision eller timeout

---

## Anbefalet Mappestruktur

```
CDIO/
├── README.md                    # Projektbeskrivelse
├── .gitignore                   # Git-ignore fil
├── docs/                        # Dokumentation og rapporter
│   ├── kravspecifikation.md
│   └── images/
├── src/
│   ├── vision/                  # Kører på ekstern PC
│   │   ├── __init__.py
│   │   ├── camera.py            # Kamera-feed håndtering
│   │   ├── ball_detector.py     # Bolddetektion (HSV + contours)
│   │   ├── obstacle_detector.py # Forhindringsdetektion
│   │   ├── robot_tracker.py     # Robot-positionering
│   │   └── field_map.py         # Bane-kortlægning
│   ├── planning/                # Kører på ekstern PC
│   │   ├── __init__.py
│   │   ├── pathfinder.py        # A*-pathfinding
│   │   ├── strategy.py          # Boldprioriteringslogik
│   │   └── command_generator.py # Oversæt rute → motorkommandoer
│   ├── communication/           # Fælles modul
│   │   ├── __init__.py
│   │   ├── protocol.py          # Kommando-definitioner
│   │   └── connection.py        # BT/WiFi socket-håndtering
│   ├── robot/                   # Kører på EV3
│   │   ├── __init__.py
│   │   ├── motor_controller.py  # Motorstyring via ev3dev
│   │   ├── collector.py         # Boldopsamlingsmekanisme
│   │   └── main.py              # EV3 hovedprogram
│   └── server/                  # Kører på ekstern PC
│       ├── __init__.py
│       └── main.py              # PC hovedprogram (orchestrator)
├── tests/                       # Unit tests
│   ├── test_ball_detector.py
│   ├── test_pathfinder.py
│   └── test_protocol.py
├── calibration/                 # Kalibreringsscripts
│   ├── camera_calibration.py
│   └── color_tuner.py           # HSV-slider til farvejustering
├── requirements.txt             # Python dependencies (PC)
└── ev3_requirements.txt         # Python dependencies (EV3)
```

---

## Repository-opsætning

### Git Branching-strategi

Vi anbefaler **GitHub Flow** (simpel model, velegnet til et 3-ugers projekt):

```
main ─────────────────────────────────────── (stabil kode)
   └── feature/vision-ball-detection ─────── (feature branches)
   └── feature/pathfinding ──────────────── 
   └── feature/ev3-motor-control ────────── 
   └── fix/bluetooth-latency ────────────── (bugfixes)
```

- `main` = altid kørende, stabil kode
- Feature-branches for nye features
- Pull Requests med minimum 1 reviewer

### `.gitignore` indhold

```gitignore
__pycache__/
*.pyc
.env
venv/
.vscode/
*.mp4
*.avi
```

### `requirements.txt` (Ekstern PC)

```
opencv-python>=4.8.0
numpy>=1.24.0
```

### `ev3_requirements.txt` (EV3)

```
python-ev3dev2
```

---

## Prioriteret Udviklingsplan (matcher jeres milepæle)

| # | Milestone | Software-opgave | Frist |
|---|---|---|---|
| 1 | **Kørende robot** | EV3 motor-styring + grundlæggende BT-kommunikation | 04-03-2026 |
| 2 | **Navigere rundt om forhindringer** | Pathfinding-modul + Vision-based obstacle detection | 25-03-2026 |
| 3 | **Identificere bolde** | OpenCV bolddetektion (HSV + contours) | 08-04-2026 |
| 4 | **Opsamle en bold** | Samlermekanisme + koordinering vision→robot | 22-04-2026 |
| 5 | **Fuld prototype** | Samlet system: detektér → navigér → saml → aflever | 06-05-2026 |
| 6 | **Optimering** | VIP-bold-prioritering, hastighed, mål A vs. B strategi | 12-06-2026 |

---

## Vigtige Beslutninger I Skal Tage

> [!IMPORTANT]
> Følgende spørgsmål bør I afklare internt i gruppen:

1. **Bluetooth vs. WiFi?** — WiFi dongle til EV3 giver lavere latency men kræver ekstra hardware. Bluetooth er built-in men langsommere.
2. **Boldopsamlingsmekanisme** — Skovl/ske vs. klemmemekanisme vs. roterende "fejemaskine". Dette påvirker den fysiske konstruktion.
3. **Mål A (mindre, 150 pt) vs. Mål B (større, 100 pt)?** — Software-strategien bør som udgangspunkt gå efter Mål A for max point, men falde tilbage til B ved navigeringsproblemer.
4. **Én bold ad gangen vs. flere?** — Påvirker kapaciteten af opsamlingsmekanismen og ruteplanlægningen.

---

## Næste Skridt

Hvis I godkender denne plan, sætter jeg følgende op:

1. ✅ Initialiserer Git-repository med mappestruktur
2. ✅ Opretter `.gitignore`, `README.md`, `requirements.txt`
3. ✅ Opretter skeleton-filer med docstrings for hvert modul
4. ✅ Opretter et basalt `color_tuner.py` kalibreringsscript

---

## Verifikationsplan

### Enhedstest
- `test_ball_detector.py`: Test med statiske billeder af bolde
- `test_pathfinder.py`: Test A* med kendte bane-layouts
- `test_protocol.py`: Test kommando-serialisering

### Manuel verifikation
- **Kamera-kalibering**: Kør `color_tuner.py` med kamera monteret over bane → bekræft bolde detekteres
- **Motor-test**: Kør EV3 `main.py` i test-mode → bekræft fremad/bagud/drej fungerer
- **Integration**: Fuld test på banen med timer
