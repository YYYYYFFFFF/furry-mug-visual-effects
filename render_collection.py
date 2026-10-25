"""Render all local input mugs with shared styling and image-specific guides."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageOps
from fur_rendering_batch import FurRenderingBatchRunner, iter_images, log


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def image_settings(preset, image_name):
    settings = dict(preset["shared"])
    override = preset["images"].get(image_name, {})
    settings.update({k: v for k, v in override.items() if k in settings})
    for key in ("rim_guide_mask", "inner_wall_mask", "exclude_mask"):
        if settings[key] and not (ROOT / settings[key]).is_file():
            raise FileNotFoundError(f"{image_name}: missing {key}: {settings[key]}")
    return settings, override


def make_gallery(out: Path, rows) -> None:
    successful = [row for row in rows if row["status"] == "ok"]
    if not successful:
        return
    tile = 260
    cols = 5
    cell_height = tile + 30
    board = Image.new("RGB", (cols * tile, ((len(successful) + cols - 1) // cols) * cell_height), "#20242a")
    draw = ImageDraw.Draw(board)
    cards = []
    for i, row in enumerate(successful):
        x, y = (i % cols) * tile, (i // cols) * cell_height
        result = Image.open(out / row["final_image"]).convert("RGB")
        draw.text((x + 8, y + 8), row["image_name"], fill="white")
        board.paste(ImageOps.contain(result, (tile, tile)), (x, y + 30))
        original = os.path.relpath(ROOT / "image_folder" / row["image_name"], out)
        original, final = html.escape(original, quote=True), html.escape(row["final_image"], quote=True)
        name = html.escape(row["image_name"])
        cards.append(f'<article><h2>{name}</h2><div class="pair"><figure><img loading="lazy" src="{original}"><figcaption>原图</figcaption></figure><figure><a href="{final}"><img loading="lazy" src="{final}"></a><figcaption>毛茸茸效果 · 点击查看原尺寸</figcaption></figure></div></article>')
    board.save(out / "all-mugs-overview.png")
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Furry Mug · 全部杯子</title><style>
body{margin:0;padding:24px;background:#f4f1ec;color:#302c28;font-family:system-ui,sans-serif}main{max-width:1280px;margin:auto}h1{font-size:28px}h2{font-size:18px}article{background:white;border-radius:14px;padding:20px;margin:24px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0}img{display:block;width:100%;height:auto}figcaption{padding:8px 0;color:#6c6259}@media(max-width:650px){body{padding:12px}.pair{gap:8px}article{padding:12px}}a{color:inherit}</style><main><h1>Furry Mug · 全部杯子</h1><p>左侧原图，右侧生成结果。点击结果查看原尺寸。</p>'''
    page += "".join(cards) + "</main></html>"
    (out / "index.html").write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", type=Path, default=Path("presets/fine-fur-b.json"))
    parser.add_argument("--image", help="Optional single input for a repeat check.")
    args = parser.parse_args()
    preset_path = (ROOT / args.preset).resolve()
    preset = json.loads(preset_path.read_text())
    images = sorted(iter_images(ROOT / "image_folder"), key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)])
    if args.image:
        images = [p for p in images if p.name == args.image]
    if not images:
        parser.error("No matching input images.")
    if len({p.stem for p in images}) != len(images):
        parser.error("Input stems must be unique to keep output folders distinct.")
    for path in images:
        if path.name not in preset["images"]:
            parser.error(f"No reviewed placement settings for {path.name}; add an entry to the preset first.")
        image_settings(preset, path.name)
    stamp = datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y%m%d-%H%M%S")
    out = ROOT / "outputs" / f"{stamp}-all-mugs-fine-b"
    out.mkdir(parents=True, exist_ok=False)
    source_files = ["render_collection.py", "fur_rendering_batch.py", "fur_lighting.py", "fur_rim.py", "fur_strokes.py", "matte_refinement.py", "soft_form.py"]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    config = {"preset": preset, "preset_sha256": sha256(preset_path), "starting_code_commit": commit,
              "source_sha256": {name: sha256(ROOT / name) for name in source_files},
              "input_sha256": {p.name: sha256(p) for p in images},
              "model_ids": {"depth": "depth-anything/Depth-Anything-V2-Small-hf", "segmentation": "SAM ViT-B"},
              "sam_checkpoint_sha256": sha256(ROOT / "model_cache/sam_vit_b_01ec64.pth"),
              "package_versions": {name: importlib.metadata.version(name) for name in ["numpy", "torch", "transformers", "opencv-python", "Pillow"]}}
    write_json(out / "run_config.json", config)
    log(f"Collection output: {out}")
    models = None
    rows = []
    for number, image in enumerate(images, 1):
        settings, placement = image_settings(preset, image.name)
        case = out / image.stem
        case.mkdir()
        guide = settings["rim_guide_mask"]
        case_config = {"image": image.name, **settings, "placement_notes": placement,
                       "input_sha256": sha256(image), "rim_guide_sha256": sha256(ROOT / guide) if guide else None,
                       "source_sha256": config["source_sha256"]}
        write_json(case / "run_config.json", case_config)
        arguments = dict(settings)
        for key in ("exclude_mask", "inner_wall_mask", "rim_guide_mask"):
            name = arguments.pop(key)
            arguments[key + "_path"] = ROOT / name if name else None
        runner = FurRenderingBatchRunner(project_root=ROOT, image_dir=ROOT / "image_folder",
                                        output_root=case, **arguments)
        if models is None:
            runner.load_models()
            models = runner.depth_pipe, runner.predictor
        else:
            runner.depth_pipe, runner.predictor = models
        log(f"Collection {number}/{len(images)}: {image.name}")
        # Each image owns a directory, so prefix image_1 is unambiguous and stable.
        result = runner.process_image(image, index=1, total=1)
        row = asdict(result)
        row["output_dir"] = image.stem
        if result.status == "ok":
            final = case / "image_1_final_project_furry_mug.png"
            row.update(final_image=str(final.relative_to(out)), final_sha256=sha256(final))
            if image.name == "mug3.jpg":
                row["matches_previous_B"] = row["final_sha256"] == preset["baseline_mug3_final_sha256"]
        rows.append(row)
        write_json(case / "batch_summary.json", [row])
        write_json(out / "batch_summary.json", rows)
        make_gallery(out, rows)
    failures = sum(row["status"] != "ok" for row in rows)
    log(f"Collection complete: {len(rows) - failures}/{len(rows)} succeeded; {out / 'index.html'}")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
