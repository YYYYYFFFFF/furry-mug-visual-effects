# Fur stroke comparison — 20 October 2026

Status: local development experiment on `improve/fur-quality-v2`. These results have not been published as a version or GitHub Release. The input and result files below are in Git-ignored `outputs/`; `outputs/comparisons/20261020-stroke-ab/run-record.json` records their checksums and settings.

## Why this test

The batch script requested `cv2.LINE_AA` while drawing onto `float32` arrays. In the installed OpenCV build, a small control drawing on `float32` had only fully lit or unlit edge pixels; the same drawing on an 8-bit array had intermediate edge values. I added optional 8-bit drawing (`--stroke-rasterizer aa8`), then tested line width and strand density while keeping the same input, segmentation prompt, depth mode and model weights.

The original renderer remains the default (`--stroke-rasterizer legacy --stroke-width-scale 1 --fur-density 0.35`). All comparisons used the fixed NumPy seed 42, cached Depth Anything V2 Small-hf and SAM ViT-B weights, and the course Python 3.9 environment described in [the depth experiment](experiment-2026-10-20.md).

## Controlled comparisons

| Input | Settings changed from preceding row | Strands | Observation |
| --- | --- | ---: | --- |
| `mug9.jpg`, float depth, box `(30,75,585,560)` | Legacy renderer, width 1, density 0.35 | 208,230 | Full cup and handle are covered, but the fur has broad, overlapping marks. |
| Same input | 8-bit antialiasing only | 208,230 | Edges look slightly smoother; the dense, coarse surface remains. |
| Same input | Width scale 0.5, keeping 8-bit drawing and density 0.35 | 208,230 | Finer silhouette around rim and handle, and less blocky body texture. This is the most promising of these tested settings. |
| Same input | Density 0.15, keeping 8-bit drawing and width 0.5 | 89,383 | The surface develops conspicuous dark flecks and looks less even. Lowering density this far is not an improvement for this patterned input. |
| `mug1.jpg`, float depth, centre point | Legacy defaults versus 8-bit drawing with width 0.5 and density 0.35 | 125,097 in new run | The combined thin-stroke setting also gives a finer body and edge texture on the simpler cup. This is a combined-setting check, not an independent test of antialiasing on `mug1.jpg`. |

These are visual assessments of the saved full-resolution images, not objective quality scores or evidence that the paper's rendering quality has been reached. The screenshots and exact run directories are in the local comparison folder. The `mug9.jpg` density test also changes the random-number sequence of strand placement; with the same seed it is a parameter comparison, not a pixel-matched subset of the 0.35-density strands.

## Reproduce the selected runs

```bash
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560 --stroke-rasterizer aa8
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560 --stroke-rasterizer aa8 --stroke-width-scale 0.5
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560 --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-density 0.15
python fur_rendering_batch.py --image mug1.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5
```

The optional settings preserve the legacy defaults. `--fur-density` is a density per estimated 3D triangle surface area, so the strand count is input-dependent. The box coordinates are specific to the 602 × 602 `mug9.jpg` file.

After adding all three optional controls, the default `mug9.jpg` float-depth box run was repeated. Its final PNG matched the earlier pre-change result byte for byte (SHA-256 `a2c494431b9eced1c416a3e5572c7a9b33926d5aa3874d24ae17d733dfce0b94`). This checks the default output in the current local environment.

## What to change next

Keep density 0.35 for the next controlled test. The main remaining issue is the flat-looking cup interior: the compositor uses one median-colour underlayer and retains at most 15% of the original interior image before adding fur. Test an underlayer that preserves more broad light-and-shadow variation without reintroducing the original high-contrast surface pattern. Then inspect strand direction and silhouette at full resolution. Preserve both success and failure cases before selecting an approved version.
