# GolfBot — Software-arkitektur & Repository-opsætning

## Projektresume

Autonom robot (LEGO Mindstorm EV3) der indsamler 11 bordtennisbolde på en 180x120 cm bane med et kryds som forhindring. Systemet består af to dele: **EV3-robotten** og et **eksternt "Eye in the Sky"-kamera** med en tilhørende computer.

---

## Software-stack

| Komponent | Teknologi | Begrundelse |
|---|---|---|
| **EV3 OS** | [ev3dev](https://www.ev3dev.org/) (Debian Linux) | Giver fuld Python-adgang til EV3-motorer og sensorer |
| **EV3 sprog** | Python 3 + `python-ev3dev2` | Velunderstøttet, nemt at debugge, hurtig iteration |
| **Computer Vision** | Python 3 + OpenCV (`cv2`) på **ekstern PC** | EV3's 300 MHz CPU er for langsom til billedbehandling |
| **Kommunikation** | WiFi (TCP sockets) | ev3dev understøtter WiFi; giver lav latency |
| **Navigation** | Direkte vinkel/afstands-beregning (kamera-baseret) | Simpelt og effektivt til nuværende behov |
| **Versionskontrol** | Git + GitHub | Standard for samarbejde i teams |

### Arkitektur-diagram

```
┌─────────────────────────────────────────────────────────┐
│                    EKSTERN PC (Laptop)                   │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │  USB Kamera   │───>│  OpenCV       │──>│  Kommando- │  │
│  │  (Eye in Sky) │    │  Bolddetekt.  │   │  beregning │  │
│  └──────────────┘    │  + Banekort   │   │            │  │
│                      └──────────────┘   └─────┬──────┘  │
│                                               │         │
│                                        Kommandoer       │
│                                         (WiFi/TCP)      │
└─────────────────────────────────────┬───────────────────┘
                                      │
                                      v
┌─────────────────────────────────────────────────────────┐
│                    LEGO EV3 BRICK                        │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │  Kommando-    │───>│  Motor-       │──>│  Motorer   │  │
│  │  modtager     │    │  controller   │   │  & Samler  │  │
│  │  (WiFi/TCP)  │    │  (ev3dev)     │   │            │  │
│  └──────────────┘    └──────────────┘   └────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Software-komponenternes ansvar

### 1. Vision-modul (Ekstern PC) — Implementeret

- **Kamera-feed**: Læser frames fra USB-kamera via `cv2.VideoCapture`
- **Farvegenkendelse**: Central `ColorDetector` med kalibrerede HSV-profiler
- **Bolddetektion**: Finder orange og hvide bolde via farvesegmentering
- **Robot-tracking**: Finder robottens position via grøn markør (+ valgfri blå bag-markør for direkte heading)
- **Bane-kortlægning**: Perspektiv-transformation fra pixel til cm-koordinater
- **Kalibrering**: Interaktive værktøjer til farve- og banekalibrering

### 2. Kommando-beregning (Ekstern PC) — Delvist implementeret

- **Vinkel/afstands-beregning**: Beregner drejning og fremad-distance fra robot til bold (implementeret)
- **A*-pathfinding**: Planlagt men **ikke implementeret** (`pathfinder.py` er tom)
- **Strategi**: Planlagt boldprioritering (orange VIP-bold først) men **ikke implementeret** (`strategy.py` er en stub)
- **Forhindringshåndtering**: Ikke implementeret i navigations-loopet

### 3. Kommunikationsmodul — Implementeret

- **Protocol**: Simpel tekst-baseret protokol over WiFi TCP socket
- **Kommandoer PC → EV3**: `FORWARD <cm>`, `TURN <grader>`, `HEADING`, `STOP`, `COLLECT`
- **Svar EV3 → PC**: `DONE`, `ERROR`
- **Forbindelse**: `RobotServer` (EV3) lytter, `PCClient` (PC) forbinder med auto-retry

### 4. Robot-controller (EV3) — Delvist implementeret

- **Motor-styring**: Modtager FORWARD/TURN-kommandoer og styrer hjulmotorer (implementeret)
- **Opsamler**: `BallCollector`-klasse eksisterer men er **ikke integreret** i `main.py` — COLLECT-kommandoen er en stub der svarer DONE uden at gøre noget
- **Heading**: Kamera-baseret (PC-side) — gyro er ikke i brug

---

## Aktuel Mappestruktur

```
GolfBot/
├── README.md                    # Projektbeskrivelse
├── .gitignore                   # Git-ignore fil
├── config.py                    # Central konfiguration (deles af PC og EV3)
├── requirements.txt             # Python dependencies (PC)
├── ev3_requirements.txt         # Python dependencies (EV3)
├── docs/
│   ├── arkitektur.md            # Arkitektur-forklaring med analogi
│   ├── implementation_plan.md   # Denne fil
│   └── kalibrering-og-kørsel.md # Step-by-step guide
├── src/
│   ├── vision/                  # Kører på ekstern PC
│   │   ├── __init__.py
│   │   ├── camera.py            # Kamera-feed håndtering
│   │   ├── color_detector.py    # Central farvegenkendelse (HSV-profiler)
│   │   ├── color_calibrator.py  # Interaktiv farvekalibrering
│   │   ├── ball_detector.py     # Bolddetektion via farve
│   │   ├── robot_tracker.py     # Robot-positionering (dobbelt-markør)
│   │   ├── field_map.py         # Pixel→cm perspektiv-transformation
│   │   ├── field_calibrator.py  # Interaktiv banekalibrering (4 hjørner)
│   │   ├── obstacle_detector.py # Forhindringsdetektion (til fremtidig brug)
│   │   ├── hsv_utils.py         # HSV-hjælpefunktioner og profilindlæsning
│   │   └── find_cameras.py      # Kamera-scanner (find USB-kamera-indeks)
│   ├── planning/                # Kører på ekstern PC
│   │   ├── __init__.py
│   │   ├── command_generator.py # Beregn vinkel og afstand til bold
│   │   ├── pathfinder.py        # (TOM — A* endnu ikke implementeret)
│   │   └── strategy.py          # (STUB — boldprioritering endnu ikke implementeret)
│   ├── communication/           # Fælles modul
│   │   ├── __init__.py
│   │   ├── protocol.py          # Kommando-definitioner og encode/decode
│   │   └── connection.py        # WiFi TCP socket-håndtering
│   ├── robot/                   # Kører på EV3
│   │   ├── __init__.py
│   │   ├── motor_controller.py  # Motorstyring via ev3dev (tank-drev)
│   │   ├── collector.py         # BallCollector-klasse (ikke integreret i main endnu)
│   │   ├── main.py              # EV3 hovedprogram (kommando-lytter)
│   │   ├── test_collector.py    # Test opsamlermotor isoleret
│   │   ├── test_wifi.py         # Test WiFi-forbindelse
│   │   ├── tests/               # Yderligere testscripts
│   │   │   └── drive_and_collect.py
│   │   └── ev3dev2/motor.py     # Stub-modul til PC-import
│   └── server/                  # Kører på ekstern PC
│       ├── __init__.py
│       ├── main.py              # PC hovedprogram (orchestrator)
│       └── test_wifi.py         # Test WiFi fra PC-side
├── calibration/                 # Kalibrerings-data
│   └── field_corners.json       # Gemte bane-hjørner
├── color_profiles/              # Kalibrerede HSV-farveprofiler
│   ├── green.json               # Robot-markør (front)
│   ├── blue.json                # Robot-markør (bag)
│   ├── orange.json              # Orange bold
│   ├── white.json / hvid.json   # Hvid bold
│   └── roed.json                # Rød (forhindring/andet)
└── tests/                       # Unit tests
    └── test_field.py            # Test af FieldMap
```

---

## Repository-opsætning

### Git Branching-strategi

Vi bruger **GitHub Flow** med `develop` som primær branch:

```
develop ──────────────────────────────────── (primær, stabil kode)
   └── feature/vision-ball-detection ─────── (feature branches)
   └── feature/pathfinding ────────────────
   └── feature/pickup ─────────────────────
   └── fix/bluetooth-latency ──────────────  (bugfixes)
```

- `develop` = primær branch med stabil kode
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

## Udviklingsplan

| # | Milestone | Software-opgave | Status |
|---|---|---|---|
| 1 | **Kørende robot** | EV3 motor-styring + WiFi-kommunikation | Implementeret |
| 2 | **Kamera-vision** | OpenCV bolddetektion, farvekalibrering, robot-tracking | Implementeret |
| 3 | **Bane-kortlægning** | Perspektiv-transformation, field_calibrator | Implementeret |
| 4 | **Kamera-navigation** | Server-loop med TURN/FORWARD baseret på kamera | Implementeret |
| 5 | **Dobbelt-markør** | Direkte heading fra to farvede markører | Implementeret |
| 6 | **Boldopsamling** | Integrer `BallCollector` i `robot/main.py` | **TODO** |
| 7 | **Navigere rundt om forhindringer** | A*-pathfinding + obstacle detection i loop | **TODO** |
| 8 | **Boldstrategi** | VIP-bold-prioritering, mål A vs. B | **TODO** |

---

## Vigtige Beslutninger

> [!IMPORTANT]
> Følgende spørgsmål bør afklares:

1. **Boldopsamlingsmekanisme** — `BallCollector`-klassen er klar men skal integreres i `main.py`'s COLLECT-handler.
2. **Mål A (mindre, 150 pt) vs. Mål B (større, 100 pt)?** — Software-strategien bør som udgangspunkt gå efter Mål A for max point, men falde tilbage til B ved navigeringsproblemer.
3. **En bold ad gangen vs. flere?** — Påvirker kapaciteten af opsamlingsmekanismen og ruteplanlægningen.
4. **Forhindringshåndtering** — Aktuelt kører robotten direkte mod bolden uden hensyn til krydset. A*-pathfinding er planlagt.

---

## Verifikationsplan

### Eksisterende tests
- `tests/test_field.py`: Test af FieldMap (pixel→cm transformation)
- `src/robot/test_collector.py`: Manuel test af opsamlermotoren
- `src/robot/test_wifi.py`: Test af WiFi-forbindelse (EV3-side)
- `src/server/test_wifi.py`: Test af WiFi-forbindelse (PC-side)
- `src/robot/tests/drive_and_collect.py`: Kombineret kør-og-saml test

### Manglende tests (TODO)
- Test af bolddetektion med statiske billeder
- Test af kommando-generering (vinkel/afstand)
- Test af protokol encode/decode
- Integrationstest: fuld system på banen med timer

### Manuel verifikation
- **Kamera-kalibrering**: Kør `color_calibrator.py` med kamera over bane — bekræft bolde og markører detekteres
- **Bane-kalibrering**: Kør `field_calibrator.py` — bekræft pixel→cm mapping er korrekt
- **Motor-test**: Kør EV3 `main.py` og send FORWARD/TURN manuelt — bekræft bevægelse
- **Integration**: Fuld test på banen
