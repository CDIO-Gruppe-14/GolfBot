# Robottens Arkitektur — En Kropslig Analogi

For at gøre koden super nem at forstå og huske, kan vi sammenligne systemets 5 hovedmapper med kroppens dele eller en virksomheds struktur. Dette er et rigtig godt eksempel på at bygge sin kode efter **Separation of Concerns** (modulerne er adskilt med hvert deres klare ansvarsområde).

---

## 1. `vision/` — ØJNENE
**(Kører på den eksterne PC)**

Alt, hvad der har med at "se" og forstå verden, bor her. Den får et råt billede fra USB-kameraet oppe i loftet og omsætter det til brugbare data for resten af programmet.

**Dens job:** At kigge på billedet og sige: *"Robotten er på koordinat (40, 60), bolden er på (120, 30)."*

**Filer indeni:**
- `camera.py`: Tager selve billedet fra USB-kameraet.
- `color_detector.py`: Central farvegenkendelse — indlæser HSV-profiler og finder farvede objekter i frames.
- `ball_detector.py`: Bruger `color_detector` til at finde orange/hvide bolde.
- `robot_tracker.py`: Finder robottens position (og evt. retning) via grøn + blå markør.
- `field_map.py`: Bane-kortlægning — oversætter pixel-koordinater til cm via perspektiv-transformation.
- `field_calibrator.py`: Kalibreringsværktøj — klik banens 4 hjørner for at gemme `calibration/field_corners.json`.
- `color_calibrator.py`: Kalibreringsværktøj — klik på en farve og juster HSV-sliders, gemmer til `color_profiles/`.
- `hsv_utils.py`: Hjælpefunktioner til HSV-masker og profilindlæsning.
- `obstacle_detector.py`: Forhindringsdetektion (til fremtidig brug).
- `find_cameras.py`: Hjælpescript der scanner kamera-indekser for at finde det rigtige kamera.

---

## 2. `planning/` — HJERNEN
**(Kører på den eksterne PC)**

Når Øjnene har fortalt, hvor alting er, tager Hjernen over. Den beregner hvilken retning robotten skal dreje og hvor langt den skal køre.

**Dens job:** At regne ud og sige: *"Vi er på (40,60). Bolden er på (120,30). Vi skal dreje -45 grader og køre 20 cm fremad."*

**Filer indeni:**
- `command_generator.py`: Beregner drejningsvinkel og fremad-afstand fra robot til bold. Begrænser skridt-størrelse for at undgå overshoot.
- `pathfinder.py`: Reserveret til A*-algoritmen — **ikke implementeret endnu** (tom fil).
- `strategy.py`: Reserveret til boldprioriterings-logik (orange VIP-bold først) — **ikke implementeret endnu** (stub med kommentarer).

> **Bemærk:** Aktuelt navigerer systemet direkte mod nærmeste bold uden ruteberegning eller forhindringshåndtering. Pathfinding og strategi er planlagt men ikke implementeret.

---

## 3. `communication/` — NERVESYSTEMET / TELEFONEN
**(Deles af både PC og EV3)**

Dette er bindeleddet. Uden denne mappe aner Hjernen (PC) ikke, hvordan den skal få fat i Musklerne (EV3), og Musklerne ved ikke, hvem de skal lytte til.

**Dens job:** At sørge for, at beskeden (*"Kør 40 cm frem"*) kommer sikkert fra PC'en gennem WiFi (TCP socket) ned til EV3'en.

**Filer indeni:**
- `connection.py`: Opsætter WiFi-forbindelsen via TCP sockets. `RobotServer` kører på EV3 og lytter, `PCClient` kører på PC'en og forbinder.
- `protocol.py`: Kommando-format; definerer at det f.eks. staves `FORWARD 40\n`. Understøttede kommandoer: `FORWARD`, `TURN`, `HEADING`, `STOP`, `COLLECT`.

---

## 4. `robot/` — MUSKLERNE
**(Kører på EV3 robotten)**

Denne mappe ligger fysisk nede på LEGO-klodsen. Den har ingen anelse om, at der findes en bane, et kamera eller bolde. Den er "dum", men den er utrolig god til at udføre præcise ordrer.

