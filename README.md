# Furry Mug Visual Effects

An independent COMP5405 course project that turns a centred mug photo into a fur-like composite using pretrained depth estimation, SAM segmentation, and procedural strand rendering. The course output is an exploratory approximation and does not match the quality of the reference paper.

This local checkout is on `improve/fur-quality-v2`, with local depth, mask and fur-stroke experiments. The original course program is preserved by the `original-program` Git tag and GitHub Release. The input archive is tracked in `data/input-images/`; working copies in `image_folder/` and the reference PDF remain Git-ignored.

See [release and result archive](docs/versioning.md) for the version names and the private [Original program Release](https://github.com/YYYYYFFFFF/furry-mug-visual-effects/releases/tag/original-program) with the saved course results.

## Run the batch script

Use Python 3.10–3.12 and have Git available for the `segment-anything` dependency. The first run downloads pretrained model weights and needs internet access.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fur_rendering_batch.py --limit 1
```

Put one or more `.jpg` or `.png` inputs in `image_folder/`. The original input set and its checksums are stored separately from the program in [data/input-images/](data/README.md); copy the images you want to test into `image_folder/` after cloning. The v2 batch script saves results in timestamped folders under `outputs/`, with the selected settings recorded in each folder’s `run_config.json`. `Final_Project.ipynb` still contains the course baseline pipeline and has not received the v2 depth change. The four notebooks in `experiments/` document earlier method exploration and include Colab-specific code; they are not the main entry point. Notebook execution outputs were removed from these copies, while code cells were retained.

## First v2 experiment: depth precision

The batch script now uses the model's full-precision `predicted_depth` for surface geometry by default. Use `--depth-source preview8` to reproduce the original script's 8-bit depth input. On the same input, compare the normal map, fur layer and final composite from these two runs. Each run's output directory ends with its depth source:

```bash
python fur_rendering_batch.py --limit 1 --depth-source preview8
python fur_rendering_batch.py --limit 1 --depth-source float
```

The two modes were rendered on `mug1.jpg` and `mug9.jpg` on 20 October 2026. Float depth visibly reduces banding in the normal maps, while the change to the final fur image is modest. The patterned mug exposed a separate centre-point mask failure. See [the local experiment record](docs/experiment-2026-10-20.md) for the tested inputs, results and limitations.

## Mask control for patterned mugs

The `--image` option selects one input by filename. When the default centre-point SAM prompt selects only part of a mug, `--mask-box X0 Y0 X1 Y1` supplies a pixel-coordinate box for that image. The tested `mug9.jpg` box below covers the whole cup body and handle:

```bash
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560
```

Box runs save to `outputs/<timestamp>-float-box/`. Each run also saves `run_config.json` alongside the generated images. The box coordinates need to be adjusted for other photos.

## Fur stroke experiment

For the same mug input and mask, the optional 8-bit rasterizer makes OpenCV's line antialiasing effective. A half-width setting produced finer cup and handle edges on the two tested mugs. Lowering density from 0.35 to 0.15 made the patterned mug visibly speckled, so 0.35 remains the better tested density for that image. These are local visual comparisons, not an approved new version.

```bash
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560 --stroke-rasterizer aa8 --stroke-width-scale 0.5
```

The optional defaults are `legacy`, width scale `1`, and density `0.35`. Running without the new options reproduced the prior final PNG byte for byte. The comparison images, exact settings and limitations are in [the stroke experiment record](docs/stroke-experiment-2026-10-20.md). Generated images remain local and Git-ignored until a version is approved for release.

The [next visual target](docs/visual-target.md) provisionally uses `mug3.jpg` as the development hero, with `mug1.jpg` as a second check and `mug9.jpg` as a challenge case. It records the reference figures, current baseline and a subjective review rubric.

## Current constraints

- Input should contain one centred, clearly bounded mug on a fairly simple background.
- A single centre-point SAM prompt can select only part of a patterned mug.
- The final fur appearance is recognisable but below the visual quality of the reference research.
- The course report and batch script differ in some model and rendering details. Describe the version actually run when presenting results.

The reference paper by Pouli et al., *Rendering fur directly into images*, is available locally at `docs/CAG2010_fur.pdf` and is ignored by Git.

See `docs/optimization-notes.md` for a focused next iteration. The original course program remains preserved under the `original-program` tag. The input photos are tracked in `data/input-images/` within this private archive; model weights and generated images remain Git-ignored. Only approved generated results should be attached to their matching GitHub Release. Check image reuse rights before making this repository public.
