# 🏌️ GolfBot — Autonom Boldindsamler

> CDIO-Projekt: Autonom robot der indsamler bordtennisbolde på en driving range-prototype.

## Oversigt

GolfBot er et to-delt system:

1. **Eye in the Sky** — Et USB-kamera monteret på stativ over banen, tilsluttet en ekstern PC, der håndterer computer vision og ruteplanlægning.
2. **EV3 Robot** — En LEGO Mindstorm EV3-robot der modtager kommandoer og udfører bevægelse og boldopsamling.

## Arkitektur

```
USB Kamera → OpenCV (PC) → Path Planning (PC) → BT/WiFi → EV3 Robot
```

## Projektstruktur

```
src/
├── vision/          # Bolddetektion, forhindringsdetektion, robot-tracking
├── planning/        # Pathfinding (A*), strategi, kommando-generering
├── communication/   # Protokol og forbindelse (BT/WiFi)
├── robot/           # EV3 motorstyring og opsamlermekanisme
└── server/          # Hovedprogram (orchestrator) på ekstern PC
```

## Kom i gang (første gang efter clone/pull)

### 1. Klon repository

```bash
git clone <repository-url>
cd CDIO
```

### 2. Installér dependencies (Ekstern PC)

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
2. Sæt SD-kortet i din PC og kopiér `src/robot/` mappen til kortet
3. Installér dependencies på EV3 (første gang):
   ```bash
   pip3 install -r ev3_requirements.txt
   ```
4. Kør robot-programmet:
   ```bash
   python3 src/robot/main.py
   ```

> **Bemærk:** `python-ev3dev2` kan kun installeres på EV3 med ev3dev OS — ikke på din PC.
> For hurtigere iteration kan man også bruge SSH over Bluetooth i stedet for at flytte SD-kortet.

## Konkurrenceregler

- 11 bordtennisbolde (1 orange VIP-bold)
- 180 × 120 cm bane med kryds-forhindring
- 8 minutter til indsamling
- Mål A (80mm, 150 pt/bold) | Mål B (200mm, 100 pt/bold)
- 200 bonuspoint for orange bold først
- -50 pt for berøring af bane/forhindring

## Team

CDIO Projektgruppe — 2026