**Dens job:** At tænde og slukke for strømmen til de rigtige motor-porte og stoppe præcist, når de rigtige grader/centimeter er nået.

**Filer indeni:**
- `motor_controller.py`: Beregner hjul-rotationer og styrer tank-drevet (venstre/højre motor).
- `collector.py`: `BallCollector`-klasse der styrer opsamlingsmotoren (ind/ud/stop). **Bemærk:** Endnu ikke integreret i `main.py` — COLLECT-kommandoen er en stub.
- `main.py`: Selve programmet, der starter EV3'en op, lytter på WiFi og udfører modtagne kommandoer.
- `test_collector.py`: Test-script der kører opsamlermotoren frem og tilbage.
- `test_wifi.py`: Test-script til WiFi-forbindelse.
- `tests/drive_and_collect.py`: Kombineret kør-og-saml test.
- `ev3dev2/motor.py`: Stub-modul (bruges til at kunne importere på PC uden ev3dev).

---

## 5. `server/` — DIRIGENTEN / CHEFEN
**(Kører på den eksterne PC)**

Hver af de andre mapper er super gode til deres specifikke job, men de ved ikke, *hvornår* de skal gøre det. Dirigenten (hovedprogrammet på PC'en) binder det hele sammen i et evigt loop.

**Dens job:** At uddelegere opgaverne i den rigtige rækkefølge.

**Dirigentens loop (`main.py`):**
1. *"Øjne (`vision`), giv mig robottens og boldens position!"*
2. *"Beregn vinkel og afstand til bolden (`planning`)!"*
3. *"Telefon (`communication`), send TURN/FORWARD-kommando til EV3'en og vent på DONE!"*
4. *"Tag nyt billede, opdater heading, og start forfra!"*

Ekstra features:
- **Dobbelt-markør heading**: Hvis robotten har to farvede markører (front: grøn, bag: blå), beregnes heading direkte fra kameraet.
- **Enkelt-markør fallback**: Heading estimeres fra bevægelsesretning efter FORWARD-kommandoer.
- **Præcisions-tilnærmelse**: Når robotten er tæt på bolden, retter den vinkel præcist og kører den sidste distance i ét ryk.

---

> **Tip til fremlæggelse/Eksamen:** Når I forklarer arkitekturen på denne måde, viser I 100% forståelse for **Separation of Concerns**. Det beviser at koden ikke blot er blandet sammen i en stor fil, men har et gennemtænkt og let-testbart design.

---

## 6. Systemarkitektur Diagram

Herunder er et Mermaid-diagram, der visuelt opsummerer ovenstående struktur og dataflow.

```mermaid
flowchart TD
    %% Kamera
    Kamera["USB Kamera<br>(Monteret over banen)"]

    %% Ekstern PC
    subgraph PC ["Ekstern PC (Hjerne & Øjne)"]
        Server["server/<br>Dirigenten (Hovedprogram)"]
        Vision["vision/<br>Øjnene (OpenCV & Tracker)"]
        Planning["planning/<br>Kommando-beregning"]
    end

    %% Netværk / Delt
    subgraph Netvaerk ["Netværk (Delt)"]
        Comm["communication/<br>Nervesystemet (WiFi / TCP Sockets)"]
    end

    %% EV3 Robot
    subgraph EV3 ["LEGO EV3 (Muskler)"]
        Robot["robot/<br>Musklerne (Motor-styring)"]
    end

    %% Flow og forbindelser
    Kamera -->|Sender RAW Billede| Vision
    Server -->|1. Hent (X,Y) for robot, bolde| Vision
    Vision -->|Returnerer koordinater| Server
    Server -->|2. Send koordinater for at få vinkel/afstand| Planning
    Planning -->|Returnerer TURN/FORWARD-kommando| Server
    Server -->|3. Send kommando via protokol| Comm
    Comm <-->|4. WiFi (TCP)| Robot
    Robot -->|5. Udfører bevægelse og svarer 'DONE'| Comm
    Comm -->|6. Videregiver 'DONE' status| Server

    %% Styling
    classDef hardware fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    classDef pc fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000
    classDef network fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000
    classDef ev3 fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000

    class Kamera hardware
    class Server,Vision,Planning pc
    class Comm network
    class Robot ev3
```
