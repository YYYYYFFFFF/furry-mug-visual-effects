"""Guided, image-space padding before surface normals and strand generation.

This is a controlled 2.5D deformation for one upright mug photograph, not a
physical soft-body simulation or recovery of an unseen 3D shape.
"""
from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np


@dataclass
class SoftFormResult:
    rgb: np.ndarray
    depth: np.ndarray
    mask: np.ndarray
    opening: np.ndarray
    map_x: np.ndarray
    map_y: np.ndarray
    padding: np.ndarray
    diagnostics: dict


def _smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def _sdf(mask):
    mask = np.asarray(mask, dtype=np.uint8)
    return (cv2.distanceTransform(mask, cv2.DIST_L2, 5)
            - cv2.distanceTransform(1-mask, cv2.DIST_L2, 5))


def _direction(signed, sigma):
    field = cv2.GaussianBlur(signed, (0, 0), sigma)
    dy, dx = np.gradient(field)
    norm = np.maximum(np.hypot(dx, dy), 0.35)
    return dx / norm, dy / norm


def _remap(array, mx, my, interpolation=cv2.INTER_LINEAR):
    return cv2.remap(array, mx, my, interpolation, borderMode=cv2.BORDER_REPLICATE)


def deform_soft_form(rgb, depth, mask, opening, amount=8.0):
    """Inflate the silhouette, contract the opening slightly and round depth.

    amount is an image-space displacement scale at 602px input size. One shared
    inverse map transports foreground colour, alpha, depth and the opening
    guide. Mask-normalized sampling avoids pulling background into new cup
    pixels. Foreground geometry is then padded locally in relative depth.
    """
    if not np.isfinite(amount) or not 0 <= amount <= 12:
        raise ValueError('Soft-form amount must be finite and in [0, 12].')
    mask, opening = np.asarray(mask, bool), np.asarray(opening, bool)
    h, w = mask.shape
    if rgb.shape != (h, w, 3) or rgb.dtype != np.uint8 or depth.shape != (h, w):
        raise ValueError('Soft form expects same-size RGB uint8, float depth and masks.')
    if not mask.any() or mask.all() or opening.shape != mask.shape or not opening.any() or opening.all():
        raise ValueError('Object matte and explicit opening guide must contain both regions.')
    if not np.isfinite(depth).all():
        raise ValueError('Soft form requires finite depth.')
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    if amount == 0:
        return SoftFormResult(rgb.copy(), depth.copy(), mask.copy(), opening.copy(),
                              xx, yy, np.zeros_like(depth), {'amount': 0.0, 'identity': True})
    scale = min(h, w) / 602.0
    pixels = amount * scale
    ys, xs = np.where(mask)
    gy, gx = np.where(opening)
    bottom = float(ys.max())
    middle = (float(gy.min()) + float(gy.max())) * 0.5
    # The last 5px of the supporting foot stays fixed; ramp over the next 40px.
    anchor = _smooth((bottom - yy - 5*scale) / (40*scale))
    body = _smooth((xx - gx.min() + 64*scale) / (64*scale))
    body *= _smooth((gx.max() + 64*scale - xx) / (64*scale))
    vertical = np.clip((yy - middle) / max(bottom-middle, 1), 0, 1)
    fullness = 0.55 + 0.45 * np.sin(np.pi * vertical)
    wobble = 1 + 0.08 * np.sin(2*np.pi*yy/h + 0.6) * np.cos(np.pi*xx/w)
    signed = _sdf(mask)
    ix, iy = _direction(signed, max(2.4*scale, 0.6))
    near_edge = np.exp(-0.5 * (signed / (27*scale))**2)
    displacement = pixels * (0.55 + 0.45*body) * fullness * wobble * anchor * near_edge
    # Enclosed handle holes get a lower cap based on their actual diameter.
    count, labels, stats, _ = cv2.connectedComponentsWithStats((~mask).astype(np.uint8), connectivity=8)
    for label in range(1, count):
        x, y, bw, bh, area = stats[label]
        if x == 0 or y == 0 or x+bw == w or y+bh == h:
            continue
        hole = labels == label
        distance = cv2.distanceTransform((~hole).astype(np.uint8), cv2.DIST_L2, 5)
        limit = min(0.55*pixels, 0.07*min(bw, bh))
        blend = np.exp(-0.5*(distance/(8*scale))**2)
        displacement = np.minimum(displacement, displacement*(1-blend) + limit*blend)
    vx, vy = -ix * displacement, -iy * displacement
    # Pull the opening boundary slightly inward, adding visible lip thickness.
    opening_distance = _sdf(opening)
    ox, oy = _direction(opening_distance, max(2.5*scale, 0.6))
    rim = np.exp(-0.5*(opening_distance/(17*scale))**2) * mask * anchor
    inset = 0.36 * pixels * rim
    vx += ox * inset
    vy += oy * inset
    # Smooth narrow seams in the guide/medial-axis field before inversion.
    vx = cv2.GaussianBlur(vx, (0, 0), max(4*scale, 0.8)) * anchor
    vy = cv2.GaussianBlur(vy, (0, 0), max(4*scale, 0.8)) * anchor
    # Use a smooth inverse map; reject a folded mapping instead of hiding it.
    mx, my = xx.copy(), yy.copy()
    for _ in range(48):
        target_x, target_y = xx - _remap(vx, mx, my), yy - _remap(vy, mx, my)
        nx, ny = 0.5*mx + 0.5*target_x, 0.5*my + 0.5*target_y
        error = float(max(np.max(np.abs(nx-mx)), np.max(np.abs(ny-my))))
        mx, my = nx.astype(np.float32), ny.astype(np.float32)
        if error < 0.005:
            break
    error = float(max(np.max(np.abs(mx + _remap(vx, mx, my) - xx)),
                      np.max(np.abs(my + _remap(vy, mx, my) - yy))))
    mx_y, mx_x = np.gradient(mx)
    my_y, my_x = np.gradient(my)
    jacobian = mx_x*my_y - mx_y*my_x
    active = (np.hypot(mx-xx, my-yy) > 0.02)
    if error > 0.1 or np.any(jacobian[active] <= 0.1):
        raise ValueError(f'Soft-form map invalid: residual={error:.4f}, min determinant={jacobian.min():.4f}; reduce amount.')
    weight = _remap(mask.astype(np.float32), mx, my)
    new_mask = weight >= 0.5
    new_opening = _remap(opening.astype(np.uint8), mx, my, cv2.INTER_NEAREST) > 0
    if np.count_nonzero(new_opening) < 0.75*np.count_nonzero(opening):
        raise ValueError('Soft form would collapse too much of the opening.')
    # Pull foreground samples only. Newly covered pixels never sample background
    # depth or colour, even when bilinear interpolation straddles the old matte.
    colour_sum = _remap(rgb.astype(np.float32) * mask[..., None], mx, my)
    colour = colour_sum / np.maximum(weight[..., None], 1e-6)
    depth_sum = _remap(depth.astype(np.float32)*mask, mx, my)
    warped_depth = depth_sum / np.maximum(weight, 1e-6)
    # Remove the old object only where shape contraction exposes it. The rest
    # of the background is copied byte-for-byte; hidden inpaint values are unused.
    vacated = mask & ~new_mask
    result_rgb = rgb.copy()
    if vacated.any():
        background = cv2.inpaint(rgb, mask.astype(np.uint8)*255, 3, cv2.INPAINT_TELEA)
        result_rgb[vacated] = background[vacated]
    result_rgb[new_mask] = np.rint(np.clip(colour[new_mask], 0, 255)).astype(np.uint8)
    # Round the depth transition around the lip while preserving the deep core.
    # Foreground-normalized filtering cannot blend in background depth values.
    new_signed = _sdf(new_mask)
    new_rim_distance = _sdf(new_opening)
    rim_weight = np.exp(-0.5*(new_rim_distance/(14*scale))**2) * new_mask
    blur_weight = cv2.GaussianBlur(new_mask.astype(np.float32), (0, 0), 6*scale)
    blur_depth = cv2.GaussianBlur(warped_depth*new_mask, (0, 0), 6*scale)
    smooth_depth = blur_depth / np.maximum(blur_weight, 1e-6)
    rim_mix = 0.65 * min(amount/8, 1) * rim_weight * anchor
    surface_depth = warped_depth*(1-rim_mix) + smooth_depth*rim_mix
    # A rounded padding cross-section raises the front surface (larger depth in
    # this renderer), with an additional convex lip ridge and an untouched core.
    interior_core = _smooth((new_rim_distance - 4*scale)/(16*scale))
    body_padding = (1-np.exp(-np.maximum(new_signed, 0)/(20*scale))) * (1-interior_core)
    lip_padding = 0.65*np.exp(-0.5*(new_rim_distance/(10*scale))**2)
    padding = (pixels/min(h,w)) * (0.7*body_padding + lip_padding) * anchor * new_mask
    result_depth = depth.copy()
    result_depth[new_mask] = np.clip(surface_depth[new_mask] + padding[new_mask], 0, 1)
    diagnostics = {'amount':float(amount), 'max_displacement_px':float(np.hypot(mx-xx,my-yy).max()),
        'min_inverse_jacobian':float(jacobian[active].min()) if active.any() else 1.0, 'inverse_residual_px':error,
        'old_mask_pixels':int(mask.sum()), 'new_mask_pixels':int(new_mask.sum()),
        'added_pixels':int((new_mask & ~mask).sum()), 'vacated_pixels':int(vacated.sum()),
        'opening_area_ratio':float(new_opening.sum()/opening.sum()),
        'max_depth_padding':float(padding.max()), 'bottom_anchor_from_row':int(np.ceil(bottom-5*scale))}
    return SoftFormResult(result_rgb, result_depth.astype(np.float32), new_mask,
                          new_opening, mx, my, padding, diagnostics)
