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

## Cup inner-wall control

The earlier `--exclude-mask` test removed fur from the entire cup interior. Yifan identified the resulting ceramic rim, broken fur edge and unfurred inner wall as failures. The [original region experiment](docs/region-underlayer-experiment-2026-10-20.md) now records that rejected output accurately.

For an image-specific correction, `--inner-wall-mask` keeps the visible cup interior in the fur region but styles it with shorter strands, feathered coverage, retained recess shading and fine fibres. The tracked masks are manually placed guides for `mug1.jpg` and `mug3.jpg`; they do not detect the inside of other cups automatically:

```bash
python fur_rendering_batch.py --image mug1.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --inner-wall-mask data/region-masks/mug1-interior.png
```

See [the inner-wall correction record](docs/inner-wall-correction-2026-10-21.md) for full-size and rim-crop comparisons, exact settings and remaining visual problems. The optional `--underlayer-mode local` was also tested and had little visible effect, so `flat` remains the default. All of these results are unpublished local experiments.

## Fine fur and soft tips

Yifan selected the `mug1.jpg` result `20261021-120024-float-aa8-width0.5` as the appearance baseline. The optional fine finish corrects dark antialiasing fringes, draws narrower tapered strands at 4x resolution, and fades their tips. A fur-coloured undercoat fills gaps exposed by the finer strands. Nearby background colour can lightly tint only the exterior part of a strand's tip:

```bash
.venv/bin/python fur_rendering_batch.py --image mug1.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12
```

The tint value is a maximum blending weight, not a uniform 12% recolouring of every tip. The tested difference is subtle; the main visual changes come from alpha correction and finer rendering. `--tip-environment-blend 0` turns the tint off. `--fur-finish alpha` isolates the alpha correction on the older strokes; `--fur-finish original` is the default and keeps the previous renderer. Both new finishes require `aa8`. Keep the same depth, width and density when comparing finishes.

`fur_strokes.py` implements the optional renderer. `tests/test_fur_strokes.py` checks colour/alpha compositing and tint scope without loading models:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

See [the fine-fur experiment](docs/fine-fur-experiment-2026-10-24.md) for exact runs, comparison images, runtime versions and limitations. The local `.venv` was recovered with access to existing system/user packages and cached models; a clean isolated installation has not been validated. New runs record source-file hashes in `run_config.json`. Results remain local pending visual review.

The [visual target](docs/visual-target.md) now uses `mug1.jpg` and the user-selected `120024` result, with `mug3.jpg` as a second check and `mug9.jpg` as a later challenge case. The current candidate uses neither exclusion nor inner-wall guide masks.

## Matte gaps and sparse coverage

Yifan's review of the mug3 `200110` result found a missing patch at the lower handle joint. The raw SAM matte excluded real cup pixels there; the underlayer and hair roots inherited that defect. Fine strands also exposed sparse coverage elsewhere. Optional repairs now let you close small mask defects and add short fibres behind under-covered object pixels:

```bash
.venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1
```

`--matte-close-radius` defaults to `0` (off) and saves raw/added-pixel masks for inspection. Radius 5 was reviewed on this 602px mug3 input; small genuine openings can also close at that scale, so this is not an automatic semantic repair for every image. `--fill-fur-gaps` requires the fine finish and adds short backing fibres only inside sparse object coverage. `--fur-alpha-cap 1` allows dense fur to fully hide the backing; its default remains `0.92` for compatibility. Low-coverage tips still fade.

See [the gap investigation and controlled comparisons](docs/coverage-repair-2026-10-24.md). The previous `200110` output remains reproducible with the old parameters. All new results are local experiments awaiting review.

## Fine-fur overlap order

The repaired mug3 still showed a smooth, apparently bald strip at the right edge. A controlled test reused the same strand geometry, shaded colours and original strand IDs, changing only their draw order. Optional `--fur-order depth` paints approximate farther roots before nearer roots; this makes individual fibres more visible through the affected edge. The full-run matte and alpha PNGs remain byte-identical to the previous candidate.

```bash
.venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1 --fur-order depth
```

This option requires the fine finish. `generation` remains the default and reproduces the previous image. Depth order uses each root's estimated relative depth, not full per-pixel 3D visibility, and changes overlap across the whole object. See [the ordering investigation](docs/depth-order-2026-10-24.md) for edge, rim, joint and body comparisons. The new mode has been visually evaluated on mug3 only and is awaiting user review.

## Local outer-rim detail

Yifan accepted the depth-order result outside the outer lip and requested denser-looking fur only around that rim. Optional guided finishing adds short, curved, interleaved fibres inside a feathered boundary band. It preserves all final pixels outside that band exactly. Add these options to the mug3 depth-order command above:

```bash
--rim-guide-mask data/region-masks/mug3-interior.png --rim-detail-strength 0.75
```

The existing white opening ellipse is reused solely as a placement guide; this does not enable `--inner-wall-mask` styling. `fur_rim.py` performs the local finishing after the accepted primary composite. It saves the pre-finish image, rim support and added alpha so the edit's scope can be checked. This is an image-specific guided effect, not automatic rim detection. See [the rim-detail experiment](docs/rim-detail-2026-10-24.md) for the actual run, narrow-band comparisons and pixel-preservation checks. Without a rim guide, the finishing pass is disabled.

## Current constraints

- Input should contain one centred, clearly bounded mug on a fairly simple background.
- A single centre-point SAM prompt can select only part of a patterned mug.
- The final fur appearance is recognisable but below the visual quality of the reference research.
- The course report and batch script differ in some model and rendering details. Describe the version actually run when presenting results.

The reference paper by Pouli et al., *Rendering fur directly into images*, is available locally at `docs/CAG2010_fur.pdf` and is ignored by Git.

See `docs/optimization-notes.md` for a focused next iteration. The original course program remains preserved under the `original-program` tag. The input photos are tracked in `data/input-images/` within this private archive; model weights and generated images remain Git-ignored. Only approved generated results should be attached to their matching GitHub Release. Check image reuse rights before making this repository public.
