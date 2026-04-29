"""
GolfBot - Kamera-finder
========================
Scanner alle kamera-indekser og backends for at finde det eksterne kamera.
Koer: python src/vision/find_cameras.py
"""

import cv2
import sys


def scan_cameras(max_index=10):
    """Proever forskellige indekser OG backends for at finde alle kameraer."""

    # Paa Windows er DirectShow (DSHOW) ofte bedre til eksterne kameraer
    backends = [
        ("Standard (MSMF)",  cv2.CAP_MSMF),
        ("DirectShow",       cv2.CAP_DSHOW),
        ("Ingen backend",    cv2.CAP_ANY),
    ]

    print("=" * 60)
    print("  GolfBot Kamera-scanner")
    print("=" * 60)

    found = []

    for backend_name, backend_id in backends:
        print(f"\n-- Backend: {backend_name} --")
        for idx in range(max_index):
            cap = cv2.VideoCapture(idx, backend_id)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                ret, frame = cap.read()
                status = "OK - frame laest" if ret else "Aaben men ingen frame"
                print(f"  [OK] Index {idx}: {w}x{h} - {status}")
                found.append((idx, backend_name, backend_id, w, h))
                cap.release()
            else:
                cap.release()

    if not found:
        print("\n  [X] Ingen kameraer fundet overhovedet!")
        return

    print("\n" + "=" * 60)
    print("  Fundne kameraer:")
    print("=" * 60)
    for idx, bname, bid, w, h in found:
        print(f"  Index {idx} via {bname} - {w}x{h}")

    print("\n-- Live preview --")
    print("Tryk SPACE for at skifte kamera, 'q' for at afslutte\n")

    # Vis hvert fundet kamera saa brugeren kan se hvilket der er det rigtige
    current = 0
    while current < len(found):
        idx, bname, bid, w, h = found[current]
        print(f"  Viser: Index {idx} via {bname}")
        cap = cv2.VideoCapture(idx, bid)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"  Kunne ikke laese frame fra index {idx}")
                break

            label = f"Index {idx} | {bname} | SPACE=naeste | q=afslut"
            cv2.putText(frame, label, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("Kamera-scanner", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key == ord(' '):
                break

        cap.release()
        current += 1

    cv2.destroyAllWindows()
    print("\nAlle kameraer vist. Opdater CAMERA_INDEX i config.py")
    print("Hvis dit kamera kun virker med DirectShow, se nedenfor.")


if __name__ == "__main__":
    scan_cameras()
