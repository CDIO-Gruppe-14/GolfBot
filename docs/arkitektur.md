# Robottens Arkitektur – En Kropslig Analogi 🤖

For at gøre koden super nem at forstå og huske, kan vi sammenligne systemets 5 hovedmapper med kroppens dele eller en virksomheds struktur. Dette er et rigtig godt eksempel på bygge sin kode efter **Separation of Concerns** (modulerne er adskilt med hvert deres klare ansvarsområde).

---

## 1. `vision/` 👀 — ØJNENE
**(Kører på den eksterne PC)**

Alt, hvad der har med at "se" og forstå verden, bor her. Den får et råt billede fra USB-kameraet oppe i loftet og omsætter det til brugbare data for resten af programmet.

**Dens job:** At kigge på billedet og sige: *"Robotten er på koordinat (40, 60), bolden er på (120, 30), og der er et rødt kryds på (90, 60)."*

**Filer indeni:**
- `camera.py`: Tager selve billedet.
- `ball_detector.py`: Leder efter orange/hvide farver.
- `robot_tracker.py`: Leder efter den grønne plet på robotten.

---

## 2. `planning/` 🧠 — HJERNEN
**(Kører på den eksterne PC)**

Når Øjnene har fortalt, hvor alting er, tager Hjernen over. Den kigger på banen ligesom et skakbræt og lægger en plan. Den styrer ikke nogen motorer; den tænker kun.

**Dens job:** At regne ud og sige: *"Okay, vi er på (40,60). Bolden er på (120,30). Krydset er i vejen. Den klogeste rute er at køre venstre om krydset. Først skal vi dreje -45 grader og køre 42 cm."*

**Filer indeni:**
- `pathfinder.py`: A* algoritmen, der finder den korteste rute uden at ramme forhindringer.
- `command_generator.py`: Oversætter ruten til konkrete grader og centimeter.

---

## 3. `communication/` 🗣️ — NERVESYSTEMET / TELEFONEN
**(Deles af både PC og EV3)**

Dette er bindeleddet. Uden denne mappe aner Hjernen (PC) ikke, hvordan den skal få fat i Musklerne (EV3), og Musklerne ved ikke, hvem de skal lytte til.

**Dens job:** At sørge for, at beskeden (*"Kør 40 cm frem"*) kommer sikkert fra PC'en gennem luften (via WiFi) ned til EV3'en.

**Filer indeni:**
- `connection.py`: Opsætter WiFi-forbindelsen og sockets.
- `protocol.py`: Ordbogen; definerer at det f.eks. staves `FORWARD 40\n`.

---

## 4. `robot/` 💪 — MUSKLERNE
**(Kører på EV3 robotten)**

Denne mappe ligger fysisk nede på LEGO-klodsen. Den har ingen anelse om, at der findes en bane, et kamera eller bolde. Den er "dum", men den er utrolig god til at udføre præcise ordrer.

**Dens job:** At tænde og slukke for strømmen til de rigtige motor-porte, aflæse gyro-sensoren, og stoppe præcist, når de rigtige grader/centimeter er nået.

**Filer indeni:**
- `motor_controller.py`: Beregner hjul-rotationer og aflæser gyro.
- `collector.py`: Styrer den specifikke motor, der fejer/samler bolden op.
- `main.py`: Selve programmet, der starter EV3'en op og lytter efter WiFi.

---

## 5. `server/` 🎼 — DIRIGENTEN / CHEFEN
**(Kører på den eksterne PC)**

Hver af de andre mapper er super gode til deres specifikke job, men de ved ikke, *hvornår* de skal gøre det. Dirigenten (hovedprogrammet på PC'en) binder det hele sammen i et evigt loop.

**Dens job:** At uddelegere opgaverne i den rigtige rækkefølge.

**Eksempel på Dirigentens loop (`main.py`):**
1. *"Øjne (`vision`), giv mig robottens og boldens position!"*
2. *"Hjerne (`planning`), her er positionerne. Beregn en rute og giv mig første kommando!"*
3. *"Telefon (`communication`), send lige denne kommando til EV3'en og råb op, når den svarer DONE!"*
4. *"Okay, den er DONE. Vi starter forfra!"*

---

> **Tip til fremlæggelse/Eksamen:** Når I forklarer arkitekturen på denne måde, viser I 100% forståelse for **Separation of Concerns**. Det beviser at koden ikke blot er blandet sammen i én stor fil, men har et gennemtænkt og let-testbart design. Det giver topkarakter i software-design! 🚀

---

## 6. Systemarkitektur Diagram

Herunder er et Mermaid-diagram, der visuelt opsummerer ovenstående struktur og dataflow. Diagrammet kan indsættes direkte i Markdown-understøttede rapport-værktøjer (som f.eks. GitHub, Notion, overleaf pga. mermaid integrering) eller eksporteres som et billede.

```mermaid
flowchart TD
    %% Kamera
    Kamera["📷 USB Kamera<br>(Monteret over banen)"]

    %% Ekstern PC
    subgraph PC ["💻 Ekstern PC (Hjerne & Øjne)"]
        Server["🎼 server/<br>Dirigenten (Hovedprogram)"]
        Vision["👀 vision/<br>Øjnene (OpenCV & Tracker)"]
        Planning["🧠 planning/<br>Hjernen (A* Ruteplanlægning)"]
    end

    %% Netværk / Delt
    subgraph Netværk ["📶 Netværk (Delt)"]
        Comm["🗣️ communication/<br>Nervesystemet (WiFi/Sockets)"]
    end

    %% EV3 Robot
    subgraph EV3 ["🤖 LEGO EV3 (Muskler)"]
        Robot["💪 robot/<br>Musklerne (Motor & Gyro)"]
    end

    %% Flow og forbindelser
    Kamera -->|Sender RAW Billede| Vision
    Server -->|1. Hent (X,Y) for robot, bolde, mm.| Vision
    Vision -->|Returnerer koordinater| Server
    Server -->|2. Send koordinater for at få rute| Planning
    Planning -->|Returnerer næste bevægelses-kommando<br>(fx. FORWARD 40)| Server
    Server -->|3. Send kommando via protokol| Comm
    Comm <-->|4. Trådløs overførsel| Robot
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
