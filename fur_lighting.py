"""Opt-in coherent strand brightness and soft directional glints.

An artistic image-space refinement, not a physical hair-scattering model.
No geometry, opacity, draw order or shared RNG state is changed.
"""
from __future__ import annotations

import numpy as np


def _random01(index: int, salt: int) -> float:
    # Independent hashed samples avoid adjacent-ID bands and never consume the
    # geometry/colour generator. Existing strand IDs remain stable after sorting.
    value = (int(index) ^ salt) & 0xffffffff
    value = ((value ^ (value >> 16)) * 0x7feb352d) & 0xffffffff
    value = ((value ^ (value >> 15)) * 0x846ca68b) & 0xffffffff
    return (value ^ (value >> 16)) / 4294967295.0


def shade_strand_detail(hair: np.ndarray, colors: np.ndarray, index: int,
                        light_direction: np.ndarray, normal: np.ndarray,
                        contrast: float = 0.0,
                        highlight_strength: float = 0.0) -> np.ndarray:
    """Modify RGB only; keep one brightness factor per complete strand.

    Highlights select about 30% of strands, favour lit roots, and have one soft
    lobe along the shaft. A broad tangent/half-vector term supplies directionality
    under the renderer's approximate +Z view convention. Taper/alpha is handled
    by FineFurCanvas as before. Gain limiting preserves channel ratios at white.
    """
    if contrast == 0 and highlight_strength == 0:
        return colors
    gain = np.full(len(colors), 1.0 + contrast * (2 * _random01(index, 0x527a21) - 1),
                   dtype=np.float32)
    if highlight_strength > 0 and _random01(index, 0x7da013) < 0.30:
        light = np.asarray(light_direction, dtype=np.float32)
        light = light / max(float(np.linalg.norm(light)), 1e-8)
        surface_normal = np.asarray(normal, dtype=np.float32)
        surface_normal = surface_normal / max(float(np.linalg.norm(surface_normal)), 1e-8)
        facing = np.clip(float(np.dot(surface_normal, light)), 0.0, 1.0)
        half_vector = light + np.array([0, 0, 1], dtype=np.float32)
        half_vector /= max(float(np.linalg.norm(half_vector)), 1e-8)
        tangent = np.diff(hair, axis=0)
        tangent = tangent / np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-8)
        directional = np.clip(1 - (tangent @ half_vector) ** 2, 0, 1) ** 2
        position = (np.arange(len(colors), dtype=np.float32) + 0.5) / len(colors)
        centre = 0.35 + 0.30 * _random01(index, 0x31fe20)
        lobe = np.exp(-0.5 * ((position - centre) / 0.22) ** 2)
        # Fade out before the translucent tip to retain the accepted soft edge.
        tip_fade = np.clip((0.95 - position) / 0.25, 0, 1)
        tip_fade = tip_fade * tip_fade * (3 - 2 * tip_fade)
        gain += highlight_strength * facing * directional * lobe * tip_fade
    max_channel = np.max(colors, axis=1)
    gain = np.minimum(gain, 1.0 / np.maximum(max_channel, 1e-8))
    return np.clip(colors * gain[:, None], 0, 1).astype(np.float32)
