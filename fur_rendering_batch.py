from __future__ import annotations

import argparse
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
from PIL import Image, ImageOps
from segment_anything import SamPredictor, sam_model_registry
from transformers import pipeline

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
    def __init__(self, project_root: Path, image_dir: Path, output_root: Path, depth_source: str, mask_box: list[int] | None) -> None:
        self.project_root = project_root
        self.image_dir = image_dir
        self.output_root = output_root
        self.depth_source = depth_source
        self.mask_box = mask_box
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
            height, width = image_np.shape[:2]
            log(f"[{index}/{total}] Loaded image with size {width} x {height}")

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
            mug_matte = best_mask.astype(np.uint8)
            mask_area = np.sum(best_mask)
            image_area = height * width
            mask_ratio = mask_area / image_area
            if mask_ratio < 0.03:
                raise ValueError("Detected mug matte is too small. Please use a clearer centered mug image.")
            if mask_ratio > 0.85:
                raise ValueError("Detected mug matte is too large and likely includes background.")
            if self.mask_box is None and not bool(best_mask[center_y, center_x]):
                raise ValueError("Image center is not inside the mug matte.")
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
            depth_scale = max(float(vertices[:, 2].max()), 1.0)
            fur_density = 0.35
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
            z_min = vertices[:, 2].min()
            z_max = vertices[:, 2].max()
            z_range = z_max - z_min + 1e-6
            center = vertices.mean(axis=0)
            for triangle in triangles:
                v0, v1, v2 = vertices[triangle].astype(np.float32)
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
                    root_normal = w * n0 + u * n1 + v * n2
                    root_normal = root_normal / (np.linalg.norm(root_normal) + 1e-8)
                    length_variation = rng.uniform(0.6, 1.4)
                    base_length = rng.uniform(fur_length_min, fur_length_max)
                    length = base_length * length_variation * (0.7 + 0.3 * np.clip(root[2] / depth_scale, 0.0, 1.0))
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
            fur_layer = np.zeros((height, width, 3), dtype=np.float32)
            fur_alpha = np.zeros((height, width), dtype=np.float32)
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
                    x0, y0 = int(round(p0[0])), int(round(p0[1]))
                    x1, y1 = int(round(p1[0])), int(round(p1[1]))
                    width_px = max(2, int(4.8 * (1.0 - 0.35 * t)))
                    cv2.line(fur_layer, (x0, y0), (x1, y1), shaded_color.tolist(), thickness=width_px, lineType=cv2.LINE_AA)
                    cv2.line(fur_alpha, (x0, y0), (x1, y1), 1.0, thickness=width_px, lineType=cv2.LINE_AA)
                if hair_index % render_progress_step == 0 or hair_index == len(hairs):
                    log(f"[{index}/{total}] Stage 5/7 progress: rendered {hair_index}/{len(hairs)} strands")
            fur_layer_blurred = cv2.GaussianBlur(fur_layer, (0, 0), sigmaX=1.2, sigmaY=1.2)
            fur_layer = np.clip(0.85 * fur_layer + 0.15 * fur_layer_blurred, 0.0, 1.0)
            fur_alpha_blurred = cv2.GaussianBlur(fur_alpha, (0, 0), sigmaX=1.5, sigmaY=1.5)
            fur_alpha = fur_alpha_blurred * mask + fur_alpha * (1 - mask)
            fur_alpha = np.clip(fur_alpha * 1.05, 0.0, 0.92)
            log(
                f"[{index}/{total}] Stage 5/7 complete: {stage_elapsed_message(stage_started)}; "
                f"sampled base color {np.round(base_color, 3).tolist()}"
            )

            # Stage 6: final composite
            log(f"[{index}/{total}] Stage 6/7: compositing final image")
            stage_started = time.time()
            result_float = image_float.copy()
            diffuse_underlayer = np.zeros_like(result_float)
            for channel in range(3):
                diffuse_underlayer[:, :, channel] = base_color[channel]
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
            Image.fromarray(final_image_uint8).save(final_output_path)
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
            axes[0, 0].imshow(image_np)
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
        "--depth-source",
        choices=("float", "preview8"),
        default="float",
        help="Use full-precision model depth (default) or the original 8-bit preview for A/B comparison.",
    )
    args = parser.parse_args()
    if args.mask_box is not None and args.image is None:
        parser.error("--mask-box requires --image so the coordinates apply to one input.")
    return args


def main() -> int:
    ensure_environment()
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    image_dir = (project_root / "image_folder").resolve()
    output_base_dir = (project_root / "outputs").resolve()
    run_timestamp = make_run_timestamp()
    run_suffix = "-box" if args.mask_box is not None else ""
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
    log(f"Discovered {len(images)} image(s)")
    for image_path in images:
        log(f" - {image_path.name}")

    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "run_config.json").write_text(
        json.dumps({"image": args.image, "depth_source": args.depth_source, "mask_box": args.mask_box}, indent=2),
        encoding="utf-8",
    )

    runner = FurRenderingBatchRunner(
        project_root=project_root,
        image_dir=image_dir,
        output_root=output_root,
        depth_source=args.depth_source,
        mask_box=args.mask_box,
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
