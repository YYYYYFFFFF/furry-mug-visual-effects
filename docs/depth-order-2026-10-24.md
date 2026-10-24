# Right-edge texture and strand overlap

Date: 24 October 2026. Agent-assisted local experiment following Yifan's repeated observation that the right side still looks bald in the previous cap-1 result. No release or visual approval is claimed.

## Evidence and cause

The previous matte repair fixed the lower handle-joint notch, and backing fibres repaired sparse coverage. Increasing the opacity cap reduced backing visibility. Those changes did not resolve the smooth strip on the right edge, which Yifan identified again in a crop of `20261024-202218`.

The remaining strip already had dense alpha coverage. The renderer created triangles in image traversal order and painted complete strands in generation order. That traversal does not represent their front-to-back relationship. Later opaque roots could paint over the finer visible portions of previously drawn strands, suppressing apparent fibre detail even when the pixel was fully covered.

To isolate this, 197,301 strands were captured from the unchanged mug3 pipeline, retaining their geometry, shaded segment colours and original IDs. A padded right-side crop was rerendered using generation, reverse, root-depth and shuffled order. No roots, lengths, widths or colours were changed in this ordering comparison. Reversed, shuffled and depth ordering all changed the apparent texture; root-depth order exposed coherent fine fibres across the smooth band. This establishes an overlap-order contribution without relying on a density increase.

A separate diagnostic approximately recomputed root colours with mask-normalized source blur, excluding background from the samples. That mainly darkened the boundary; generation-order rendering still had the smooth strip. Root-colour masking was therefore not added to the implementation in this change. The existing source-colour and tip-environment treatment remain in place.

## Implementation

`--fur-order depth` requires `--fur-finish fine`. Shading and random colour offsets are still calculated in the original generation order. Each buffered record contains the geometry, shaded segment colours and original strand index. `depth_ordered_strands` sorts these records by root relative depth, using the original index to resolve ties. The existing fine renderer then draws each record with its original identity, retaining the same deterministic width/opacity variation.

Larger root-depth values are treated as nearer in this image-space approximation, so smaller values are painted first. This is a root-based painter order, not per-fragment depth testing. Intersections, long fibres and inaccurate monocular depth can still give incorrect occlusions. The additional shaded-colour buffer adds memory use.

The short-underfur pass and fur-colour undercoat run afterward as before. Their colours derive from the newly composited primary layer, so the complete output includes those downstream colour changes too. The padded crop experiment omitted the optional underfur pass to isolate primary ordering.

## Actual full-pipeline runs

All paths are relative to `outputs/`.

| Role | Directory |
| --- | --- |
| Before, reviewed by Yifan | `20261024-202218-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1` |
| Old-parameter regression | `20261024-204114-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1` |
| Current depth-order candidate | `20261024-204114-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth` |

The full old-parameter rerun is byte-identical to the previous final PNG. Between generation and depth ordering, the matte and saved alpha PNGs are also byte-identical: the same object area and transparency produce visibly different strand texture. Both have 80 masked pixels with saved alpha below 0.4. Both draw 197,301 primary strands and 34,714 short backing fibres. These are coverage/implementation checks, not an aesthetic quality score.

Visual inspection of the full image and enlarged right edge shows more visible individual fibres through the previously smooth strip. The central body and inner wall also appear more strandy because ordering applies across the object. The repaired handle joint remains covered and the handle opening remains open. The inner wall is still dark, the rim still has some coarse or brush-like strands, and the overall directional flow remains stylized. User review of the broader texture change is still needed.

## Review artifacts

`outputs/comparisons/20261024-depth-order/` contains:

- `right-edge-before-after.png`: the same right-side crop, enlarged 3x with nearest-neighbour sampling.
- `mug3-before-after.png`: full-size final images, before and after.
- `other-regions-before-after.png`: rim, lower handle joint and body crops.
- `order-comparison.png`: diagnostic generation/reverse/depth/shuffled ordering of the captured strands.
- `color-order-comparison.png`: diagnostic root-colour versus ordering comparison.
- `run-record.json`: exact run settings, source/input/output hashes, capture hash, crop coordinates, alpha/matte checks and regression result. The geometry capture was temporary diagnostic data; source parameters and hashes identify its provenance.

Seven model-free tests pass, including a new synthetic crossing-strand check: the nearer red fibre remains in front of the farther blue fibre regardless of input-list order. Existing compositing, tint-scope, matte-hole and sparse-coverage tests still pass. The main script's original CRLF line endings are preserved.

```bash
.venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1 --fur-order depth
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Only mug3 has been rendered with this new ordering mode. `generation` remains the default; previous results, tags and output folders are intact. Model weights, generated results and reference PDF remain Git-ignored. A public/release version is not created by this local development commit.

## Subsequent user review

Yifan judged the other areas well optimized and requested only denser-looking fur around the outer lip. The following [local rim finish](rim-detail-2026-10-24.md) uses this exact depth-order image as the accepted base and preserves every final pixel outside its narrow rim band.
