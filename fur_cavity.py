"""Local inward relief and short pile for a guided visible cup interior.

Depth is relative inverse depth (larger is nearer), not physical distance.
The guide must be transported by soft_form before this pass when it is active.
"""
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class CavityResult:
    depth: np.ndarray
    weight: np.ndarray
    recession: np.ndarray
    length_scale: np.ndarray
    diagnostics: dict


def _smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def refine_cavity(depth, mask, opening, amount=0.0, length_scale=1.0):
    """Recess only the interior; leave a protected lip and all outer geometry.

    amount is a maximum decrement in normalized inverse depth. The actual
    decrement is softly limited where the original depth approaches zero.
    Roots are sampled on the pre-cavity surface by the caller, so changing this
    relief does not reduce root density or reshuffle exterior random strands.
    """
    if not np.isfinite(amount) or not 0 <= amount <= 0.12:
        raise ValueError('Cavity depth must be finite and in [0, 0.12].')
    if not np.isfinite(length_scale) or not 0.2 <= length_scale <= 1:
        raise ValueError('Cavity length scale must be finite and in [0.2, 1].')
    depth = np.asarray(depth)
    mask, opening = np.asarray(mask, bool), np.asarray(opening, bool)
    if depth.ndim != 2 or mask.shape != depth.shape or opening.shape != depth.shape:
        raise ValueError('Depth, object mask and opening must be matching 2D arrays.')
    if not np.isfinite(depth).all() or np.any(depth < 0) or np.any(depth > 1):
        raise ValueError('Cavity depth input must be finite and normalized to [0, 1].')
    inside = mask & opening
    if not inside.any() or inside.all():
        raise ValueError('Opening guide must overlap the cup and leave an exterior.')
    scale = min(depth.shape) / 602.0
    distance = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
    # Smooth rasterized guide stair steps; an inner gate prevents blur leakage.
    smoothed = cv2.GaussianBlur(distance, (0, 0), max(1.5*scale, 0.5))
    lip = 5.0 * scale
    gate = _smooth((distance-lip) / max(4.0*scale, 1e-6))
    profile = _smooth((smoothed-lip) / max(float(smoothed.max())-lip, scale)) * gate
    weight = _smooth((smoothed-lip) / max(10.0*scale, 1e-6)) * gate
    # Limit the relief without clipping a broad flat floor into shallow inputs.
    recession = np.minimum(amount, depth*0.8) * profile
    result = depth - recession
    lengths = 1.0 - (1.0-length_scale)*weight
    return CavityResult(result, weight, recession, lengths, {
        'cavity_depth': float(amount), 'cavity_length_scale': float(length_scale),
        'protected_lip_px': float(lip),
        'modified_depth_pixels': int(np.count_nonzero(recession)),
        'max_relative_recession': float(recession.max()),
        'shortened_surface_pixels': int(np.count_nonzero(lengths < 1)),
        'minimum_length_scale': float(lengths.min()),
        'root_sampling': 'pre-cavity geometry; original density and RNG schedule',
    })
