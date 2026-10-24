"""Local rim finishing guided by an image-specific mask of the cup opening."""
import cv2
import numpy as np
from fur_strokes import FineFurCanvas


def rim_band(opening: np.ndarray, coverage: np.ndarray):
    """Return a feathered band and outward direction around the opening guide."""
    opening = np.asarray(opening, dtype=bool)
    if opening.shape != coverage.shape or not opening.any() or opening.all():
        raise ValueError("Opening guide must match the image and contain both regions.")
    outside = cv2.distanceTransform((~opening).astype(np.uint8), cv2.DIST_L2, 5)
    inside = cv2.distanceTransform(opening.astype(np.uint8), cv2.DIST_L2, 5)
    signed = outside - inside
    # Widths are about 3 px inward / 12 px outward on the current 602 px inputs.
    scale = min(opening.shape) / 602.0
    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)
    weight = smooth((signed + 3 * scale) / (3 * scale))
    weight *= 1 - smooth((signed - 7 * scale) / (5 * scale))
    weight *= np.clip(coverage, 0, 1)
    field = cv2.GaussianBlur(signed, (0, 0), 0.8)
    dx = cv2.Sobel(field, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(field, cv2.CV_32F, 0, 1, ksize=3)
    return weight.astype(np.float32), np.arctan2(dy, dx)


def apply_rim_detail(final_rgb: np.ndarray, opening: np.ndarray,
                     coverage: np.ndarray, strength: float = 0.75,
                     supersample: int = 4):
    """Add fine interleaved rim fibres; pixels outside the band are byte-preserved.

    This is an explicit image-space finishing pass, not automatic rim detection
    or a change to the primary geometry, global density or interior-wall model.
    """
    if not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("Rim detail strength must be finite and between 0 and 1.")
    weight, direction = rim_band(opening, coverage)
    if final_rgb.shape != (*weight.shape, 3) or final_rgb.dtype != np.uint8:
        raise ValueError("Rim finishing expects a same-size RGB uint8 image.")
    if strength == 0:
        return final_rgb.copy(), np.zeros_like(weight), weight, 0
    support = weight > 0
    if not support.any():
        raise ValueError("Opening guide's rim band does not overlap rendered fur.")
    image = final_rgb.astype(np.float32) / 255
    # Keep colour from the selected rim itself, without mixing in the background.
    colour_sum = cv2.GaussianBlur(image * weight[..., None], (0, 0), 1.4)
    colour_weight = cv2.GaussianBlur(weight, (0, 0), 1.4)
    colour = colour_sum / np.maximum(colour_weight[..., None], 1e-6)
    canvas = FineFurCanvas(image, coverage > 0, width_scale=0.38,
                           supersample=supersample, environment_blend=0)
    ys, xs = np.where(weight > 0.08)
    rng = np.random.default_rng(20261025)
    ids = rng.choice(len(xs), size=int(len(xs) * 1.5), replace=True)
    t = np.linspace(0, 1, 7, dtype=np.float32)
    scale = min(weight.shape) / 602.0
    for index, pixel in enumerate(ids):
        x, y = xs[pixel], ys[pixel]
        angle = direction[y, x] + rng.uniform(-1.15, 1.15)
        forward = np.array([np.cos(angle), np.sin(angle)], np.float32)
        sideways = np.array([-forward[1], forward[0]], np.float32)
        length = rng.uniform(3, 7) * scale
        bend = rng.uniform(-0.45, 0.45) * length
        root = np.array([x, y], np.float32) + rng.uniform(-0.45, 0.45, 2)
        hair = np.zeros((len(t), 3), np.float32)
        hair[:, :2] = root + t[:, None] * length * forward
        hair[:, :2] += (t * (1-t))[:, None] * bend * sideways
        brightness = rng.uniform(0.75, 1.22)
        segment_colour = np.clip(colour[y, x] * brightness, 0, 1)
        colors = segment_colour[None, :] * np.linspace(0.96, 1.04, len(t)-1)[:, None]
        canvas.draw_strand(hair, np.clip(colors, 0, 1).astype(np.float32), index)
    rgb, alpha = canvas.finish()
    alpha *= weight * strength
    mixed = np.clip(image * (1-alpha[..., None]) + rgb * alpha[..., None], 0, 1)
    result = final_rgb.copy()
    changed = alpha > 0
    result[changed] = np.rint(mixed[changed] * 255).astype(np.uint8)
    return result, alpha, weight, len(ids)
