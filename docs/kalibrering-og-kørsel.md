# 🏌️ GolfBot — Kalibrering & Kørsel

> Step-by-step guide til at opsætte, kalibrere og køre GolfBot-systemet fra bunden.
> Alle kommandoer køres fra **projektets rodmappe** (`c:\GitHub\CDIO`) medmindre andet er angivet.

---

## Forudsætninger

Inden du starter, sikrer du dig at:

- [ ] EV3-robotten er tændt og kørende med **ev3dev OS**
- [ ] EV3-robotten er tilsluttet WiFi (samme netværk som PC'en)
- [ ] USB-kameraet er tilsluttet PC'en og hænger over banen på stativet
- [ ] Du har installeret Python-afhængigheder på PC'en:

```powershell
cd c:\GitHub\CDIO
pip install -r requirements.txt
```

---

## Trin 1 — Find robotens IP-adresse

### 1a. SSH ind via USB (første gang)

Tilslut EV3 til PC'en med USB-kablet. Brug SSH over USB-netværket (EV3's standard USB-IP er `10.42.0.3` — se på EV3-displayet):

```powershell
ssh robot@10.42.0.3
```

Adgangskode: `maker`

### 1b. Find WiFi-IP-adressen

Når du er logget ind på EV3, kør:

```bash
ip addr show wlan0
```

Du leder efter en linje der ligner:
```
inet 172.20.10.4/24
```
Det er den IP du skal bruge. Notér den.

### 1c. Opdatér IP i config.py

Åbn `config.py` og ret `ROBOT_IP`:

```powershell
notepad c:\GitHub\CDIO\config.py
```

Find og ret denne linje:
```python
ROBOT_IP = "172.20.10.4"   # <-- Ret til jeres aktuelle IP
```

> **Tip:** Fra nu af kan du SSH direkte over WiFi (næste trin).

---

## Trin 2 — SSH ind på robotten over WiFi

Erstat `172.20.10.4` med den faktiske IP du fandt i trin 1:

```powershell
ssh robot@172.20.10.4
```

Adgangskode: `maker`

