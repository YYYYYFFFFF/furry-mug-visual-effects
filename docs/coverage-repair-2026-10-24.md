# Matte gaps and sparse fur: mug3 follow-up

Date: 24 October 2026. Agent-assisted local experiment after Yifan's review of `200110`; not an approved release.

## Diagnosis

Yifan supplied crops showing apparent gaps on the right wall and handle, plus holes in the underlayer and matte. Inspection of the source photograph, matte, fur RGB, alpha and backing separates the causes:

- **Lower handle joint:** the raw SAM matte excludes part of the actual cup. The missing region is also excluded from the underlayer, and no mesh vertices or root triangles exist there. Nearby strands cannot reliably bridge it. The code additionally requires all four pixels of a mesh cell to be valid before creating its triangles, so jagged gaps reduce available root area. Merely increasing strand density or tinting tips cannot fix an excluded region.
- **Sparse fine coverage:** the new narrower fibres leave some valid object pixels under-covered. The smooth undercoat prevents empty colour but contains no fibre detail of its own. In `200110`, 9,498 of 192,323 masked pixels have saved alpha below 0.4. This is a coverage diagnostic, not an image-quality score.
- **Right contour:** most of the highlighted narrow edge already has alpha around 0.92, including pixels just outside the matte. Its smooth/comb-like appearance is not simply missing hair. Similar strand directions and broad shading remain factors. The inherited hard cap of 0.92 also forces at least 8% of the backing to remain visible even under dense overlapping fur; the backing changes abruptly from recoloured cup to the source image at the matte boundary. A separate cap-1 comparison isolates this contribution.

The environment tint does not change alpha or the matte and therefore did not create the missing mask pixels. Thinner strokes made an existing segmentation defect more visible.

## Optional implementation

- `matte_refinement.py` performs additive morphological closing with an elliptical kernel. Radius 5 adds 492 pixels on this image, 448 in the inspected lower-joint crop, removes no foreground, and leaves the large handle opening intact. Radii 3, 5 and 8 were compared against the source; radius 3 leaves much of the notch. This is a geometric repair at a selected pixel scale, not semantic recognition. Small real background openings can also be filled. The raw matte and added pixels are saved for review. Repair runs before geometry and region styling/exclusions.
- `FineFurCanvas.add_underfur` adds 2–4px fibres behind the existing fur only where raw object coverage is below 0.8. It uses a separate fixed RNG, nearby coverage-weighted fur colour and varied projected direction. The high-resolution pass is clipped to sparse object pixels and composited behind the primary layer. It adds 34,714 short fibres on this mug; primary density remains 0.35. It does not alter exterior pixels or well-covered pixels in the fur layer. The subsequently recomputed undercoat can change slightly nearby.
- `--fur-alpha-cap` exposes the inherited 0.92 cap. A value of 1 permits dense bundles to fully cover the backing while preserving partial coverage at sparse tips. This does not force every hair pixel to opacity 1. The existing 1.05 alpha scale is unchanged.

All controls are optional. Old defaults remain radius 0, no short-fibre pass and cap 0.92. No earlier output directory is overwritten.

## Controlled runs

All directories below are relative to `outputs/`; each retains its settings and source hashes in `run_config.json`.

| Run | Directory | Object pixels with saved alpha < 0.4 | Same measure within lower-joint crop |
| --- | --- | ---: | ---: |
| Previous result | `20261024-200110-float-aa8-width0.5-underlayer-fur-fine4-env0.12` | 9,498 | 302 |
| Mask repair only | `20261024-201840-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5` | 9,417 | 201 |
| Mask + short underfur | `20261024-201841-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps` | 80 | 1 |

The lower-joint crop is `(105, 310, 225, 430)`. These counts use each run's own mask; the first row has 448 fewer masked pixels in that crop. The last two rows share an identical mask and primary-strand layout, so their coverage change isolates the short-fibre pass. Their final exterior pixels are identical. Mask repair changes the triangle list and subsequent RNG consumption, so the first and second rows also have different individual strands elsewhere even with the same seed.

The repaired joint no longer has the conspicuous ceramic-looking notch, and the undercoat is continuous. Supplementary fibres reduce sparse gaps while the large handle opening and tapered exterior silhouette remain visible. The broad right-side direction/shading band is not eliminated by these two repairs.

The third comparison is `20261024-202218-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1`, adding only the opacity-cap change to the preceding candidate. The cap-1 render preserves the preceding candidate's matte and fur RGB byte-for-byte. Saved alpha values below the previous cap are unchanged, so sparse tip coverage still fades; only the former cap-limited pixels gain opacity. The full image and enlarged contour show reduced backing visibility, while the broad direction/shading band remains. Its low-coverage pixel count stays at 80. This is the current candidate for review, not a claim that every right-edge artifact is resolved.

## Artifacts and validation

`outputs/comparisons/20261024-coverage-repair/mug3-repaired-before-after.png` compares `200110` with the final cap-1 candidate. `mug3-final-details.png` compares old, repaired cap-0.92, and repaired cap-1 crops; `right-edge-cap-comparison.png` isolates the narrow right contour. The same directory contains full-frame comparisons, enlarged joint/handle/right-wall crops, matte/undercoat/alpha comparisons and a `run-record.json` with exact settings, file hashes and measured coverage. Enlarged pixels use nearest-neighbour scaling, not invented detail. Preliminary cap-removal proxies are diagnostic only; the final cap-1 output is an actual pipeline render.

Six model-free tests passed: the four existing compositing/tint checks plus a synthetic mask test preserving a large opening while repairing tiny defects, and a coverage test asserting increased interior coverage with unchanged exterior and already-covered layer pixels. A full old-parameter rerun at `20261024-202053-float-aa8-width0.5-underlayer-fur-fine4-env0.12` matches the `200110` final PNG byte-for-byte. That run preceded exposing the cap parameter; the parameter's default remains the same literal 0.92, and the final CLI/default check verifies it.

Reproduction command:

```bash
.venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1
```

These repairs were inspected on mug3 only. Matte-closing radius should be reviewed for other inputs, especially narrow genuine openings. The dense interior and directional/shading bands remain limitations of the inherited image-space geometry and lighting. No paper-similarity percentage or final visual approval is claimed.
