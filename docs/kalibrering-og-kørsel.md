# GolfBot — Kalibrering & Kørsel

> Step-by-step guide til at opsætte, kalibrere og køre GolfBot-systemet fra bunden.
> Alle kommandoer køres fra **projektets rodmappe** (`GolfBot/`) medmindre andet er angivet.

---

## Forudsætninger

Inden du starter, sørg for at:

- [ ] EV3-robotten er tændt og kørende med **ev3dev OS**
- [ ] EV3-robotten er tilsluttet WiFi (samme netværk som PC'en)
- [ ] USB-kameraet er tilsluttet PC'en og hænger over banen på stativet
- [ ] Du har installeret Python-afhængigheder på PC'en:

```bash
pip install -r requirements.txt
```

---

## Trin 1 — Find robotens IP-adresse

### 1a. SSH ind via USB (første gang)

Tilslut EV3 til PC'en med USB-kablet. Brug SSH over USB-netværket (EV3's standard USB-IP er `10.42.0.3` — se på EV3-displayet):

```bash
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
Det er den IP du skal bruge. Noter den.

### 1c. Opdater IP i config.py

Åbn `config.py` i projektets rod og ret `ROBOT_IP`:

```python
ROBOT_IP = "172.20.10.4"   # <-- Ret til jeres aktuelle IP
```

> **Tip:** Fra nu af kan du SSH direkte over WiFi (næste trin).

---

## Trin 2 — SSH ind på robotten over WiFi

Erstat `172.20.10.4` med den faktiske IP du fandt i trin 1:

```bash
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

Åbn en **ny** terminal på din PC (hold SSH-terminalen åben i en anden):

```bash
# Overfør robot-kode, communication og config
scp -r src robot@172.20.10.2:/home/robot/src
```

Adgangskode: `maker`

Installer Python-pakker på EV3 (kun første gang, kør i SSH-terminalen):

```bash
pip3 install -r /home/robot/CDIO/ev3_requirements.txt
```

> **Efterfølgende opdateringer:** Hvis du kun har ændret i `config.py`, er det nok at overføre den:
> ```bash
> scp config.py robot@172.20.10.4:/home/robot/src/
> ```

---

## Trin 4 — Juster fysiske mål i `config.py`

Inden første kørsel, åbn `config.py` og verificer at disse værdier matcher jeres robot:

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

```bash
scp config.py robot@172.20.10.4:/home/robot/CDIO/
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
Koerer forlaens i 10 sekunder med 60% hastighed...
Stopper motoren...
Koerer baglaens i 10 sekunder med 60% hastighed...
Stopper motoren...
Test afsluttet!
```

> **Bemærk:** Motoren kører faktisk i 20 sekunder per retning (print-beskeden siger 10 men sleep er 20). Tjek at den er tilsluttet den korrekte port (`A` som standard).

---

## Trin 6 — Kalibrer farver (PC — en gang per farve)

Farvekalibrering køres på din **PC** og kræver at kameraet er tilsluttet og placeret over banen.

### 6a. Kalibrer robotmarkøren (grøn — frontmarkør)

```bash
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

### 6b. Kalibrer bagmarkøren (blå — valgfrit men anbefalet)

Hvis robotten har en blå markør på bagsiden (til direkte heading-måling fra kameraet):

```bash
python src/vision/color_calibrator.py blue
```

Klik på den blå markør. Juster sliders. Gem med **`s`**.

> **Tip:** Dobbelt-markør giver langt bedre heading-præcision end enkelt-markør. Konfigurer `MARKER_COLOR_BACK = "blue"` i `config.py` (standard). Sæt til `None` for enkelt-markør mode.

### 6c. Kalibrer orange bold

```bash
python src/vision/color_calibrator.py orange
```

Klik på en orange bold i billedet. Juster sliders. Gem med **`s`**.

### 6d. Kalibrer hvid bold

```bash
python src/vision/color_calibrator.py white
```

Hvide bolde er sværest — V-tolerance skal helst ikke gøre hele banen hvid. Juster forsigtigt. Gem med **`s`**.

### Verificer at profilerne er gemt

```bash
ls color_profiles/
```

Du skal se (minimum):
```
green.json
blue.json
orange.json
white.json
```

---

## Trin 7 — Kalibrer banen (PC — felt-hjørner)

Banekalibreringen fortæller systemet præcist hvor banens 4 hjørner er i kameraets billede.

```bash
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
  1: Øverst-venstre: (130, 39)
  2: Øverst-højre: (538, 39)
  3: Nederst-højre: (545, 454)
  4: Nederst-venstre: (115, 441)