Du er nu logget ind på EV3. Terminalen ser sådan ud:
```
Linux ev3dev 4.14.x ...
             _____     _
   _____   _|___ /  __| | _____   __
  / _ \ \ / / |_ \ / _` |/ _ \ \ / /
 |  __/\ V / ___) | (_| |  __/\ V /
  \___| \_/ |____/ \__,_|\___| \_/

Debian stretch on LEGO MINDSTORMS EV3!
robot@ev3dev:~$
```

---

## Trin 3 — Overfør projektfiler til EV3 (første gang)

Åbn en **ny** PowerShell-terminal på din PC (hold SSH-terminalen åben i en anden):

```powershell
# Overfør hele projektet
scp -r c:\GitHub\CDIO\src\robot robot@172.20.10.4:/home/robot/CDIO/src/
scp -r c:\GitHub\CDIO\src\communication robot@172.20.10.4:/home/robot/CDIO/src/
scp c:\GitHub\CDIO\config.py robot@172.20.10.4:/home/robot/CDIO/
```

Adgangskode: `maker`

Opret evt. mappestrukturen på EV3 først (i SSH-terminalen):

```bash
mkdir -p /home/robot/CDIO/src
```

Installer Python-pakker på EV3 (kun første gang, kør i SSH-terminalen):

```bash
pip3 install -r /home/robot/CDIO/ev3_requirements.txt
```

> **Efterfølgende opdateringer:** Hvis du kun har ændret i `config.py`, er det nok at overføre den:
> ```powershell
> scp c:\GitHub\CDIO\config.py robot@172.20.10.4:/home/robot/CDIO/
> ```

---

## Trin 4 — Justér fysiske mål i `config.py`

Inden første kørsel, åbn `config.py` på PC'en og verificer at disse værdier matcher jeres robot:

```powershell
notepad c:\GitHub\CDIO\config.py
```

| Parameter | Standardværdi | Beskrivelse |
|---|---|---|
| `WHEEL_DIAMETER_CM` | `6.88` | Mål hjuldiameteren med en lineal |
| `AXLE_TRACK_CM` | `12.0` | Afstand fra hjulcenter til hjulcenter |
| `MOTOR_LEFT_PORT` | `"B"` | Portbogstavet for venstre motor på EV3 |
| `MOTOR_RIGHT_PORT` | `"D"` | Portbogstavet for højre motor på EV3 |
| `COLLECTOR_MOTOR_PORT` | `"A"` | Port for opsamlermotor |
| `MOTOR_SPEED` | `30` | Kørehastighed i % (0-100) |

> **Vigtigt:** `WHEEL_DIAMETER_CM` og `AXLE_TRACK_CM` påvirker direkte præcisionen af `FORWARD`- og `TURN`-kommandoer. Mål omhyggeligt med en lineal!

Husk at genoverføre `config.py` til EV3 efter ændringer:

```powershell
scp c:\GitHub\CDIO\config.py robot@172.20.10.4:/home/robot/CDIO/
```

---

## Trin 5 — Test opsamlermotoren (valgfrit)

Kør dette på EV3 (via SSH-terminalen) for at verificere at opsamlermotoren virker:

```bash
cd /home/robot/CDIO
python3 src/robot/test_collector.py
```

Forventet output:
```
Initialiserer opsamlingsmotor paa port: A
Koerer forlaens i 20 sekunder med 60% hastighed...
Stopper motoren...
Koerer baglaens i 20 sekunder med 60% hastighed...
Stopper motoren...
Test afsluttet!
```

Hvis motoren ikke reagerer, tjek at den er tilsluttet den korrekte port (`A` som standard).

---

## Trin 6 — Kalibrér farver (PC — én gang per farve)

Farvekalibrering køres på din **PC** og kræver at kameraet er tilsluttet og placeret over banen.

Alle kommandoer køres fra `c:\GitHub\CDIO`:

```powershell
cd c:\GitHub\CDIO
```

### 6a. Kalibrér robotmarkøren (grøn)

```powershell
python src/vision/color_calibrator.py green
```

To vinduer åbner: **"Kalibrering"** og **"Maske"**.

1. **Klik** på den grønne markør på robotten i "Kalibrering"-vinduet.
2. Terminalen bekræfter:
   ```
   Valgt HSV: H=62  S=148  V=201
   ```
3. Brug **sliderne** (H/S/V tolerance) til at justere, så masken i "Maske"-vinduet viser markøren som hvid og resten som sort.
4. Tryk **`s`** for at gemme → `color_profiles/green.json`.
5. Tryk **`q`** for at lukke.

### 6b. Kalibrér orange bold

```powershell
python src/vision/color_calibrator.py orange
```

Klik på en orange bold i billedet. Justér sliders. Gem med **`s`**.

### 6c. Kalibrér hvid bold

```powershell
python src/vision/color_calibrator.py white
```

Hvide bolde er sværest — V-tolerance skal helst ikke gøre hele banen hvid. Justér forsigtigt. Gem med **`s`**.

### Verificér at profilerne er gemt

```powershell
dir c:\GitHub\CDIO\color_profiles
```

Du skal se:
```
green.json
orange.json
white.json
```

---

## Trin 7 — Kalibrér banen (PC — felt-hjørner)

Banekalibreringen fortæller systemet præcist hvor banens 4 hjørner er i kameraets billede.

```powershell
python src/vision/field_calibrator.py
```

Vinduet **"Bane-kalibrering"** åbner sig.

Klik de **4 hjørner i præcis denne rækkefølge** — klik nøjagtigt i banekanten:

```
1 ─────────────────── 2
│                     │
│      (banen)        │
│                     │
4 ─────────────────── 3
```

Terminalen bekræfter hvert klik:
```
  ✓ 1: Øverst-venstre: (130, 39)
  ✓ 2: Øverst-højre: (538, 39)
  ✓ 3: Nederst-højre: (545, 454)
  ✓ 4: Nederst-venstre: (115, 441)
```

Et grønt polygon tegnes rundt om banen.

- Tryk **`s`** for at gemme → `calibration/field_corners.json`
- Tryk **`r`** for at nulstille og starte forfra
- Tryk **`q`** for at afslutte uden at gemme

Verificér at filen er gemt:

```powershell
type c:\GitHub\CDIO\calibration\field_corners.json
```

> **Bemærk:** Kalibrér igen hver gang kameraet flyttes eller justeres.

---

## Trin 8 — Start EV3-robotten (Terminal A)

Robotten skal starte **før** PC-serveren, da den venter på en indgående forbindelse.

Gå til **SSH-terminalen** (Terminal A) og kør:

```bash
cd /home/robot/CDIO
python3 src/robot/main.py
```

Forventet output på EV3:
```
GolfBot EV3 -- venter paa forbindelse...
EV3 venter paa at PC'en forbinder paa port 12345
```

EV3-robotten sidder nu og venter. **Lad terminalen være åben.**

---

## Trin 9 — Start PC-serveren (Terminal B)

Åbn en **ny** PowerShell-terminal på PC'en (Terminal B). Kør fra projektets rodmappe:

```powershell
cd c:\GitHub\CDIO
python src/server/main.py
```

PC'en forsøger at forbinde (op til 5 forsøg med 2 sekunders mellemrum):
```
Forbinder til EV3...
[1/5] Ringer til EV3 paa IP: 172.20.10.4...
Forbundet!
Indlaedte farveprofiler: ['green', 'orange', 'white']
Forbundet! Starter kamera-navigation.
============================================================
```

Samtidig viser **EV3-terminalen** (Terminal A):
```
BINGO! Forbundet til PC'en paa adresse ('172.20.10.4', 54321)
Klar -- venter paa kommandoer...
```

---

## Trin 10 — Initial heading-kalibrering (automatisk)

Systemet kender ikke robotens retning ved opstart. Det kalibrerer automatisk:

```
[1] Ukendt retning. Koerer fremad 10 cm for at kalibrere...
 -> Retning kalibreret til: -12.3 grader
```

Robotten kører 10 cm fremad og systemet beregner retningen ud fra kameraet.

> **Sørg for:** Robotten har mindst **10 cm frit foran sig** ved opstart.

---

## Navigation kører (automatisk)

Efter kalibrering kører systemet selv. PC-terminalen viser løbende status:

```
------------------------------------------------------------
[5] Robot: (45.2, 60.1)  Bold: (120.8, 85.3)
[5] Heading: -12.3  Turn: 24.7  Dist: 79.4 cm
[5] TURN 24.7
[6] FORWARD 20.0
[6] Heading rettet til: 12.1
------------------------------------------------------------
[7] >>> BOLD NAAET! <<<
```

---

## Stop systemet

Tryk **`Ctrl+C`** i **PC-terminalen** (Terminal B):

```
^C
Afbrudt af bruger.
Server afsluttet.
```

EV3-terminalen (Terminal A) viser automatisk:
```
Robot afsluttet.
```

Log ud af SSH:

```bash
exit
```

---

## Hurtig reference — alle kommandoer

### PC (PowerShell fra `c:\GitHub\CDIO`)

```powershell
# Installér afhængigheder (kun første gang)
pip install -r requirements.txt

# Farvekalibrering
python src/vision/color_calibrator.py green
python src/vision/color_calibrator.py orange
python src/vision/color_calibrator.py white

# Banekalibrering
python src/vision/field_calibrator.py

# Start PC-server (orchestrator) — køres EFTER EV3-programmet er startet
python src/server/main.py

# Overfør opdateret config til EV3
scp c:\GitHub\CDIO\config.py robot@172.20.10.4:/home/robot/CDIO/
```

### EV3 (via SSH: `ssh robot@172.20.10.4`, adgangskode: `maker`)

```bash
# Start robot-kommandolytter — køres FØR PC-serveren
cd /home/robot/CDIO
python3 src/robot/main.py

# Test opsamlermotor isoleret
python3 src/robot/test_collector.py

# Find WiFi IP-adresse
ip addr show wlan0

# Genstart robot-program efter nedbrud
pkill -f "python3 src/robot/main.py" ; python3 src/robot/main.py
```

---

## Fejlfinding

### Kan ikke SSH ind på EV3

```powershell
# Prøv USB-IP'en i stedet
ssh robot@10.42.0.3
# Adgangskode: maker
```

Sørg for at EV3's USB-netværk er aktivt (vises på EV3-displayet under "Wireless and Networks").

### "Kunne ikke forbinde til robotten" (PC-server fejler)

1. Kontrollér at EV3-programmet kører (Terminal A skal vise "venter paa forbindelse")
2. Kontrollér at IP'en i `config.py` er korrekt
3. Test at IP'en kan pinges:
   ```powershell
   ping 172.20.10.4
   ```
4. Start altid EV3-programmet **før** PC-serveren

### Farverne genkendes ikke / robotten ses ikke

- Kør farvekalibrering igen under de aktuelle lysforhold
- Kontrollér at profilerderne eksisterer:
  ```powershell
  dir c:\GitHub\CDIO\color_profiles
  ```
- Øg `COLOR_MIN_AREA` i `config.py` for at filtrere støj (standard: 40)

### Robotten drejer forkert

- Mål `AXLE_TRACK_CM` nøjagtigt — placer en lineal fra center af venstre hjul til center af højre hjul
- Bekræft motorportene ved at kigge på EV3-brikken: port `B` og `D` er til store motorer

### Robotten kører for langt/kort

- Mål hjulets diameter: læg en lineal over hjulets midte og mål fra kant til kant
- Opdatér `WHEEL_DIAMETER_CM` og overfør `config.py` til EV3 igen

### Banekalibreringen er unøjagtig

- Klik i selve hjørnet af banens indre kant — ikke yderkanten
- Brug `r` i kalibrerings-vinduet til at nulstille og prøve igen
- Sørg for at kameraet ikke bevæger sig under kørsel

---

## Konfigurationsreference (`config.py`)

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `ROBOT_IP` | `172.20.10.4` | EV3-robotens WiFi IP-adresse |
| `PORT` | `12345` | TCP-port til kommunikation |
| `WHEEL_DIAMETER_CM` | `6.88` | Hjuldiameter i cm |
| `AXLE_TRACK_CM` | `12.0` | Afstand mellem hjulcentre i cm |
| `MOTOR_SPEED` | `30` | Kørehastighed i % (0–100) |
| `MOTOR_LEFT_PORT` | `"B"` | Venstre motor-port på EV3 |
| `MOTOR_RIGHT_PORT` | `"D"` | Højre motor-port på EV3 |
| `COLLECTOR_MOTOR_PORT` | `"A"` | Opsamlermotor-port på EV3 |
| `COLLECTOR_SPEED` | `60` | Opsamler-hastighed i % |
| `CAMERA_INDEX` | `0` | Kamera-index (0 = første USB-kamera) |
| `BALL_COLORS` | `["orange", "white"]` | Bold-farver der søges efter (prioriteret) |
| `MARKER_COLOR` | `"green"` | Robotmarkørens farve |
| `FIELD_SIZE_CM` | `(180, 120)` | Banens fysiske størrelse i cm |
| `MIN_TURN_DEGREES` | `2.0` | Mindste drejningsvinkel (dead-zone) |
| `MIN_DISTANCE_CM` | `3.0` | Afstand til bold der udløser indsamling |
| `MAX_STEP_CM` | `20.0` | Maksimalt fremad-skridt pr. iteration |
| `COLOR_MIN_AREA` | `40` | Minimalt pixel-areal for farvegenkendelse |
