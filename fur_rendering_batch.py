from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLBACKEND", "Agg")

from importlib.util import find_spec

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps
from segment_anything import SamPredictor, sam_model_registry
from transformers import pipeline

from fur_strokes import FineFurCanvas, depth_ordered_strands, repair_aa_color
from matte_refinement import close_matte_gaps
from fur_rim import apply_rear_rim_fringe, apply_rim_detail
from fur_lighting import shade_strand_detail
from soft_form import deform_soft_form
from fur_cavity import refine_cavity

REQUIRED_PACKAGES = {
    "cv2": "opencv-python",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "torch": "torch",
    "PIL": "Pillow",
    "transformers": "transformers",
    "segment_anything": "segment-anything",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
DEFAULT_SAM_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
DEFAULT_SAM_FILENAME = "sam_vit_b_01ec64.pth"


@dataclass
class ImageRunResult:
    image_name: str
    status: str
    output_dir: str
    elapsed_seconds: float
    error: str | None = None


def ensure_environment() -> None:
    missing_packages = [
        package_name
        for module_name, package_name in REQUIRED_PACKAGES.items()
        if find_spec(module_name) is None
    ]
    if missing_packages:
        missing_text = ", ".join(sorted(set(missing_packages)))
        raise ModuleNotFoundError(
            "Missing required packages: "
            f"{missing_text}. Install them with `pip install -r requirements.txt` in this folder, "
            "then rerun the script."
        )


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def sanitize_name(file_stem: str) -> str:
    cleaned = []
    for char in file_stem:
        if char.isalnum() or char in {"-", "_"}:
            cleaned.append(char)
        else:
            cleaned.append("_")
    safe_name = "".join(cleaned).strip("_")
    return safe_name or "image"


def iter_images(image_dir: Path) -> Iterable[Path]:
    for path in sorted(image_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("._") or path.name.startswith("."):
            continue
        if "__MACOSX" in path.parts:
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        yield path


def save_figure(figure: plt.Figure, output_path: Path, dpi: int = 150) -> None:
    figure.tight_layout()
    figure.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)


def save_rgb_image(output_path: Path, image_rgb: np.ndarray) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))


def stage_elapsed_message(stage_started: float) -> str:
    return f"done in {time.time() - stage_started:.1f}s"


def make_run_timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def make_output_prefix(index: int) -> str:
    return f"image_{index}"


