import cv2
import numpy as np
import os

PROFILES_DIR = "color_profiles"


def build_hsv_mask(hsv_frame, h, s, v, h_tol, s_tol, v_tol):
    """Byg en binær maske fra HSV-center + tolerancer. Håndterer hue wraparound."""
    lower = np.array([max(h - h_tol, 0), max(s - s_tol, 0), max(v - v_tol, 0)])
    upper = np.array([min(h + h_tol, 179), min(s + s_tol, 255), min(v + v_tol, 255)])

    mask = cv2.inRange(hsv_frame, lower, upper)

    if h - h_tol < 0:
        lo2 = np.array([h - h_tol + 180, lower[1], lower[2]])
        hi2 = np.array([179, upper[1], upper[2]])
        mask |= cv2.inRange(hsv_frame, lo2, hi2)
    if h + h_tol > 179:
        lo2 = np.array([0, lower[1], lower[2]])
        hi2 = np.array([h + h_tol - 180, upper[1], upper[2]])
        mask |= cv2.inRange(hsv_frame, lo2, hi2)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def hsv_bounds(h, s, v, h_tol, s_tol, v_tol):
    """Returnér (lower, upper) lister til JSON-profil."""
    return (
        [max(int(h - h_tol), 0), max(int(s - s_tol), 0), max(int(v - v_tol), 0)],
        [min(int(h + h_tol), 179), min(int(s + s_tol), 255), min(int(v + v_tol), 255)],
    )
