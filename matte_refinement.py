"""Opt-in additive repair of small holes and narrow cuts in a binary matte."""
import cv2
import numpy as np


def close_matte_gaps(mask: np.ndarray, radius: int) -> np.ndarray:
    """Close gaps at the chosen pixel scale without removing existing foreground.

    Large openings survive when wider than the kernel. This is geometric cleanup,
    not semantic segmentation: inspect the saved added-pixel mask for each input.
    """
    binary = np.asarray(mask, dtype=bool)
    if radius == 0:
        return binary.copy()
    if radius < 0 or radius > 10:
        raise ValueError("Matte closing radius must be between 0 and 10 pixels.")
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1))
    closed = cv2.morphologyEx(binary.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    return binary | closed.astype(bool)