class FurRenderingBatchRunner:
    def __init__(
        self,
        project_root: Path,
        image_dir: Path,
        output_root: Path,
        depth_source: str,
        mask_box: list[int] | None,
        stroke_rasterizer: str,
        stroke_width_scale: float,
        fur_density: float,
        underlayer_mode: str,
        exclude_mask_path: Path | None,
        inner_wall_mask_path: Path | None,
        inner_wall_length_scale: float,
        inner_wall_opacity: float,
        fur_finish: str,
        supersample: int,
        tip_environment_blend: float,
        matte_close_radius: int,
        fill_fur_gaps: bool,
        fur_alpha_cap: float,
        fur_order: str,
        rim_guide_mask_path: Path | None,
        rim_detail_strength: float,
        rear_rim_strength: float,
        strand_contrast: float,
        strand_highlight: float,
        soft_form_amount: float = 0.0,
        cavity_depth: float = 0.0,
        cavity_length_scale: float = 1.0,
    ) -> None:
        self.project_root = project_root
        self.image_dir = image_dir
        self.output_root = output_root
        self.depth_source = depth_source
        self.mask_box = mask_box
        self.stroke_rasterizer = stroke_rasterizer
        self.stroke_width_scale = stroke_width_scale
        self.fur_density = fur_density
        self.underlayer_mode = underlayer_mode
        self.exclude_mask_path = exclude_mask_path
        self.inner_wall_mask_path = inner_wall_mask_path
        self.inner_wall_length_scale = inner_wall_length_scale
        self.inner_wall_opacity = inner_wall_opacity
        self.fur_finish = fur_finish
        self.supersample = supersample
        self.tip_environment_blend = tip_environment_blend
        self.matte_close_radius = matte_close_radius
        self.fill_fur_gaps = fill_fur_gaps
        self.fur_alpha_cap = fur_alpha_cap
        self.fur_order = fur_order
        self.rim_guide_mask_path = rim_guide_mask_path
        self.rim_detail_strength = rim_detail_strength
        self.rear_rim_strength = rear_rim_strength
        self.strand_contrast = strand_contrast
        self.strand_highlight = strand_highlight
        self.soft_form_amount = soft_form_amount
        self.cavity_depth = cavity_depth
        self.cavity_length_scale = cavity_length_scale
        self.cavity_active = cavity_depth > 0 or cavity_length_scale < 1
        if not np.isfinite(cavity_depth) or not 0 <= cavity_depth <= 0.12:
            raise ValueError("Cavity depth must be finite and in [0, 0.12].")
        if not np.isfinite(cavity_length_scale) or not 0.2 <= cavity_length_scale <= 1:
            raise ValueError("Cavity length scale must be finite and in [0.2, 1].")
        if self.cavity_active and (rim_guide_mask_path is None or fur_finish != "fine"
                                   or exclude_mask_path is not None or inner_wall_mask_path is not None):
            raise ValueError("Cavity refinement requires fine fur, an opening guide and no older region-style masks.")
        if not np.isfinite(soft_form_amount) or not 0 <= soft_form_amount <= 12:
            raise ValueError("Soft-form amount must be finite and in [0, 12].")
        if soft_form_amount > 0 and (rim_guide_mask_path is None or fur_finish != "fine"
                                    or exclude_mask_path is not None or inner_wall_mask_path is not None):
            raise ValueError("Soft form requires fine fur, an opening guide and no older region-style masks.")
        self.model_cache_dir = project_root / "model_cache"
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)
        self.depth_pipe = None
        self.predictor = None

    def load_models(self) -> None:
        if self.depth_pipe is None:
            device = 0 if torch.cuda.is_available() else -1
            log(f"Loading depth model on {'GPU' if device == 0 else 'CPU'}...")
            self.depth_pipe = pipeline(
                task="depth-estimation",
                model=DEFAULT_DEPTH_MODEL,
                device=device,
            )
            log("Depth estimation model loaded.")

        if self.predictor is None:
            checkpoint_path = self.model_cache_dir / DEFAULT_SAM_FILENAME
            if not checkpoint_path.exists():
                log("Downloading Segment Anything checkpoint...")
                urllib.request.urlretrieve(DEFAULT_SAM_URL, checkpoint_path)
            model_type = "vit_b"
            sam = sam_model_registry[model_type](checkpoint=str(checkpoint_path))
            sam.to(device="cuda" if torch.cuda.is_available() else "cpu")
            self.predictor = SamPredictor(sam)
            log(f"SAM checkpoint ready: {checkpoint_path}")

    def process_image(self, image_path: Path, index: int, total: int) -> ImageRunResult:
        started = time.time()
        output_prefix = make_output_prefix(index)
        final_output_path = self.output_root / f"{output_prefix}_final_project_furry_mug.png"
        pipeline_output_path = self.output_root / f"{output_prefix}_full_pipeline.png"

        log(f"[{index}/{total}] Starting {image_path.name}")
        try:
            image = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
            image_np = np.array(image)
            source_image_np = image_np
            height, width = image_np.shape[:2]
            log(f"[{index}/{total}] Loaded image with size {width} x {height}")

            rim_guide = None
            if self.rim_guide_mask_path is not None:
                with Image.open(self.rim_guide_mask_path) as guide_image:
                    rim_guide = np.asarray(guide_image.convert("L")) > 127
                if rim_guide.shape != (height, width) or not rim_guide.any() or rim_guide.all():
                    raise ValueError("Rim opening guide must match the image and contain both regions.")

            # Stage 1: depth map
            log(f"[{index}/{total}] Stage 1/7: estimating depth map")
            stage_started = time.time()
            result = self.depth_pipe(image)
            if self.depth_source == "float":
                depth_output = result["predicted_depth"]
                if torch.is_tensor(depth_output):
                    depth_output = depth_output.detach().cpu().numpy()
            else:
                depth_output = result["depth"]
            depth = np.squeeze(np.asarray(depth_output, dtype=np.float32))
            if depth.ndim != 2 or not np.isfinite(depth).all():
                raise ValueError("Depth model returned an invalid 2D depth map.")
            depth = cv2.resize(depth, image.size)
            depth_norm = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
            depth_gray = (depth_norm * 255).astype(np.uint8)
            depth_color = cv2.applyColorMap(depth_gray, cv2.COLORMAP_INFERNO)
            depth_color = cv2.cvtColor(depth_color, cv2.COLOR_BGR2RGB)
            log(f"[{index}/{total}] Stage 1/7 complete: {stage_elapsed_message(stage_started)}")

            # Stage 2: matte generation
            log(f"[{index}/{total}] Stage 2/7: generating mug matte")
            stage_started = time.time()
            self.predictor.set_image(image_np)
            center_x = width // 2
            center_y = height // 2
            if self.mask_box is None:
                input_point = np.array([[center_x, center_y]])
                input_label = np.array([1])
                masks, scores, _ = self.predictor.predict(
                    point_coords=input_point,
                    point_labels=input_label,
                    multimask_output=True,
                )
            else:
                x0, y0, x1, y1 = self.mask_box
                if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                    raise ValueError("Mask box must fit inside the image: x0 y0 x1 y1.")
                masks, scores, _ = self.predictor.predict(
                    box=np.array(self.mask_box),
                    multimask_output=True,
                )
            best_mask = masks[np.argmax(scores)]
            if self.mask_box is None and not bool(best_mask[center_y, center_x]):
                raise ValueError("Image center is not inside the mug matte.")
            if self.matte_close_radius:
                raw_mask = best_mask.copy()
                best_mask = close_matte_gaps(best_mask, self.matte_close_radius)
                added = best_mask & ~raw_mask
                Image.fromarray(raw_mask.astype(np.uint8) * 255).save(
                    self.output_root / f"{output_prefix}_matte_raw.png")
                Image.fromarray(added.astype(np.uint8) * 255).save(
                    self.output_root / f"{output_prefix}_matte_added.png")
                log(f"[{index}/{total}] Matte repair: added {int(added.sum())} pixels "
                    f"with radius {self.matte_close_radius}")
            inner_wall_region = np.zeros((height, width), dtype=bool)
            if self.inner_wall_mask_path is not None:
                with Image.open(self.inner_wall_mask_path) as inner_wall_image:
                    inner_wall = np.asarray(inner_wall_image.convert("L"))
                if inner_wall.shape != (height, width):
                    raise ValueError("Inner-wall mask must match the selected image dimensions.")
                inner_wall_region = (inner_wall > 127) & best_mask
                if not np.any(inner_wall_region):
                    raise ValueError("Inner-wall mask does not overlap the detected mug.")
            inner_wall_weight = cv2.GaussianBlur(inner_wall_region.astype(np.float32), (0, 0), 3.0)
            inner_wall_weight *= best_mask.astype(np.float32)
            excluded_region = np.zeros((height, width), dtype=bool)
            if self.exclude_mask_path is not None:
                with Image.open(self.exclude_mask_path) as exclusion_image:
                    exclusion = np.asarray(exclusion_image.convert("L"))
                if exclusion.shape != (height, width):
                    raise ValueError("Exclude mask must match the selected image dimensions.")
                excluded_region = exclusion > 127
                best_mask = best_mask & ~excluded_region
            mug_matte = best_mask.astype(np.uint8)
            mask_area = np.sum(best_mask)
            image_area = height * width
            mask_ratio = mask_area / image_area
            if mask_ratio < 0.03:
                raise ValueError("Detected mug matte is too small. Please use a clearer centered mug image.")
            if mask_ratio > 0.85:
                raise ValueError("Detected mug matte is too large and likely includes background.")
            top_touch = np.any(best_mask[0:5, :])
            bottom_touch = np.any(best_mask[-5:, :])
            left_touch = np.any(best_mask[:, 0:5])
            right_touch = np.any(best_mask[:, -5:])
            border_touch_count = sum([top_touch, bottom_touch, left_touch, right_touch])
            if border_touch_count >= 2:
                raise ValueError("Mug matte touches too many borders.")
            mug_matte_255 = mug_matte * 255
            matte_overlay = image_np.copy()
            matte_overlay[mug_matte == 1] = (
                matte_overlay[mug_matte == 1] * 0.5 + np.array([255, 0, 0]) * 0.5
            )
            matte_overlay = matte_overlay.astype(np.uint8)
            log(
                f"[{index}/{total}] Stage 2/7 complete: {stage_elapsed_message(stage_started)}; "
                f"mask ratio {mask_ratio:.3f}, border touches {border_touch_count}"
            )

            if self.soft_form_amount > 0:
                log(f"[{index}/{total}] Soft form: deforming silhouette and depth before normals")
                original_mask, original_depth = mug_matte.copy(), depth_norm.copy()
                original_guide = rim_guide.copy()
                form = deform_soft_form(image_np, depth_norm, mug_matte, rim_guide,
                                        self.soft_form_amount)
                image_np, depth_norm = form.rgb, form.depth
                mug_matte, best_mask = form.mask.astype(np.uint8), form.mask
                rim_guide = form.opening
                mug_matte_255 = mug_matte * 255
                matte_overlay = image_np.copy()
                matte_overlay[best_mask] = (image_np[best_mask]*0.5 + np.array([255, 0, 0])*0.5).astype(np.uint8)
                Image.fromarray(image_np).save(self.output_root / f"{output_prefix}_soft_form_source.png")
                Image.fromarray(original_mask*255).save(self.output_root / f"{output_prefix}_before_soft_form_matte.png")
                Image.fromarray(rim_guide.astype(np.uint8)*255).save(self.output_root / f"{output_prefix}_soft_form_opening.png")
                contours = image_np.copy()
                for shape, colour in ((original_mask, (255, 90, 40)), (mug_matte, (30, 220, 240))):
                    lines, _ = cv2.findContours(shape, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(contours, lines, -1, colour, 1)
                Image.fromarray(contours).save(self.output_root / f"{output_prefix}_soft_form_contours.png")
                np.savez_compressed(self.output_root / f"{output_prefix}_soft_form_geometry.npz",
                                    original_depth=original_depth, deformed_depth=depth_norm,
                                    original_mask=original_mask, deformed_mask=mug_matte,
                                    original_opening=original_guide, deformed_opening=rim_guide,
                                    map_x=form.map_x, map_y=form.map_y, padding=form.padding)
                (self.output_root / f"{output_prefix}_soft_form.json").write_text(
                    json.dumps(form.diagnostics, indent=2), encoding="utf-8")
                log(f"[{index}/{total}] Soft form: {form.diagnostics['added_pixels']} added silhouette pixels; "
                    f"max displacement {form.diagnostics['max_displacement_px']:.2f}px")

            # Apply interior relief after the guide has travelled with soft form.
            sampling_depth = depth_norm
            cavity = None
            if self.cavity_active:
                cavity = refine_cavity(depth_norm, mug_matte, rim_guide,
                                       self.cavity_depth, self.cavity_length_scale)
                depth_norm = cavity.depth
                np.savez_compressed(self.output_root / f"{output_prefix}_cavity_geometry.npz",
                                    before_depth=sampling_depth, after_depth=depth_norm,
                                    opening=rim_guide, weight=cavity.weight,
                                    recession=cavity.recession, length_scale=cavity.length_scale)
                Image.fromarray((cavity.weight*255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_cavity_support.png")
                (self.output_root / f"{output_prefix}_cavity.json").write_text(
                    json.dumps(cavity.diagnostics, indent=2), encoding="utf-8")
                log(f"[{index}/{total}] Cavity: max recession {cavity.recession.max():.4f}; "
                    f"inner pile scale {cavity.length_scale.min():.2f}")

            # Stage 3: normals
            log(f"[{index}/{total}] Stage 3/7: estimating surface normals")
            stage_started = time.time()
            vertices = []
            vertex_map = np.full((height, width), -1, dtype=int)
            for row in range(height):
                for col in range(width):
                    if mug_matte[row, col] > 0:
                        vertex_map[row, col] = len(vertices)
                        z_value = depth_norm[row, col] * min(height, width) * 1.0
                        vertices.append([col, row, z_value])
            vertices = np.array(vertices)
            sampling_vertices = vertices
            if cavity is not None:
                sampling_vertices = vertices.copy()
                sampling_vertices[:, 2] = sampling_depth[mug_matte > 0].astype(np.float64) * min(height, width) * 1.0
            triangles = []
            for row in range(height - 1):
                for col in range(width - 1):
                    quad = [
                        vertex_map[row, col],
                        vertex_map[row, col + 1],
                        vertex_map[row + 1, col],
                        vertex_map[row + 1, col + 1],
                    ]
                    if all(index_value >= 0 for index_value in quad):
                        triangles.append([quad[0], quad[1], quad[2]])
                        triangles.append([quad[1], quad[3], quad[2]])
            triangles = np.array(triangles)
            vertex_normals = np.zeros((len(vertices), 3))
            for triangle in triangles:
                v0, v1, v2 = vertices[triangle]
                face_normal = np.cross(v1 - v0, v2 - v0)
                vertex_normals[triangle[0]] += face_normal
                vertex_normals[triangle[1]] += face_normal
                vertex_normals[triangle[2]] += face_normal
            norms = np.linalg.norm(vertex_normals, axis=1, keepdims=True)
            vertex_normals = vertex_normals / (norms + 1e-8)
            normal_image = np.zeros((height, width, 3), dtype=np.float32)
            for row in range(height):
                for col in range(width):
                    vertex_index = vertex_map[row, col]
                    if vertex_index >= 0:
                        normal_image[row, col] = (vertex_normals[vertex_index] + 1.0) * 0.5
            normal_image[~mug_matte.astype(bool)] = 0
            normal_vis = (normal_image * 255).astype(np.uint8)
            log(
                f"[{index}/{total}] Stage 3/7 complete: {stage_elapsed_message(stage_started)}; "
                f"vertices {len(vertices)}, triangles {len(triangles)}"
            )

            # Stage 4: fur generation
            log(f"[{index}/{total}] Stage 4/7: generating fur strands")
            stage_started = time.time()
            image_float = image_np.astype(np.float32) / 255.0
            mask = mug_matte.astype(np.uint8)
            depth_scale = max(float(sampling_vertices[:, 2].max()), 1.0)
            fur_density = self.fur_density
            fur_length_min = 6.0
            fur_length_max = 15.0
            gravity_dir = np.array([0.0, 1.0, 0.0], dtype=np.float32)
            gravity_strength = 0.18
            direction_randomness = 0.25
            n_steps = 12
            dt = 1.0 / n_steps
            rng = np.random.default_rng(42)
            root_positions = []
            root_normals = []
            root_lengths = []
            z_min = sampling_vertices[:, 2].min()
            z_max = sampling_vertices[:, 2].max()
            z_range = z_max - z_min + 1e-6
            center = sampling_vertices.mean(axis=0)
            for triangle in triangles:
                v0, v1, v2 = sampling_vertices[triangle].astype(np.float32)
                area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0))
                z_values = [v0[2], v1[2], v2[2]]
                z_range_tri = max(z_values) - min(z_values)
                edge_boost = 1.0 + min(z_range_tri / (depth_scale + 1e-6) * 3.0, 2.5)
                expected_hairs = fur_density * area * edge_boost
                n_roots = int(expected_hairs)
                if rng.random() < (expected_hairs - n_roots):
                    n_roots += 1
                if n_roots == 0:
                    continue
                n0, n1, n2 = vertex_normals[triangle[0]], vertex_normals[triangle[1]], vertex_normals[triangle[2]]
                for _ in range(n_roots):
                    u = rng.random()
                    v = rng.random()
                    if u + v > 1.0:
                        u = 1.0 - u
                        v = 1.0 - v
                    w = 1.0 - u - v
                    root = w * v0 + u * v1 + v * v2
                    reference_root_z = root[2]
                    if cavity is not None:
                        q0, q1, q2 = vertices[triangle].astype(np.float32)
                        root = w * q0 + u * q1 + v * q2
                    root_normal = w * n0 + u * n1 + v * n2
                    root_normal = root_normal / (np.linalg.norm(root_normal) + 1e-8)
                    length_variation = rng.uniform(0.6, 1.4)
                    base_length = rng.uniform(fur_length_min, fur_length_max)
                    length = base_length * length_variation * (0.7 + 0.3 * np.clip(reference_root_z / depth_scale, 0.0, 1.0))
                    root_x = int(np.clip(round(float(root[0])), 0, width - 1))
                    root_y = int(np.clip(round(float(root[1])), 0, height - 1))
                    length *= 1.0 - (1.0 - self.inner_wall_length_scale) * inner_wall_weight[root_y, root_x]
                    if cavity is not None:
                        length *= cavity.length_scale[root_y, root_x]
                    root_positions.append(root)
                    root_normals.append(root_normal)
                    root_lengths.append(length)
            root_positions = np.array(root_positions, dtype=np.float32)
            root_normals = np.array(root_normals, dtype=np.float32)
            root_lengths = np.array(root_lengths, dtype=np.float32)
            hairs = []
            for root, normal, length in zip(root_positions, root_normals, root_lengths):
                direction_noise = rng.uniform(-direction_randomness, direction_randomness, 3).astype(np.float32)
                radial_dir = root - center
                radial_dir = radial_dir / (np.linalg.norm(radial_dir) + 1e-8)
                radial_strength = 0.35
                if cavity is not None:
                    ry = int(np.clip(round(float(root[1])), 0, height-1))
                    rx = int(np.clip(round(float(root[0])), 0, width-1))
                    # Inner wall fibres follow the recessed surface rather than
                    # the body-wide outward radial direction.
                    radial_strength *= 1.0 - float(cavity.weight[ry, rx])
                init_dir = (1.0 - radial_strength) * normal + radial_strength * radial_dir + direction_noise
                init_dir = init_dir / (np.linalg.norm(init_dir) + 1e-8)
                velocity = init_dir * length
                normalized_depth = (root[2] - z_min) / z_range
                if normalized_depth > 0.6:
                    gravity_factor = 0.12
                elif normalized_depth > 0.3:
                    gravity_factor = 0.5
                else:
                    gravity_factor = 1.0
                adaptive_gravity = gravity_strength * gravity_factor
                position = root.copy()
                points = [position.copy()]
                for _ in range(n_steps):
                    velocity = velocity + gravity_dir * adaptive_gravity * length * dt
                    position = position + velocity * dt
                    points.append(position.copy())
                hairs.append(np.array(points, dtype=np.float32))
            log(
                f"[{index}/{total}] Stage 4/7 complete: {stage_elapsed_message(stage_started)}; "
                f"generated {len(hairs)} strands"
            )

            # Geometry provenance for controlled lighting comparisons.
            geometry_hash = hashlib.sha256()
            for hair in hairs:
                geometry_hash.update(hair.astype("<f4", copy=False).tobytes())
            (self.output_root / f"{output_prefix}_strand_lighting.json").write_text(
                json.dumps({"strand_count": len(hairs),
                            "geometry_sha256": geometry_hash.hexdigest(),
                            "strand_contrast": self.strand_contrast,
                            "strand_highlight": self.strand_highlight}, indent=2),
                encoding="utf-8")

            # Stage 5: rendering
            log(f"[{index}/{total}] Stage 5/7: rendering fur layer (this can take tens of seconds)")
            stage_started = time.time()
            luminance = 0.2126 * image_float[:, :, 0] + 0.7152 * image_float[:, :, 1] + 0.0722 * image_float[:, :, 2]
            masked_luminance = luminance[mask > 0]
            threshold = np.percentile(masked_luminance, 85) if masked_luminance.size else 0.8
            bright_mask = (luminance > threshold) & (mask > 0)
            if bright_mask.sum() > 0:
                by, bx = np.where(bright_mask)
                cy, cx = by.mean(), bx.mean()
                light_dir = np.array([(cx / width - 0.5), (cy / height - 0.5), 0.8], dtype=np.float32)
            else:
                light_dir = np.array([0.25, -0.15, 0.95], dtype=np.float32)
            light_dir = light_dir / np.linalg.norm(light_dir)
            light_color = np.array([1.0, 0.95, 0.9], dtype=np.float32)
            blurred_image = cv2.GaussianBlur(image_float, (0, 0), sigmaX=18, sigmaY=18)
            mask_3d = mask[:, :, np.newaxis].astype(np.float32)
            color_sample_image = mask_3d * blurred_image + (1.0 - mask_3d) * image_float
            masked_pixels = color_sample_image[mask > 0]
            if len(masked_pixels) > 0:
                base_color = np.median(masked_pixels, axis=0).astype(np.float32) * 0.85
                tip_color = np.clip(base_color * 1.25, 0.0, 1.0)
            else:
                base_color = np.array([0.68, 0.48, 0.40], dtype=np.float32)
                tip_color = np.array([0.86, 0.70, 0.62], dtype=np.float32)
            canvas_dtype = np.uint8 if self.stroke_rasterizer == "aa8" else np.float32
            fur_layer = np.zeros((height, width, 3), dtype=canvas_dtype)
            fur_alpha = np.zeros((height, width), dtype=canvas_dtype)
            fine_canvas = None
            if self.fur_finish == "fine":
                fine_canvas = FineFurCanvas(image_float, mask, self.stroke_width_scale,
                                            self.supersample, self.tip_environment_blend)
            shaded_strands = [] if self.fur_order == "depth" else None
            render_progress_step = max(len(hairs) // 4, 1)
            for hair_index, hair in enumerate(hairs, start=1):
                root_pos = hair[0]
                root_x = int(np.clip(root_pos[0], 0, width - 1))
                root_y = int(np.clip(root_pos[1], 0, height - 1))
                if mask[root_y, root_x] > 0:
                    sampled_color = color_sample_image[root_y, root_x]
                    hair_base_color = sampled_color * 0.85
                    hair_tip_color = np.clip(sampled_color * 1.2, 0.0, 1.0)
                else:
                    hair_base_color = base_color
                    hair_tip_color = tip_color
                color_offset = rng.uniform(-0.04, 0.04, 3).astype(np.float32)
                n_points = len(hair)
                segment_colors = np.zeros((n_points - 1, 3), dtype=np.float32) if fine_canvas else None
                for point_index in range(n_points - 1):
                    p0, p1 = hair[point_index], hair[point_index + 1]
                    tangent = p1 - p0
                    tangent_norm = np.linalg.norm(tangent)
                    if tangent_norm < 1e-8:
                        continue
                    tangent = tangent / tangent_norm
                    t_dot_l = np.dot(tangent, light_dir)
                    diffuse = np.sqrt(max(1.0 - t_dot_l * t_dot_l, 0.0))
                    t = point_index / max(n_points - 1, 1)
                    strand_color = np.clip((1.0 - t) * hair_base_color + t * hair_tip_color + color_offset, 0.0, 1.0)
                    shaded_color = np.clip(strand_color * light_color * (0.5 + 0.5 * diffuse), 0.0, 1.0)
                    if fine_canvas is not None:
                        segment_colors[point_index] = shaded_color
                        continue
                    x0, y0 = int(round(p0[0])), int(round(p0[1]))
                    x1, y1 = int(round(p1[0])), int(round(p1[1]))
                    width_px = max(1, int(4.8 * (1.0 - 0.35 * t) * self.stroke_width_scale))
                    if self.stroke_rasterizer == "aa8":
                        draw_color = tuple(int(round(float(value) * 255)) for value in shaded_color)
                        draw_alpha = 255
                    else:
                        draw_color = shaded_color.tolist()
                        draw_alpha = 1.0
                    cv2.line(fur_layer, (x0, y0), (x1, y1), draw_color, thickness=width_px, lineType=cv2.LINE_AA)
                    cv2.line(fur_alpha, (x0, y0), (x1, y1), draw_alpha, thickness=width_px, lineType=cv2.LINE_AA)
                if fine_canvas is not None:
                    segment_colors = shade_strand_detail(
                        hair, segment_colors, hair_index, light_dir,
                        root_normals[hair_index - 1], self.strand_contrast, self.strand_highlight)
                    if shaded_strands is None:
                        fine_canvas.draw_strand(hair, segment_colors, hair_index)
                    else:
                        # Shade in generation order to preserve per-strand RNG colours.
                        shaded_strands.append((hair, segment_colors, hair_index))
                if hair_index % render_progress_step == 0 or hair_index == len(hairs):
                    action = "shaded" if shaded_strands is not None else "rendered"
                    log(f"[{index}/{total}] Stage 5/7 progress: {action} {hair_index}/{len(hairs)} strands")
            if shaded_strands is not None:
                for rendered, (hair, colors, original_index) in enumerate(depth_ordered_strands(shaded_strands), start=1):
                    fine_canvas.draw_strand(hair, colors, original_index)
                    if rendered % render_progress_step == 0 or rendered == len(hairs):
                        log(f"[{index}/{total}] Stage 5/7 depth order: rendered {rendered}/{len(hairs)} strands")
                del shaded_strands
            if self.stroke_rasterizer == "aa8":
                fur_layer = fur_layer.astype(np.float32) / 255.0
                fur_alpha = fur_alpha.astype(np.float32) / 255.0
            if fine_canvas is not None:
                if self.fill_fur_gaps:
                    count = fine_canvas.add_underfur(image_float, normal_image)
                    log(f"[{index}/{total}] Coverage repair: {count} short backing fibres")
                fur_layer, fur_alpha = fine_canvas.finish()
                log(f"[{index}/{total}] Fine fur: {self.supersample}x canvas; "
                    f"{fine_canvas.tinted_segments} segments received exterior tip tint")
            else:
                if self.fur_finish == "alpha":
                    fur_layer = repair_aa_color(fur_layer, fur_alpha)
                else:
                    fur_layer_blurred = cv2.GaussianBlur(fur_layer, (0, 0), sigmaX=1.2, sigmaY=1.2)
                    fur_layer = np.clip(0.85 * fur_layer + 0.15 * fur_layer_blurred, 0.0, 1.0)
                fur_alpha_blurred = cv2.GaussianBlur(fur_alpha, (0, 0), sigmaX=1.5, sigmaY=1.5)
                fur_alpha = fur_alpha_blurred * mask + fur_alpha * (1 - mask)
            fur_alpha = np.clip(fur_alpha * 1.05, 0.0, self.fur_alpha_cap)
            if self.inner_wall_mask_path is not None:
                fur_alpha *= 1.0 - (1.0 - self.inner_wall_opacity) * inner_wall_weight
            if self.exclude_mask_path is not None:
                fur_alpha[excluded_region] = 0.0
            if self.fur_finish != "original":
                Image.fromarray((fur_alpha * 255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_fur_alpha.png")
                Image.fromarray((fur_layer * 255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_fur_color.png")
                Image.fromarray(mask * 255).save(self.output_root / f"{output_prefix}_matte.png")
            log(
                f"[{index}/{total}] Stage 5/7 complete: {stage_elapsed_message(stage_started)}; "
                f"sampled base color {np.round(base_color, 3).tolist()}"
            )

            # Stage 6: final composite
            log(f"[{index}/{total}] Stage 6/7: compositing final image")
            stage_started = time.time()
            result_float = image_float.copy()
            if self.underlayer_mode == "local":
                # Normalized masked blur keeps broad object shading without sampling the background.
                blur_sigma = 32.0
                blurred_weight = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), blur_sigma)
                blurred_color = cv2.GaussianBlur(image_float * mask_3d, (0, 0), blur_sigma)
                diffuse_underlayer = np.clip(
                    blurred_color / np.maximum(blurred_weight[:, :, np.newaxis], 1e-6),
                    0.0,
                    1.0,
                )
                underlayer_preview = (1.0 - mask_3d) * image_float + mask_3d * diffuse_underlayer
                Image.fromarray((underlayer_preview * 255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_underlayer.png"
                )
            elif self.underlayer_mode == "fur":
                # A local undercoat avoids exposing flat backing between fine fibres.
                # Exclude exterior pixels so tip tint never leaks back into the body.
                coat_weight = fur_alpha * mask
                coat_sum = cv2.GaussianBlur(fur_layer * coat_weight[:, :, np.newaxis], (0, 0), 3.0)
                coat_coverage = cv2.GaussianBlur(coat_weight, (0, 0), 3.0)
                diffuse_underlayer = np.clip(coat_sum / np.maximum(coat_coverage[:, :, np.newaxis], 1e-6), 0.0, 1.0)
                preview = (1.0 - mask_3d) * image_float + mask_3d * diffuse_underlayer
                Image.fromarray((preview * 255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_underlayer.png")
            else:
                diffuse_underlayer = np.zeros_like(result_float)
                for channel in range(3):
                    diffuse_underlayer[:, :, channel] = base_color[channel]
            if self.inner_wall_mask_path is not None:
                # Keep the source's recess shading beneath the shorter interior fur.
                wall_weight_3d = inner_wall_weight[:, :, np.newaxis]
                diffuse_underlayer = (1.0 - wall_weight_3d) * diffuse_underlayer + wall_weight_3d * image_float
            result_float = (1.0 - mask_3d) * result_float + mask_3d * diffuse_underlayer
            distance_from_edge = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
            distance_normalized = np.clip(distance_from_edge / 12.0, 0.0, 1.0)
            blend_original = distance_normalized * 0.15
            for channel in range(3):
                result_float[:, :, channel] = (
                    (1.0 - blend_original) * result_float[:, :, channel]
                    + blend_original * image_float[:, :, channel]
                )
            alpha_3d = np.clip(fur_alpha, 0.0, 1.0)[:, :, np.newaxis]
            result_float = np.clip((1.0 - alpha_3d) * result_float + alpha_3d * fur_layer, 0.0, 1.0)
            final_image_uint8 = (result_float * 255).astype(np.uint8)
            if self.inner_wall_mask_path is not None:
                # Add fine image-space fibres to the recessed wall, where projected mesh
                # strands alone leave smooth patches. Feather strokes at the guide edge.
                fibre_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw_fibres = ImageDraw.Draw(fibre_overlay)
                inner_y, inner_x = np.where(inner_wall_region)
                detail_rng = np.random.default_rng(131)
                root_indices = detail_rng.integers(0, len(inner_x), size=int(len(inner_x) * 0.18))
                for root_index in root_indices:
                    x, y = int(inner_x[root_index]), int(inner_y[root_index])
                    brightness = detail_rng.uniform(0.73, 1.28)
                    fibre_color = tuple(
                        np.clip(final_image_uint8[y, x].astype(float) * brightness, 0, 255)
                        .astype(np.uint8)
                        .tolist()
                    )
                    length = int(detail_rng.integers(2, 5))
                    dx = int(detail_rng.integers(-2, 3))
                    draw_fibres.line((x, y, x + dx, y + length), fill=(*fibre_color, 145), width=1)
                feathered_region = Image.fromarray((inner_wall_region * 255).astype(np.uint8)).filter(
                    ImageFilter.GaussianBlur(1.0)
                )
                fibre_overlay.putalpha(ImageChops.multiply(fibre_overlay.getchannel("A"), feathered_region))
                final_image_uint8 = np.asarray(
                    Image.alpha_composite(Image.fromarray(final_image_uint8).convert("RGBA"), fibre_overlay)
                    .convert("RGB")
                )
            if rim_guide is not None:
                Image.fromarray(final_image_uint8).save(
                    self.output_root / f"{output_prefix}_before_rim_detail.png")
                # Use the same quantized coverage as the saved diagnostic alpha,
                # so a local finishing preview can be reproduced exactly.
                rim_coverage = (fur_alpha * 255).astype(np.uint8).astype(np.float32) / 255.0
                final_image_uint8, detail_alpha, rim_support, count = apply_rim_detail(
                    final_image_uint8, rim_guide, rim_coverage,
                    self.rim_detail_strength, self.supersample)
                Image.fromarray((detail_alpha * 255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_rim_detail_alpha.png")
                Image.fromarray((rim_support * 255).astype(np.uint8)).save(
                    self.output_root / f"{output_prefix}_rim_support.png")
                log(f"[{index}/{total}] Rim finish: {count} short fibres; "
                    f"strength {self.rim_detail_strength:g}")
                if self.rear_rim_strength > 0:
                    Image.fromarray(final_image_uint8).save(
                        self.output_root / f"{output_prefix}_before_rear_rim.png")
                    final_image_uint8, rear_alpha, rear_support, rear_count = apply_rear_rim_fringe(
                        final_image_uint8, image_float, mask, rim_guide,
                        self.rear_rim_strength, self.supersample, self.tip_environment_blend)
                    final_fur_alpha = fur_alpha + (1.0 - fur_alpha) * detail_alpha
                    final_fur_alpha += (1.0 - final_fur_alpha) * rear_alpha
                    Image.fromarray((rear_alpha * 255).astype(np.uint8)).save(
                        self.output_root / f"{output_prefix}_rear_rim_alpha.png")
                    Image.fromarray((rear_support * 255).astype(np.uint8)).save(
                        self.output_root / f"{output_prefix}_rear_rim_support.png")
                    Image.fromarray((np.clip(final_fur_alpha, 0, 1) * 255).astype(np.uint8)).save(
                        self.output_root / f"{output_prefix}_final_fur_alpha.png")
                    log(f"[{index}/{total}] Rear rim: {rear_count} outward fibres; "
                        f"strength {self.rear_rim_strength:g}")
            Image.fromarray(final_image_uint8).save(final_output_path)
            if self.inner_wall_mask_path is not None or rim_guide is not None:
                result_float = final_image_uint8.astype(np.float32) / 255.0
            log(f"[{index}/{total}] Stage 6/7 complete: {stage_elapsed_message(stage_started)}")

            # Stage 7: full pipeline
            log(f"[{index}/{total}] Stage 7/7: saving full pipeline overview")
            stage_started = time.time()
            pipeline_normals = np.zeros((height, width, 3), dtype=np.float32)
            for row in range(height):
                for col in range(width):
                    vertex_index = vertex_map[row, col]
                    if vertex_index >= 0:
                        pipeline_normals[row, col] = (vertex_normals[vertex_index] + 1.0) * 0.5
            pipeline_normals[mask == 0] = 0
            depth_vis = cv2.applyColorMap((depth_norm * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
            depth_vis = cv2.cvtColor(depth_vis, cv2.COLOR_BGR2RGB)
            figure = plt.figure(figsize=(15, 10))
            axes = figure.subplots(2, 3)
            axes[0, 0].imshow(source_image_np)
            axes[0, 0].axis("off")
            axes[0, 0].set_title("1. Original")
            axes[0, 1].imshow(mask, cmap="gray")
            axes[0, 1].axis("off")
            axes[0, 1].set_title("2. Mask")
            axes[0, 2].imshow(depth_vis)
            axes[0, 2].axis("off")
            axes[0, 2].set_title("3. Depth")
            axes[1, 0].imshow(pipeline_normals)
            axes[1, 0].axis("off")
            axes[1, 0].set_title("4. Normals")
            axes[1, 1].imshow(fur_layer)
            axes[1, 1].axis("off")
            axes[1, 1].set_title("5. Fur Layer")
            axes[1, 2].imshow(result_float)
            axes[1, 2].axis("off")
            axes[1, 2].set_title("6. Final")
            save_figure(figure, pipeline_output_path, dpi=180)
            log(f"[{index}/{total}] Stage 7/7 complete: {stage_elapsed_message(stage_started)}")

            elapsed = time.time() - started
            log(f"[{index}/{total}] Completed {image_path.name} in {elapsed:.1f}s -> {final_output_path.name}")
            return ImageRunResult(
                image_name=image_path.name,
                status="ok",
                output_dir=str(self.output_root / output_prefix),
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = time.time() - started
            log(f"[{index}/{total}] Failed on {image_path.name}: {exc}")
            return ImageRunResult(
                image_name=image_path.name,
                status="failed",
                output_dir=str(self.output_root / output_prefix),
                elapsed_seconds=elapsed,
                error=str(exc),
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-generate fur-rendering pipeline outputs for every image in image_folder.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on how many images to process.",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Process only the named file from image_folder (for example, mug9.jpg).",
    )
    parser.add_argument(
        "--mask-box",
        type=int,
        nargs=4,
        metavar=("X0", "Y0", "X1", "Y1"),
        default=None,
        help="Use a pixel-coordinate SAM box prompt for a selected image instead of the center point.",
    )
    parser.add_argument(
        "--exclude-mask",
        type=Path,
        default=None,
        help="Exclude white pixels in a same-size grayscale mask from fur; requires --image.",
    )
    parser.add_argument(
        "--inner-wall-mask",
        type=Path,
        default=None,
        help="Style white pixels as a furry inner wall; requires --image and cannot combine with --exclude-mask.",
    )
    parser.add_argument(
        "--inner-wall-length-scale",
        type=float,
        default=0.45,
        help="Scale strand length inside --inner-wall-mask; default 0.45.",
    )
    parser.add_argument(
        "--inner-wall-opacity",
        type=float,
        default=0.70,
        help="Scale fur coverage over the inner wall; default 0.70.",
    )
    parser.add_argument(
        "--stroke-rasterizer",
        choices=("legacy", "aa8"),
        default="legacy",
        help="Use the original float canvas or 8-bit anti-aliased line drawing.",
    )
    parser.add_argument(
        "--stroke-width-scale",
        type=float,
        default=1.0,
        help="Scale strand thickness; 1.0 preserves the original widths.",
    )
    parser.add_argument(
        "--fur-finish", choices=("original", "alpha", "fine"), default="original",
        help="Preserve the baseline, repair AA alpha, or draw fine tapered fibres; new modes require aa8.",
    )
    parser.add_argument(
        "--supersample", type=int, choices=(2, 4), default=4,
        help="Internal canvas scale for the fine finish; final image size is unchanged.",
    )
    parser.add_argument(
        "--tip-environment-blend", type=float, default=0.0,
        help="Mix 0 to 0.3 of nearby background colour into exterior tips; fine finish only.",
    )
    parser.add_argument(
        "--rim-guide-mask", type=Path, default=None,
        help="Image-specific white opening guide; add local outer-rim detail around its boundary.",
    )
    parser.add_argument(
        "--rim-detail-strength", type=float, default=0.75,
        help="Strength of guided local rim finishing in [0, 1]; requires a rim guide to have effect.",
    )
    parser.add_argument(
        "--rear-rim-strength", type=float, default=0.0,
        help="Optional outward rear-rim fibres in [0, 1]; requires --rim-guide-mask.",
    )
    parser.add_argument(
        "--strand-contrast", type=float, default=0.0,
        help="Per-strand brightness variation in [0, 0.4]; 0 preserves shading; fine finish only.",
    )
    parser.add_argument(
        "--strand-highlight", type=float, default=0.0,
        help="Soft directional glint strength in [0, 0.3]; 0 disables; fine finish only.",
    )
    parser.add_argument(
        "--soft-form", type=float, default=0.0,
        help="Opt-in guided silhouette/depth padding, 0 to 12 pixels at 602px; single fine-fur image only.",
    )
    parser.add_argument(
        "--cavity-depth", type=float, default=0.0,
        help="Optional inward relief inside the transformed opening guide, in [0, 0.12] relative depth.",
    )
    parser.add_argument(
        "--cavity-length-scale", type=float, default=1.0,
        help="Inner pile length multiplier in [0.2, 1]; preserves root density and the outer lip.",
    )
    parser.add_argument(
        "--fur-order", choices=("generation", "depth"), default="generation",
        help="Fine-fur draw order: original traversal or approximate far-to-near root depth.",
    )
    parser.add_argument(
        "--fur-alpha-cap", type=float, default=0.92,
        help="Maximum fur opacity in (0, 1]; 1 lets dense fibres fully cover the backing.",
    )
    parser.add_argument(
        "--matte-close-radius", type=int, choices=range(0, 11), default=0,
        help="Opt-in additive mask closing radius in pixels; inspect saved raw/added masks.",
    )
    parser.add_argument(
        "--fill-fur-gaps", action="store_true",
        help="Add short backing fibres only under sparse object coverage; requires fine finish.",
    )
    parser.add_argument(
        "--fur-density",
        type=float,
        default=0.35,
        help="Set strand root density per estimated surface area; 0.35 is the original value.",
    )
    parser.add_argument(
        "--underlayer-mode",
        choices=("flat", "local", "fur"),
        default="flat",
        help="Use the original flat base, blurred source colour, or a local fur-colour undercoat.",
    )
    parser.add_argument(
        "--depth-source",
        choices=("float", "preview8"),
        default="float",
        help="Use full-precision model depth (default) or the original 8-bit preview for A/B comparison.",
    )
    args = parser.parse_args()
    if args.mask_box is not None and args.image is None:
        parser.error("--mask-box requires --image so the coordinates apply to one input.")
    if args.exclude_mask is not None and args.image is None:
        parser.error("--exclude-mask requires --image so the mask applies to one input.")
    if args.inner_wall_mask is not None and args.image is None:
        parser.error("--inner-wall-mask requires --image so the mask applies to one input.")
    if args.inner_wall_mask is not None and args.exclude_mask is not None:
        parser.error("--inner-wall-mask and --exclude-mask cannot be combined.")
    if not np.isfinite(args.fur_alpha_cap) or not 0 < args.fur_alpha_cap <= 1:
        parser.error("--fur-alpha-cap must be finite and in (0, 1].")
    if args.rim_guide_mask is not None and (args.image is None or args.fur_finish != "fine"):
        parser.error("--rim-guide-mask requires --image and --fur-finish fine.")
    if not np.isfinite(args.rim_detail_strength) or not 0 <= args.rim_detail_strength <= 1:
        parser.error("--rim-detail-strength must be finite and between 0 and 1.")
    if not np.isfinite(args.rear_rim_strength) or not 0 <= args.rear_rim_strength <= 1:
        parser.error("--rear-rim-strength must be finite and between 0 and 1.")
    if args.rear_rim_strength > 0 and args.rim_guide_mask is None:
        parser.error("--rear-rim-strength requires --rim-guide-mask.")
    for flag, value, maximum in (("--strand-contrast", args.strand_contrast, 0.4),
                                 ("--strand-highlight", args.strand_highlight, 0.3)):
        if not np.isfinite(value) or not 0 <= value <= maximum:
            parser.error(f"{flag} must be finite and between 0 and {maximum}.")
        if value > 0 and args.fur_finish != "fine":
            parser.error(f"{flag} requires --fur-finish fine.")
    if not np.isfinite(args.soft_form) or not 0 <= args.soft_form <= 12:
        parser.error("--soft-form must be finite and between 0 and 12.")
    if args.soft_form > 0:
        if args.image is None or args.rim_guide_mask is None or args.fur_finish != "fine":
            parser.error("--soft-form requires --image, --rim-guide-mask and --fur-finish fine.")
        if args.exclude_mask is not None or args.inner_wall_mask is not None:
            parser.error("--soft-form cannot yet be combined with the older region-style masks.")
    if not np.isfinite(args.cavity_depth) or not 0 <= args.cavity_depth <= 0.12:
        parser.error("--cavity-depth must be finite and between 0 and 0.12.")
    if not np.isfinite(args.cavity_length_scale) or not 0.2 <= args.cavity_length_scale <= 1:
        parser.error("--cavity-length-scale must be finite and between 0.2 and 1.")
    if args.cavity_depth > 0 or args.cavity_length_scale < 1:
        if args.image is None or args.rim_guide_mask is None or args.fur_finish != "fine":
            parser.error("Cavity refinement requires --image, --rim-guide-mask and --fur-finish fine.")
        if args.exclude_mask is not None or args.inner_wall_mask is not None:
            parser.error("Cavity refinement cannot be combined with older region-style masks.")
    if args.fur_order != "generation" and args.fur_finish != "fine":
        parser.error("--fur-order depth requires --fur-finish fine.")
    if args.fill_fur_gaps and args.fur_finish != "fine":
        parser.error("--fill-fur-gaps requires --fur-finish fine.")
    if args.fur_finish != "original" and args.stroke_rasterizer != "aa8":
        parser.error("--fur-finish alpha/fine requires --stroke-rasterizer aa8.")
    if args.tip_environment_blend != 0 and args.fur_finish != "fine":
        parser.error("--tip-environment-blend requires --fur-finish fine.")
    if not np.isfinite(args.tip_environment_blend) or not 0 <= args.tip_environment_blend <= 0.3:
        parser.error("--tip-environment-blend must be finite and between 0 and 0.3.")
    return args


def main() -> int:
    ensure_environment()
    args = parse_args()
    if not np.isfinite(args.stroke_width_scale) or args.stroke_width_scale <= 0:
        raise ValueError("--stroke-width-scale must be a positive finite number")
    if not np.isfinite(args.fur_density) or args.fur_density <= 0:
        raise ValueError("--fur-density must be a positive finite number")
    if not np.isfinite(args.inner_wall_length_scale) or not 0 < args.inner_wall_length_scale <= 1:
        raise ValueError("--inner-wall-length-scale must be between 0 and 1")
    if not np.isfinite(args.inner_wall_opacity) or not 0 < args.inner_wall_opacity <= 1:
        raise ValueError("--inner-wall-opacity must be between 0 and 1")
    project_root = Path(__file__).resolve().parent
    image_dir = (project_root / "image_folder").resolve()
    output_base_dir = (project_root / "outputs").resolve()
    exclude_mask_path = None
    if args.exclude_mask is not None:
        exclude_mask_path = args.exclude_mask if args.exclude_mask.is_absolute() else project_root / args.exclude_mask
        exclude_mask_path = exclude_mask_path.resolve()
        if not exclude_mask_path.is_file():
            raise ValueError(f"Exclude mask not found: {exclude_mask_path}")
    inner_wall_mask_path = None
    if args.inner_wall_mask is not None:
        inner_wall_mask_path = args.inner_wall_mask if args.inner_wall_mask.is_absolute() else project_root / args.inner_wall_mask
        inner_wall_mask_path = inner_wall_mask_path.resolve()
        if not inner_wall_mask_path.is_file():
            raise ValueError(f"Inner-wall mask not found: {inner_wall_mask_path}")
    rim_guide_mask_path = None
    if args.rim_guide_mask is not None:
        rim_guide_mask_path = args.rim_guide_mask if args.rim_guide_mask.is_absolute() else project_root / args.rim_guide_mask
        rim_guide_mask_path = rim_guide_mask_path.resolve()
        if not rim_guide_mask_path.is_file():
            raise ValueError(f"Rim guide mask not found: {rim_guide_mask_path}")
    run_timestamp = make_run_timestamp()
    run_suffix = "-box" if args.mask_box is not None else ""
    if args.stroke_rasterizer == "aa8":
        run_suffix += "-aa8"
    if args.stroke_width_scale != 1.0:
        run_suffix += f"-width{args.stroke_width_scale:g}"
    if args.fur_density != 0.35:
        run_suffix += f"-density{args.fur_density:g}"
    if args.underlayer_mode != "flat":
        run_suffix += f"-underlayer-{args.underlayer_mode}"
    if exclude_mask_path is not None:
        run_suffix += "-exclude"
    if inner_wall_mask_path is not None:
        run_suffix += f"-innerwall{args.inner_wall_length_scale:g}-opacity{args.inner_wall_opacity:g}"
    if args.fur_finish == "alpha":
        run_suffix += "-alpha"
    elif args.fur_finish == "fine":
        run_suffix += f"-fine{args.supersample}-env{args.tip_environment_blend:g}"
    if args.matte_close_radius:
        run_suffix += f"-close{args.matte_close_radius}"
    if args.fill_fur_gaps:
        run_suffix += "-fillgaps"
    if args.fur_alpha_cap != 0.92:
        run_suffix += f"-cap{args.fur_alpha_cap:g}"
    if args.fur_order != "generation":
        run_suffix += f"-order{args.fur_order}"
    if rim_guide_mask_path is not None:
        run_suffix += f"-rim{args.rim_detail_strength:g}"
    if args.rear_rim_strength > 0:
        run_suffix += f"-rear{args.rear_rim_strength:g}"
    if args.strand_contrast > 0:
        run_suffix += f"-contrast{args.strand_contrast:g}"
    if args.strand_highlight > 0:
        run_suffix += f"-highlight{args.strand_highlight:g}"
    if args.soft_form > 0:
        run_suffix += f"-soft{args.soft_form:g}"
    if args.cavity_depth > 0 or args.cavity_length_scale < 1:
        run_suffix += f"-cavity{args.cavity_depth:g}-pile{args.cavity_length_scale:g}"
    output_root = output_base_dir / f"{run_timestamp}-{args.depth_source}{run_suffix}"

    if not image_dir.exists():
        log(f"Image folder not found: {image_dir}")
        return 1

    images = list(iter_images(image_dir))
    if args.image is not None:
        images = [path for path in images if path.name == args.image]
    if args.limit is not None:
        images = images[: args.limit]

    if not images:
        log(f"No valid images found in {image_dir}")
        return 1

    log(f"Project root: {project_root}")
    log(f"Image folder: {image_dir}")
    log(f"Output base dir: {output_base_dir}")
    log(f"Run output dir: {output_root}")
    log(f"Depth source: {args.depth_source}")
    log(f"Mask prompt: {args.mask_box if args.mask_box is not None else 'center point'}")
    log(f"Stroke rasterizer: {args.stroke_rasterizer}")
    log(f"Stroke width scale: {args.stroke_width_scale:g}")
    log(f"Fur density: {args.fur_density:g}")
    log(f"Fur finish: {args.fur_finish}; supersample {args.supersample}; tip tint {args.tip_environment_blend:g}")
    log(f"Strand lighting: contrast {args.strand_contrast:g}; highlight {args.strand_highlight:g}")
    log(f"Underlayer mode: {args.underlayer_mode}")
    log(f"Exclude mask: {exclude_mask_path if exclude_mask_path is not None else 'none'}")
    log(f"Inner-wall mask: {inner_wall_mask_path if inner_wall_mask_path is not None else 'none'}")
    log(f"Inner-wall length scale: {args.inner_wall_length_scale:g}")
    log(f"Inner-wall opacity: {args.inner_wall_opacity:g}")
    log(f"Discovered {len(images)} image(s)")
    for image_path in images:
        log(f" - {image_path.name}")

    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "run_config.json").write_text(
        json.dumps(
            {
                "image": args.image,
                "depth_source": args.depth_source,
                "mask_box": args.mask_box,
                "stroke_rasterizer": args.stroke_rasterizer,
                "stroke_width_scale": args.stroke_width_scale,
                "fur_density": args.fur_density,
                "fur_finish": args.fur_finish,
                "supersample": args.supersample,
                "tip_environment_blend": args.tip_environment_blend,
                "matte_close_radius": args.matte_close_radius,
                "fill_fur_gaps": args.fill_fur_gaps,
                "fur_alpha_cap": args.fur_alpha_cap,
                "fur_order": args.fur_order,
                "rim_guide_mask": str(args.rim_guide_mask) if args.rim_guide_mask is not None else None,
                "rim_guide_sha256": hashlib.sha256(rim_guide_mask_path.read_bytes()).hexdigest() if rim_guide_mask_path is not None else None,
                "rim_detail_strength": args.rim_detail_strength,
                "rear_rim_strength": args.rear_rim_strength,
                "strand_contrast": args.strand_contrast,
                "strand_highlight": args.strand_highlight,
                "soft_form_amount": args.soft_form,
                "cavity_depth": args.cavity_depth,
                "cavity_length_scale": args.cavity_length_scale,
                "fur_cavity_sha256": hashlib.sha256((project_root / "fur_cavity.py").read_bytes()).hexdigest(),
                "soft_form_sha256": hashlib.sha256((project_root / "soft_form.py").read_bytes()).hexdigest(),
                "fur_lighting_sha256": hashlib.sha256((project_root / "fur_lighting.py").read_bytes()).hexdigest(),
                "fur_rim_sha256": hashlib.sha256((project_root / "fur_rim.py").read_bytes()).hexdigest(),
                "matte_refinement_sha256": hashlib.sha256((project_root / "matte_refinement.py").read_bytes()).hexdigest(),
                "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "fur_strokes_sha256": hashlib.sha256((project_root / "fur_strokes.py").read_bytes()).hexdigest(),
                "underlayer_mode": args.underlayer_mode,
                "exclude_mask": str(args.exclude_mask) if args.exclude_mask is not None else None,
                "inner_wall_mask": str(args.inner_wall_mask) if args.inner_wall_mask is not None else None,
                "inner_wall_length_scale": args.inner_wall_length_scale,
                "inner_wall_opacity": args.inner_wall_opacity,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    runner = FurRenderingBatchRunner(
        project_root=project_root,
        image_dir=image_dir,
        output_root=output_root,
        depth_source=args.depth_source,
        mask_box=args.mask_box,
        stroke_rasterizer=args.stroke_rasterizer,
        stroke_width_scale=args.stroke_width_scale,
        fur_density=args.fur_density,
        underlayer_mode=args.underlayer_mode,
        exclude_mask_path=exclude_mask_path,
        inner_wall_mask_path=inner_wall_mask_path,
        inner_wall_length_scale=args.inner_wall_length_scale,
        inner_wall_opacity=args.inner_wall_opacity,
        fur_finish=args.fur_finish,
        supersample=args.supersample,
        tip_environment_blend=args.tip_environment_blend,
        matte_close_radius=args.matte_close_radius,
        fill_fur_gaps=args.fill_fur_gaps,
        fur_alpha_cap=args.fur_alpha_cap,
        fur_order=args.fur_order,
        rim_guide_mask_path=rim_guide_mask_path,
        rim_detail_strength=args.rim_detail_strength,
        rear_rim_strength=args.rear_rim_strength,
        strand_contrast=args.strand_contrast,
        strand_highlight=args.strand_highlight,
        soft_form_amount=args.soft_form,
        cavity_depth=args.cavity_depth,
        cavity_length_scale=args.cavity_length_scale,
    )
    runner.load_models()

    results = []
    for index, image_path in enumerate(images, start=1):
        results.append(runner.process_image(image_path=image_path, index=index, total=len(images)))

    summary_path = output_root / "batch_summary.json"
    summary_path.write_text(json.dumps([asdict(result) for result in results], indent=2), encoding="utf-8")
    success_count = sum(1 for result in results if result.status == "ok")
    failure_count = len(results) - success_count
    log(f"Batch finished. Success: {success_count}, Failed: {failure_count}")
    log(f"Summary written to: {summary_path}")
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
