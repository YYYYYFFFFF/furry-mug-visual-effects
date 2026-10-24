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


def _smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def rear_rim_region(object_mask, opening):
    """Local upper silhouette scope; roots must lie on the actual mug matte."""
    mask = np.asarray(object_mask, dtype=bool)
    guide = np.asarray(opening, dtype=bool)
    if mask.shape != guide.shape or not mask.any() or not guide.any() or guide.all():
        raise ValueError('Object matte and opening guide must be valid and the same size.')
    scale = min(mask.shape) / 602.0
    gy, gx = np.where(guide)
    cy = (gy.min() + gy.max()) * 0.5
    ry = max((gy.max() - gy.min()) * 0.5, 1)
    y = np.arange(mask.shape[0], dtype=np.float32)[:, None]
    rear = _smooth((cy - y) / (0.65 * ry))
    inner = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    outer = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
    guide_distance = cv2.distanceTransform((~guide).astype(np.uint8), cv2.DIST_L2, 5)
    guide_distance -= cv2.distanceTransform(guide.astype(np.uint8), cv2.DIST_L2, 5)
    near_opening = _smooth((guide_distance + 4 * scale) / (4 * scale))
    near_opening *= 1 - _smooth((guide_distance - 22 * scale) / (8 * scale))
    # Allow genuinely new coverage beyond the old fur silhouette. Fade only at
    # the explicit local scope boundary, not against the old alpha footprint.
    support = rear * near_opening
    support *= 1 - _smooth((inner - 3 * scale) / (5 * scale))
    support *= 1 - _smooth((outer - 12 * scale) / (4 * scale))
    roots = support * mask * (inner <= 6 * scale)
    field = cv2.GaussianBlur(outer - inner, (0, 0), 1.25)
    dx = cv2.Sobel(field, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(field, cv2.CV_32F, 0, 1, ksize=3)
    return support.astype(np.float32), roots.astype(np.float32), np.arctan2(dy, dx)


def apply_rear_rim_fringe(final_rgb, source_rgb, object_mask, opening,
                          strength=0.85, supersample=4, environment_blend=0.12):
    """Grow fine outward fibres at the guided rear lip, including new coverage.

    Upper-half placement assumes an upright frontal mug photograph. The existing
    matte determines the roots, while the permitted silhouette band can extend
    into background. The front lip, body and deep opening remain untouched.
    """
    if not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError('Rear-rim strength must be finite and between 0 and 1.')
    support, roots, direction = rear_rim_region(object_mask, opening)
    if final_rgb.shape != (*support.shape, 3) or final_rgb.dtype != np.uint8:
        raise ValueError('Rear-rim finishing expects a same-size RGB uint8 image.')
    if source_rgb.shape != final_rgb.shape:
        raise ValueError('Source RGB must match the final image.')
    if strength == 0:
        return final_rgb.copy(), np.zeros_like(support), support, 0
    ys, xs = np.where(roots > 0.05)
    if not len(xs):
        raise ValueError('No rear-rim roots found where the guide meets the object silhouette.')
    image = final_rgb.astype(np.float32) / 255
    mask = np.asarray(object_mask, np.float32)
    colour = cv2.GaussianBlur(image * mask[..., None], (0, 0), 2.0)
    colour /= np.maximum(cv2.GaussianBlur(mask, (0, 0), 2.0)[..., None], 1e-6)
    # Sample the original background for tip tint, not existing rendered fur.
    canvas = FineFurCanvas(source_rgb, object_mask, 0.34, supersample, environment_blend)
    rng = np.random.default_rng(20261026)
    t = np.linspace(0, 1, 9, dtype=np.float32)
    scale = min(mask.shape) / 602.0
    count = 0
    for x, y in zip(xs, ys):
        expected = 2.2 * float(roots[y, x])
        repeats = int(expected) + int(rng.random() < expected % 1)
        for _ in range(repeats):
            angle = direction[y, x] + rng.uniform(-0.55, 0.55)
            forward = np.array([np.cos(angle), np.sin(angle)], np.float32)
            tangent = np.array([-forward[1], forward[0]], np.float32)
            length = rng.uniform(4.5, 8.0) if rng.random() < 0.7 else rng.uniform(8, 12)
            length *= scale
            bend = rng.uniform(-0.6, 0.6) * length
            root = np.array([x, y], np.float32) + rng.uniform(-0.4, 0.4, 2)
            hair = np.zeros((len(t), 3), np.float32)
            hair[:, :2] = root + t[:, None] * length * forward
            hair[:, :2] += (t * (1-t))[:, None] * bend * tangent
            brightness = rng.uniform(0.9, 1.16)
            colour_ramp = np.linspace(0.96, 1.12, len(t)-1)[:, None]
            colors = np.clip(colour[y, x][None, :] * brightness * colour_ramp, 0, 1)
            canvas.draw_strand(hair, colors.astype(np.float32), count)
            count += 1
    rgb, alpha = canvas.finish()
    alpha *= support * strength
    mixed = image * (1-alpha[..., None]) + rgb * alpha[..., None]
    result = final_rgb.copy()
    active = alpha > 0
    result[active] = np.rint(np.clip(mixed[active], 0, 1) * 255).astype(np.uint8)
    return result, alpha, support, count
