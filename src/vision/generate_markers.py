"""
GolfBot — ArUco Markør-generator
==================================
Genererer alle nødvendige ArUco-markører som printbare PNG-filer.

Kør:
    python src/vision/generate_markers.py

Output:
    markers/  mappen med alle PNG-filer klar til print.

Markør-layout:
    ID  0-3  : Bane-hjørner (TL, TR, BR, BL)
    ID 10-11 : Mål A og B
    ID 42    : Robot (med FRONT-pil)
"""

import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Prøv at importere config — fald tilbage til defaults hvis den ikke findes
try:
    from config import (ARUCO_DICT, ROBOT_MARKER_ID,
                        FIELD_MARKER_IDS, GOAL_A_MARKER_ID, GOAL_B_MARKER_ID)
except ImportError:
    ARUCO_DICT = cv2.aruco.DICT_4X4_50
    ROBOT_MARKER_ID = 42
    FIELD_MARKER_IDS = [0, 1, 2, 3]
    GOAL_A_MARKER_ID = 10
    GOAL_B_MARKER_ID = 11


# Markør-størrelse i pixels (selve ArUco-koden, uden margin)
MARKER_PX = 200

# Hvid margin rundt om markøren (til printning)
MARGIN_PX = 60

# Ekstra plads til label under markøren
LABEL_HEIGHT = 80


def generate_marker(dictionary, marker_id, size_px=MARKER_PX):
    """Generér rå ArUco-markør som grayscale billede."""
    marker_img = cv2.aruco.generateImageMarker(dictionary, marker_id, size_px)
    return marker_img


def add_margin_and_label(marker_img, label, margin=MARGIN_PX,
                         label_h=LABEL_HEIGHT, show_front_arrow=False):
    """Tilføj hvid margin, label og valgfri FRONT-pil."""
    h, w = marker_img.shape[:2]

    # Total billedstørrelse
    total_w = w + 2 * margin
    total_h = h + 2 * margin + label_h
    if show_front_arrow:
        total_h += 50  # Ekstra plads til pil over markøren

    # Opret hvidt canvas (BGR for farvet annotation)
    canvas = np.ones((total_h, total_w, 3), dtype=np.uint8) * 255

    # Placer markør (konvertér til BGR)
    marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
    y_offset = margin + (50 if show_front_arrow else 0)
    canvas[y_offset:y_offset + h, margin:margin + w] = marker_bgr

    # Tegn label under markøren
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(label, font, 0.7, 2)[0]
    text_x = (total_w - text_size[0]) // 2
    text_y = y_offset + h + margin // 2 + text_size[1]
    cv2.putText(canvas, label, (text_x, text_y), font, 0.7, (0, 0, 0), 2)

    if show_front_arrow:
        # Tegn "FRONT" pil over markøren
        arrow_y = margin // 2 + 10
        center_x = total_w // 2

        # Pil: venstre mod højre (= corners[0] → corners[1] = "front")
        # Men vi vil vise det som "op" = robottens kørselsretning
        # Så vi tegner en pil der peger OP over markøren
        arrow_start = (center_x, y_offset - 5)
        arrow_end = (center_x, 15)
        cv2.arrowedLine(canvas, arrow_start, arrow_end,
                        (0, 0, 200), 3, tipLength=0.3)

        # "FRONT" label ved pilen
        ft = cv2.getTextSize("FRONT", font, 0.6, 2)[0]
        cv2.putText(canvas, "FRONT", (center_x - ft[0] // 2, 13),
                    font, 0.6, (0, 0, 200), 2)

        # Tegn hjørne-numre på markøren for reference
        corners_labels = ["c0", "c1", "c2", "c3"]
        # c0=top-left, c1=top-right, c2=bottom-right, c3=bottom-left
        positions = [
            (margin - 25, y_offset - 3),                          # c0: over top-left
            (margin + w + 3, y_offset - 3),                       # c1: over top-right
            (margin + w + 3, y_offset + h + 15),                  # c2: under bottom-right
            (margin - 25, y_offset + h + 15),                     # c3: under bottom-left
        ]
        for lbl, pos in zip(corners_labels, positions):
            cv2.putText(canvas, lbl, pos, font, 0.4, (150, 150, 150), 1)

        # VIGTIGT: Rotér hele billedet 90° mod uret,
        # så "front" (corners[0]→[1], som er vandret top-kant)
        # vises som opadrettet i det printede billede.
        # Dette gør det intuitivt: "print, og peg toppen mod robottens front"
        # ... Nej, vi gør det simplere: vi annoterer bare korrekt.

        # Tilføj monteringsvejledning
        guide = "Mont. med pilen mod robottens koerselsretning"
        gt = cv2.getTextSize(guide, font, 0.45, 1)[0]
        cv2.putText(canvas, guide,
                    ((total_w - gt[0]) // 2, total_h - 10),
                    font, 0.45, (100, 100, 100), 1)

    return canvas


def main():
    # Output-mappe
    project_root = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, "markers")
    os.makedirs(output_dir, exist_ok=True)

    # Opret dictionary
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)

    print("=" * 50)
    print("GolfBot ArUco Marker Generator")
    print("=" * 50)
    print(f"Dictionary: DICT_4X4_50")
    print(f"Output: {output_dir}/")
    print()

    # --- Robot-markør (med FRONT-pil) ---
    marker = generate_marker(dictionary, ROBOT_MARKER_ID)
    img = add_margin_and_label(marker,
                               f"ROBOT (ID {ROBOT_MARKER_ID})",
                               show_front_arrow=True)
    path = os.path.join(output_dir, f"marker_robot_{ROBOT_MARKER_ID}.png")
    cv2.imwrite(path, img)
    print(f"  Robot:        {path}")

    # --- Bane-hjørner ---
    corner_names = ["Top-Venstre (TL)", "Top-Hoejre (TR)",
                    "Bund-Hoejre (BR)", "Bund-Venstre (BL)"]
    for i, marker_id in enumerate(FIELD_MARKER_IDS):
        marker = generate_marker(dictionary, marker_id)
        img = add_margin_and_label(marker,
                                   f"BANE {corner_names[i]} (ID {marker_id})")
        path = os.path.join(output_dir, f"marker_field_{marker_id}.png")
        cv2.imwrite(path, img)
        print(f"  Bane {corner_names[i][:2]}:     {path}")

    # --- Mål-markører ---
    for label, marker_id in [("Maal A", GOAL_A_MARKER_ID),
                              ("Maal B", GOAL_B_MARKER_ID)]:
        marker = generate_marker(dictionary, marker_id)
        img = add_margin_and_label(marker, f"{label} (ID {marker_id})")
        path = os.path.join(output_dir, f"marker_goal_{marker_id}.png")
        cv2.imwrite(path, img)
        print(f"  {label}:       {path}")

    print()
    print(f"Alle {2 + len(FIELD_MARKER_IDS) + 1} markoerer gemt i: {output_dir}/")
    print()
    print("Naeste trin:")
    print("  1. Print alle PNG-filer (helst paa hvidt papir)")
    print("  2. Robot-markoeren: Mont. med FRONT-pilen mod koerselsretning")
    print("  3. Bane-markoerer: Placer i de 4 hjoerner af banen")
    print("  4. Maal-markoerer: Placer ved Maal A og Maal B")
    print("  5. Test med: python src/vision/aruco_detector.py")


if __name__ == "__main__":
    main()
