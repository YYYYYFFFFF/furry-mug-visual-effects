"""Optional alpha repair and fine, tapered image-space fur rasterization.

Canvas RGB is premultiplied by coverage until filtering is complete. Conversion
to straight RGB happens only once, immediately before the existing compositor.
"""
from __future__ import annotations

import math

import cv2
import numpy as np


def straight_color(premultiplied: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    result = np.zeros_like(premultiplied, dtype=np.float32)
    np.divide(premultiplied, alpha[..., None], out=result, where=alpha[..., None] > 1e-6)
    return np.clip(result, 0.0, 1.0)


def repair_aa_color(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Filter colour and its coverage with identical weights before unpremultiplying."""
    filtered_rgb = 0.85 * rgb + 0.15 * cv2.GaussianBlur(rgb, (0, 0), 1.2)
    filtered_alpha = 0.85 * alpha + 0.15 * cv2.GaussianBlur(alpha, (0, 0), 1.2)
    return straight_color(filtered_rgb, filtered_alpha)


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def _linear(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def _srgb(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1.0 / 2.4) - 0.055)


def depth_ordered_strands(strands):
    """Approximate far-to-near painter order using this pipeline's relative depth.

    Each record keeps (geometry, shaded colours, original index) together so
    changing draw order cannot reassign colours or deterministic width variation.
    Larger root-depth values are treated as nearer. This is a root-based ordering,
    not per-fragment depth testing of intersecting curved fibres.
    """
    return sorted(strands, key=lambda record: (float(record[0][0, 2]), record[2]))


class FineFurCanvas:
    """Draw subpixel ribbons with source-over alpha and optional background tint.

    Geometry, root density, lighting and the main renderer's RNG are untouched.
    Width/opacity variation is deterministic from each strand index.
    """

    def __init__(self, image: np.ndarray, object_mask: np.ndarray,
                 width_scale: float = 0.5, supersample: int = 4,
                 environment_blend: float = 0.0) -> None:
        self.height, self.width = object_mask.shape
        self.scale = supersample
        self.width_scale = width_scale
        self.environment_blend = environment_blend
        shape = (self.height * supersample, self.width * supersample)
        self.rgb = np.zeros((*shape, 3), dtype=np.float32)
        self.alpha = np.zeros(shape, dtype=np.float32)
        self.object_mask = object_mask.astype(bool)
        self.object_hi = cv2.resize(object_mask.astype(np.uint8),
                                   (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
        background = (~self.object_mask).astype(np.float32)
        self.safe_background = cv2.erode(background, np.ones((5, 5), np.uint8)) > 0.99
        weights = cv2.GaussianBlur(background, (0, 0), 2.0)
        weighted_color = cv2.GaussianBlur(image * background[..., None], (0, 0), 2.0)
        self.background_color = weighted_color / np.maximum(weights[..., None], 1e-6)
        self.tinted_segments = 0

    def _environment(self, hair: np.ndarray):
        if self.environment_blend == 0:
            return None
        tip = hair[-1, :2]
        x, y = int(round(float(tip[0]))), int(round(float(tip[1])))
        if not (0 <= x < self.width and 0 <= y < self.height) or self.object_mask[y, x]:
            return None
        direction = tip - hair[0, :2]
        norm = float(np.linalg.norm(direction))
        if norm < 1e-6:
            return None
        direction = direction / norm
        for distance in (2.0, 4.0, 8.0, 12.0):
            position = tip + distance * direction
            x, y = int(round(float(position[0]))), int(round(float(position[1])))
            if 0 <= x < self.width and 0 <= y < self.height and self.safe_background[y, x]:
                return self.background_color[y, x]
        return None

    def draw_strand(self, hair: np.ndarray, colors: np.ndarray, index: int) -> None:
        points = hair[:, :2] * self.scale
        count = len(points) - 1
        variation = ((index * 2654435761) & 0xffff) / 65535.0
        root_width = 1.8 * self.width_scale * (0.85 + 0.30 * variation) * self.scale
        root_opacity = 0.90 + 0.08 * variation
        environment = self._environment(hair)
        for segment in range(count):
            p0, p1 = points[segment], points[segment + 1]
            delta = p1 - p0
            length = float(np.linalg.norm(delta))
            if length < 1e-5:
                continue
            normal = np.array([-delta[1], delta[0]], dtype=np.float32) / length
            t0, t1 = segment / count, (segment + 1) / count
            radius0 = 0.5 * root_width * (0.06 + 0.94 * (1.0 - t0) ** 0.65)
            radius1 = 0.5 * root_width * (0.06 + 0.94 * (1.0 - t1) ** 0.65)
            corners = np.array([p0 + radius0 * normal, p1 + radius1 * normal,
                                p1 - radius1 * normal, p0 - radius0 * normal])
            x0 = max(0, int(math.floor(float(corners[:, 0].min()))) - 1)
            y0 = max(0, int(math.floor(float(corners[:, 1].min()))) - 1)
            x1 = min(self.width * self.scale, int(math.ceil(float(corners[:, 0].max()))) + 2)
            y1 = min(self.height * self.scale, int(math.ceil(float(corners[:, 1].max()))) + 2)
            if x1 <= x0 or y1 <= y0:
                continue
            coverage = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
            polygon = np.rint((corners - [x0, y0]) * 256).astype(np.int32)
            cv2.fillConvexPoly(coverage, polygon, 255, lineType=cv2.LINE_AA, shift=8)
            t = (t0 + t1) * 0.5
            opacity = root_opacity * (1.0 - 0.9 * _smoothstep((t - 0.45) / 0.55))
            a = coverage.astype(np.float32) * (opacity / 255.0)
            color = colors[segment]
            if environment is not None and t > 0.65:
                weight = self.environment_blend * _smoothstep((t - 0.65) / 0.35)
                tinted = _srgb((1.0 - weight) * _linear(color) + weight * _linear(environment))
                outside = self.object_hi[y0:y1, x0:x1] == 0
                color = np.where(outside[..., None], tinted, color)
                self.tinted_segments += int(np.any(outside & (a > 0)))
            rgb = self.rgb[y0:y1, x0:x1]
            alpha = self.alpha[y0:y1, x0:x1]
            rgb *= (1.0 - a[..., None])
            rgb += color * a[..., None]
            alpha *= (1.0 - a)
            alpha += a

    def finish(self):
        size = (self.width, self.height)
        premultiplied = cv2.resize(self.rgb, size, interpolation=cv2.INTER_AREA)
        alpha = cv2.resize(self.alpha, size, interpolation=cv2.INTER_AREA)
        return straight_color(premultiplied, alpha), np.clip(alpha, 0.0, 1.0)

    def add_underfur(self, image: np.ndarray, normal_image: np.ndarray) -> int:
        """Place short fibres behind sparse coverage, clipped to the object.

        The primary strands, their exterior tips and already-covered pixels are
        preserved. A separate RNG keeps this optional pass reproducible.
        """
        color, coverage = self.finish()
        sparse = self.object_mask & (coverage < 0.8)
        ys, xs = np.where(sparse)
        if not len(xs):
            return 0
        weight = coverage * self.object_mask
        color_sum = cv2.GaussianBlur(color * weight[..., None], (0, 0), 2.0)
        local_weight = cv2.GaussianBlur(weight, (0, 0), 2.0)
        fallback = np.clip(image * 0.75, 0, 1)
        local_color = np.divide(color_sum, local_weight[..., None], out=fallback.copy(),
                                where=local_weight[..., None] > 1e-5)
        underfur = FineFurCanvas(image, self.object_mask, self.width_scale, self.scale, 0.0)
        rng = np.random.default_rng(20261024)
        for index, (x, y) in enumerate(zip(xs, ys)):
            normal = normal_image[y, x, :2] * 2.0 - 1.0
            angle = np.arctan2(normal[1], normal[0]) + rng.uniform(-1.1, 1.1)
            direction = np.array([np.cos(angle), np.sin(angle)], dtype=np.float32)
            length = rng.uniform(2.0, 4.0)
            start = np.array([x, y], dtype=np.float32) + rng.uniform(-0.4, 0.4, 2)
            hair = np.zeros((5, 3), dtype=np.float32)
            hair[:, :2] = start + np.linspace(0, length, 5)[:, None] * direction
            brightness = rng.uniform(0.85, 1.15)
            strand_color = np.clip(local_color[y, x] * brightness, 0, 1)
            colors = np.tile(strand_color, (4, 1))
            underfur.draw_strand(hair, colors, index)
        # Restrict the backing fibres to under-covered object pixels. The main
        # silhouette, handle opening and environment-tinted tips stay untouched.
        support = cv2.resize(sparse.astype(np.uint8),
                             (self.width * self.scale, self.height * self.scale),
                             interpolation=cv2.INTER_NEAREST)
        underfur.rgb *= support[..., None]
        underfur.alpha *= support
        remaining = 1.0 - self.alpha
        self.rgb += remaining[..., None] * underfur.rgb
        self.alpha += remaining * underfur.alpha
        return len(xs)
