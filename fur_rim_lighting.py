"""Guided local lip illumination and inner-wall contact shadow.

A restrained 2.5D lighting approximation, not a physical shadow renderer.
Fields are sampled at strand roots so front fibres retain their own light as
these fibres overlap the darker wall. No colour blur, geometry or alpha edits.
"""
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class RimLightMaps:
    gain: np.ndarray
    highlight: np.ndarray
    shadow: np.ndarray
    diagnostics: dict


def _smooth(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


def rim_light_maps(depth, mask, opening, light_direction,
                   light_strength=0.0, shadow_strength=0.0):
    for value in (light_strength, shadow_strength):
        if not np.isfinite(value) or not 0 <= value <= 0.5:
            raise ValueError('Rim light/shadow strengths must be finite and in [0, 0.5].')
    depth = np.asarray(depth, np.float32)
    mask, opening = np.asarray(mask, bool), np.asarray(opening, bool)
    if depth.ndim != 2 or mask.shape != depth.shape or opening.shape != depth.shape:
        raise ValueError('Depth, object and opening masks must have matching 2D shapes.')
    if not np.isfinite(depth).all() or np.any(depth < 0) or np.any(depth > 1):
        raise ValueError('Depth must be finite and normalized to [0, 1].')
    if not opening.any() or opening.all() or not (opening & mask).any():
        raise ValueError('Opening guide must contain both regions and overlap the cup.')
    light = np.asarray(light_direction, np.float32)
    if light.shape != (3,) or not np.isfinite(light).all() or np.linalg.norm(light) < 1e-8:
        raise ValueError('Light direction must be a finite nonzero 3D vector.')
    light = light / np.linalg.norm(light)
    scale = min(depth.shape)/602.0
    outside = cv2.distanceTransform((~opening).astype(np.uint8), cv2.DIST_L2, 5)
    inside = cv2.distanceTransform(opening.astype(np.uint8), cv2.DIST_L2, 5)
    signed = cv2.GaussianBlur(outside-inside, (0, 0), max(1.1*scale, 0.5))
    gy, gx = np.gradient(signed)
    norm = np.maximum(np.hypot(gx, gy), 1e-6)
    gx, gy = gx/norm, gy/norm
    # Rounded lip cross-section, including its inner-facing and outer slopes.
    offset = (signed-3*scale)/max(7*scale, 1e-6)
    slope = -(5.0/7.0)*offset*np.exp(-0.5*offset**2)
    nx, ny, nz = -slope*gx, -slope*gy, np.ones_like(depth)
    normal_norm = np.sqrt(nx*nx+ny*ny+nz*nz)
    facing = np.clip((nx*light[0]+ny*light[1]+nz*light[2])/normal_norm, 0, 1)
    toward_light = np.clip((gx*light[0]+gy*light[1])/max(float(np.hypot(*light[:2])), 0.15), 0, 1)
    lip_band = np.exp(-0.5*((signed-3*scale)/max(5*scale, 1e-6))**2)
    lip_band *= _smooth((signed+2*scale)/max(3*scale, 1e-6))
    lip_band *= 1-_smooth((signed-12*scale)/max(5*scale, 1e-6))
    highlight = lip_band*facing**2*(0.65+0.35*toward_light)*mask

    # Verify that the nearby rim is in front of the receiving wall. The same
    # inverse-depth convention as the mesh is used; a flat sheet gets no shadow.
    yy, xx = np.mgrid[:depth.shape[0], :depth.shape[1]].astype(np.float32)
    travel = np.maximum(3*scale-signed, 0)
    mx, my = (xx+gx*travel).astype(np.float32), (yy+gy*travel).astype(np.float32)
    rim_depth = cv2.remap(depth, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    rim_mask = cv2.remap(mask.astype(np.uint8), mx, my, cv2.INTER_NEAREST,
                          borderMode=cv2.BORDER_CONSTANT) > 0
    height_gap = (rim_depth-depth)*min(depth.shape)
    occlusion = _smooth((height_gap-1.5*scale)/max(10*scale, 1e-6))*rim_mask
    # A narrow contact shadow favours the near/front arc. Side-directed light
    # also favours the inner wall immediately behind the illuminated side rim.
    front_arc = _smooth(gy/0.85)
    shadow_band = np.exp(-0.5*((inside-5*scale)/max(4.5*scale, 1e-6))**2)
    shadow_band *= _smooth(inside/max(3*scale, 1e-6))
    shadow_band *= 1-_smooth((inside-16*scale)/max(6*scale, 1e-6))
    shadow = shadow_band*occlusion*np.clip(0.85*front_arc+0.45*toward_light, 0, 1)
    shadow *= opening & mask
    gain = (1+light_strength*highlight)*(1-shadow_strength*shadow)
    return RimLightMaps(gain.astype(np.float32), highlight.astype(np.float32),
                        shadow.astype(np.float32), {
        'light_strength': float(light_strength), 'shadow_strength': float(shadow_strength),
        'light_direction': light.tolist(), 'minimum_gain': float(gain.min()),
        'maximum_gain': float(gain.max()),
        'highlight_support_pixels': int(np.count_nonzero(highlight)),
        'shadow_support_pixels': int(np.count_nonzero(shadow)),
        'method': 'guided rounded-lip illumination and depth-gated contact shadow at strand roots',
    })


def shade_rim_strand(colors, gain):
    """One scalar gain per strand preserves hue and the original shaft detail."""
    if gain == 1:
        return colors
    limited = np.minimum(gain, 1.0/np.maximum(np.max(colors, axis=1), 1e-8))
    return np.clip(colors*limited[:, None], 0, 1).astype(np.float32)
