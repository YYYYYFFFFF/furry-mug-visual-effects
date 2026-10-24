# Local finishing for the outer cup rim

Date: 24 October 2026. Agent-assisted local refinement. Yifan judged the latest depth-order result good elsewhere and identified the outer rim as the only remaining requested change. Preserve that accepted appearance outside a narrow rim region. This feedback is not authorization to publish a release.

## Diagnosis and chosen scope

The accepted mug3 base is `outputs/20261024-204114-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth/`. The front rim already has full coverage: within the inspected narrow front band, saved alpha has median 1.0 and no pixels below 0.4. It appears sparse because short, similarly aligned fibres form a smooth brush-like strip. Global density changes or more backing coverage would not directly address that visible texture and would disturb accepted regions.

The existing `data/region-masks/mug3-interior.png` ellipse, bounding box `(188, 68, 560, 200)`, provides the opening boundary. This is a manually placed image-specific guide, not a detected or ground-truth rim. The finishing support extends about 3px inward and 12px outward from this guide on the 602px image, feathering both limits and multiplying by existing fur coverage. The small inward feather blends the lip transition; the deeper inner wall is outside the support.

## Implementation

`fur_rim.py` adds a separate image-space finishing layer after the primary composite. It samples rim colour with a mask-weighted local blur, generates thin 3–7px curved fibres with varied directions and brightness, and renders them with the existing supersampled tapered-stroke canvas. Directions follow the outward gradient of the opening guide with variation, so the added fibres overlap instead of forming one uniform short-brush direction. The final detail alpha is clipped by the feathered rim support and selected strength.

The candidate uses strength `0.75`, nominal width scale `0.38`, 4x supersampling and a separate fixed RNG. It adds 16,171 short finishing fibres. No primary roots, depths, shading parameters or global density are changed. Strengths 0.45 and 0.75 were previewed against the same saved base; 0.75 gives the clearer local texture change and was then run through the full pipeline.

`--rim-guide-mask` requires a single `--image` and the fine finish. The main script checks the guide's dimensions and contents. `--rim-detail-strength` ranges from 0 to 1; zero is an exact no-op. Omitting the guide disables the pass. The guide path/checksum, strength and renderer/module hashes are saved in the run configuration.

## Actual result and validation

The full run is:

`outputs/20261024-210324-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75/`

It completed successfully. Visual inspection shows more short interleaved texture on the formerly smooth front lip; the existing circular lip remains legible. The final full-pipeline image is byte-identical to the strength-0.75 preview generated with the same function.

- `image_1_before_rim_detail.png` is byte-identical to the accepted base final PNG.
- Primary matte, fur colour, fur alpha and underlayer PNGs are all byte-identical to the accepted base.
- 10,706 final-image pixels changed, all inside the computed rim support. Zero pixels outside that support changed; zero pixels below image row 240 changed.
- The existing body, handle and right edge outside the rim region are preserved exactly. The deeper inner wall is also outside this edit.
- Nine model-free tests passed, including local-scope preservation, unchanged body/background/opening centre, zero-strength identity, and invalid-guide rejection.

Additional saved files are `image_1_rim_support.png` and `image_1_rim_detail_alpha.png`. The main fur layer PNG remains the primary layer; the added finishing layer is represented by these separate diagnostics. The full-pipeline overview's final panel includes the rim finishing.

## Review artifacts

Under `outputs/comparisons/20261024-rim-detail/`:

- `rim-detail-before-after.png`: front lip at 3x nearest-neighbour enlargement, before above and after below.
- `rim-overview-before-after.png`: the complete cup opening and lip, before/after.
- `mug3-before-after.png`: full-frame comparison.
- `rim-scope-overlay.png` and `changed-pixels.png`: where the edit is allowed and where final pixels actually changed.
- `run-record.json`: exact source/guide/output hashes, settings, accepted-base match and outside-region identity checks.

All generated artifacts remain local and Git-ignored. Only mug3 has been visually evaluated with this finishing pass; other inputs need their own aligned opening guide and review. This is guided image-space detail, not a physically based 3D fur or automatic rim reconstruction. The new lip texture is awaiting Yifan's review; earlier general material criticisms are not a mandate to change the now-accepted rest of this image.

```bash
.venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1 --fur-order depth --rim-guide-mask data/region-masks/mug3-interior.png --rim-detail-strength 0.75
```
