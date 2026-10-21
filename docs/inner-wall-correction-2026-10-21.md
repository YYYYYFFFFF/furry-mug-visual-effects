# Cup inner-wall correction — 21 October 2026

Status: provisional local experiment on `improve/fur-quality-v2`; Yifan has not yet accepted its visual quality. The course version and `original-program` release are unchanged.

## Why the previous result failed

Yifan observed that `outputs/20261020-230353-float-aa8-width0.5-exclude/` left a ceramic rim, a visible break in the fur around the opening, and an unfurred inner wall. That result used `--exclude-mask` with an ellipse covering the visible cup interior. The code deliberately removed those pixels from strand generation and forced their fur alpha to zero. Pixel-perfect preservation of the original interior was therefore evidence of the failure, not a quality improvement. The previous experiment record has been corrected.

## Revised local treatment

The new `--inner-wall-mask` treats the same image-specific white ellipse as an *inner-wall styling guide*. It keeps the interior in the SAM mug matte. Within a feathered version of the guide, mesh strands are shorter (`0.45` of their original length), fur coverage is reduced (`0.70` scale), and the original inner-wall shading remains below the fur. A deterministic pass adds short, fine image-space fibres throughout the visible inner wall, including areas that previously looked smooth. The opening's outside rim is no longer cut off by a hard exclusion boundary. The guide is manually authored; there is no automatic inner-wall detector.

```bash
python fur_rendering_batch.py --image mug1.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --inner-wall-mask data/region-masks/mug1-interior.png
```

Use `mug3.jpg` with `mug3-interior.png` for the second tested cup. `--inner-wall-length-scale` and `--inner-wall-opacity` expose the two main style controls; the tested values above are defaults when an inner-wall mask is provided. `--inner-wall-mask` cannot be combined with the earlier `--exclude-mask`.

## Comparisons and checks

- [`mug1` four-way board](../outputs/comparisons/20261021-inner-wall-correction/mug1-four-way.png): original photo, earlier furry baseline, rejected full-interior exclusion, revised inner wall.
- [`mug1` rim detail](../outputs/comparisons/20261021-inner-wall-correction/mug1-rim-detail.png): compare the front rim and inner texture at 2× nearest-neighbour enlargement.
- [`mug3` three-way board](../outputs/comparisons/20261021-inner-wall-correction/mug3-three-way.png): a second-input check.
- [Run record](../outputs/comparisons/20261021-inner-wall-correction/run-record.json): exact output paths, checksums and settings.

The revised `mug1` output is `outputs/20261021-115810-float-aa8-width0.5-innerwall0.45-opacity0.7/`; the revised `mug3` output is `outputs/20261021-115906-float-aa8-width0.5-innerwall0.45-opacity0.7/`. Both completed. On `mug1`, the fur region again covers 27.5% of the image and 125,097 mesh strands are generated, as in its pre-exclusion baseline. The earlier ellipse exclusion had reduced coverage to 23.7% and 113,726 strands. A rerun without inner-wall options produced the same `mug1` final PNG byte for byte as the pre-change baseline (SHA-256 `a6fa4e56389ab5b3b62ce01a666bbe84560dc43ff700f3a2aa11927f57f184eb`).

A first shorter-strand test without reduced coverage retained a dark, flat-looking interior. Lower coverage improved depth but left some smooth patches. A directional test that forced fibres toward the opening centre made the wall smoother and was rejected. The final short-fibre detail pass makes inner-wall texture more visible. These are qualitative visual comparisons, not a measured quality or similarity score.

## Remaining limits

The inner wall can still look dense and dark, especially on `mug3.jpg`; the rim silhouette and handle remain irregular. The manual ellipse may need repainting around highlights or changed cup shapes. The renderer still does not model the cup's true inside geometry or the paper's ribbon-based lighting. Treat this output as a candidate for Yifan's visual review, not a finished “80% close” result. Generated boards and images remain local and Git-ignored.