```

Et grønt polygon tegnes rundt om banen.

- Tryk **`s`** for at gemme → `calibration/field_corners.json`
- Tryk **`r`** for at nulstille og starte forfra
- Tryk **`q`** for at afslutte uden at gemme

> **Bemærk:** Kalibrer igen hver gang kameraet flyttes eller justeres.

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

Åbn en **ny** terminal på PC'en (Terminal B). Kør fra projektets rodmappe:

```bash
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

**Med dobbelt-markør (grøn + blå):** Heading aflæses direkte fra kameraet — ingen indledende kørsel nødvendig.

**Med enkelt markør (kun grøn):**
```
[1] Ukendt retning. Koerer fremad 10 cm for at kalibrere...
 -> Retning kalibreret til: -12.3 grader
```

Robotten kører 10 cm fremad og systemet beregner retningen ud fra bevægelsen.

> **Sørg for:** Robotten har mindst **10 cm frit foran sig** ved opstart (kun relevant ved enkelt-markør mode).

---

## Navigation kører (automatisk)

Efter kalibrering kører systemet selv. PC-terminalen viser løbende status:

```
------------------------------------------------------------
[5] Robot: (45.2, 60.1)  Bold: (120.8, 85.3)
[5] Heading: -12.3  Turn: 24.7  Dist: 79.4 cm
[5] TURN 24.7
[6] FORWARD 15.0
[6] Heading rettet til: 12.1
------------------------------------------------------------
[7] >>> BOLD NAAET! <<<
```

> **Bemærk:** Systemet kører aktuelt direkte mod nærmeste bold uden forhindringshåndtering. Boldopsamling (COLLECT) svarer DONE men aktiverer endnu ikke den fysiske opsamler.

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

### PC (fra projektets rodmappe)

```bash
# Installer afhængigheder (kun første gang)
pip install -r requirements.txt

# Farvekalibrering
python src/vision/color_calibrator.py green
python src/vision/color_calibrator.py blue
python src/vision/color_calibrator.py orange
python src/vision/color_calibrator.py white

# Banekalibrering
python src/vision/field_calibrator.py

# Start PC-server (orchestrator) — køres EFTER EV3-programmet er startet
python src/server/main.py

# Overfør opdateret config til EV3
scp config.py robot@172.20.10.4:/home/robot/CDIO/
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

```bash
# Prøv USB-IP'en i stedet
ssh robot@10.42.0.3
# Adgangskode: maker
```

Sørg for at EV3's USB-netværk er aktivt (vises på EV3-displayet under "Wireless and Networks").

### "Kunne ikke forbinde til robotten" (PC-server fejler)

1. Kontroller at EV3-programmet kører (Terminal A skal vise "venter paa forbindelse")
2. Kontroller at IP'en i `config.py` er korrekt
3. Test at IP'en kan pinges:
   ```bash
   ping 172.20.10.4
   ```
4. Start altid EV3-programmet **før** PC-serveren

### Farverne genkendes ikke / robotten ses ikke

- Kør farvekalibrering igen under de aktuelle lysforhold
- Kontroller at profilerne eksisterer:
  ```bash
  ls color_profiles/
  ```
- Øg `COLOR_MIN_AREA` i `config.py` for at filtrere støj (standard: 40)

### Robotten drejer forkert

- Mål `AXLE_TRACK_CM` nøjagtigt — placer en lineal fra center af venstre hjul til center af højre hjul
- Bekræft motorportene ved at kigge på EV3-brikken: port `B` og `D` er til store motorer

### Robotten kører for langt/kort

- Mål hjulets diameter: læg en lineal over hjulets midte og mål fra kant til kant
- Opdater `WHEEL_DIAMETER_CM` og overfør `config.py` til EV3 igen

### Banekalibreringen er unøjagtig

- Klik i selve hjørnet af banens indre kant — ikke yderkanten
- Brug `r` i kalibrerings-vinduet til at nulstille og prøve igen
- Sørg for at kameraet ikke bevæger sig under kørsel

---

## Konfigurationsreference (`config.py`)

### Netværk / Kommunikation

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `ROBOT_IP` | `"172.20.10.4"` | EV3-robotens WiFi IP-adresse |
| `PORT` | `12345` | TCP-port til kommunikation |
| `BUFFER_SIZE` | `1024` | Bytes der læses ad gangen fra socket |
| `MAX_RETRIES` | `5` | Antal genforsøg ved forbindelse |
| `CONNECT_TIMEOUT_SEC` | `5.0` | Timeout per forbindelsesforsøg (sek) |
| `RETRY_DELAY_SEC` | `2` | Ventetid mellem genforsøg (sek) |

### Motor & Bevægelse

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `WHEEL_DIAMETER_CM` | `6.88` | Hjuldiameter i cm |
| `AXLE_TRACK_CM` | `12.0` | Afstand mellem hjulcentre i cm |
| `MOTOR_SPEED` | `30` | Kørehastighed i % (0-100) |
| `MOTOR_LEFT_PORT` | `"B"` | Venstre motor-port på EV3 |
| `MOTOR_RIGHT_PORT` | `"D"` | Højre motor-port på EV3 |
| `COLLECTOR_MOTOR_PORT` | `"A"` | Opsamlermotor-port på EV3 |
| `COLLECTOR_SPEED` | `60` | Opsamler-hastighed i % |
| `GYRO_PORT` | `"2"` | Gyro-sensor input-port (ikke i brug aktuelt) |

### Kamera

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `CAMERA_INDEX` | `0` | Kamera-index (0 = første USB-kamera) |
| `CAMERA_FRAME_WIDTH` | `640` | Bredde i pixels |
| `CAMERA_FRAME_HEIGHT` | `480` | Højde i pixels |

### Vision / Farvedetektion

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `COLOR_MIN_AREA` | `40` | Minimalt pixel-areal for farvegenkendelse |
| `PROFILES_DIR` | `"color_profiles"` | Sti til HSV-profil-mappen |
| `BALL_COLORS` | `["orange", "white"]` | Bold-farver der søges efter (prioriteret) |
| `MARKER_COLOR` | `"green"` | Robotmarkørens farve (front) |
| `MARKER_COLOR_BACK` | `"blue"` | Bagmarkør-farve (`None` = enkelt-markør mode) |
| `MORPH_KERNEL_SIZE` | `5` | Morfologi kernel-størrelse til støjreduktion |

### Bane (FieldMap)

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `FIELD_SIZE_CM` | `(180, 120)` | Banens fysiske størrelse i cm |
| `FIELD_CORNERS_PX` | `[(50,30), ...]` | Fallback pixel-hjørner (bruges kun hvis `field_corners.json` mangler) |

### Navigation / Planlægning

| Parameter | Standard | Beskrivelse |
|---|---|---|
| `MIN_TURN_DEGREES` | `2.0` | Mindste drejningsvinkel (dead-zone) |
| `MIN_DISTANCE_CM` | `3.0` | Afstand til bold der udløser indsamling |
| `COLLECTOR_OFFSET_CM` | `5.0` | Ekstra cm forbi bold (kompenserer markør→opsamler afstand) |
| `MAX_STEP_CM` | `15.0` | Maksimalt fremad-skridt pr. iteration |
| `APPROACH_DISTANCE_CM` | `5.0` | Afstand hvor præcisions-tilnærmelse aktiveres |
