# Manually authored region masks

These 602 × 602 binary masks approximate visible cup interiors in their matching source photographs. White pixels identify the visible inner-wall region when passed to `--inner-wall-mask` with `--image`; this keeps the area furry and applies shorter strands and finer texture. The earlier `--exclude-mask` option instead removed all fur there and produced a rejected ceramic interior and rim gap. These are image-specific art-direction inputs, not automatic segmentation or ground-truth annotations. Inspect rim alignment at full resolution before reuse.

- `mug3-interior.png`: hand-placed ellipse, bounding box `(188, 68, 560, 200)` for `mug3.jpg`.
- `mug1-interior.png`: hand-placed ellipse, bounding box `(147, 163, 394, 232)` for `mug1.jpg`.

## Opening guide for outer-rim finishing

The mug3 ellipse is also used by `--rim-guide-mask data/region-masks/mug3-interior.png`. In that mode, the white area only locates the opening boundary; a narrow feathered band around it receives local short-fibre detail. This does not activate the older `--inner-wall-mask` treatment. The guide was inspected against mug3, and the resulting edit is constrained to its rim band; see [the rim-detail record](../../docs/rim-detail-2026-10-24.md). Do not apply the same coordinates to other photographs.

With `--rear-rim-strength` enabled, the same guide's upper half selects the rear lip while the actual mug matte supplies roots. The rear support allows tips outside the old silhouette, unlike the coverage-clipped surface finish. This placement assumes an upright frontal mug; review alignment for each input.

## Full input set, 25 October 2026

`presets/fine-fur-b.json` records the placements used for the full-set test. New `mug2-opening.png`, `mug4-opening.png`, `mug5-opening.png`, `mug6-opening.png`, `mug8-opening.png` and `mug9-opening.png` are manually placed opening ellipses; their exact bounding boxes are in that preset. `mug10-opening.png` is a manually traced approximation of its asymmetric/notched opening boundary, with points recorded in the preset. All are 602 × 602 binary images. They locate local finishing effects and are not automatic detection or ground-truth labels.

Mug1 and mug3 reuse the existing `*-interior.png` images as placement guides only. Mug7 has no visible opening in its frontal photograph, so no opening guide or rear-rim layer is enabled. Full-object SAM boxes for mug5, mug7 and mug9 are separate from these guides. Review both segmentation and guide placement before transferring settings to a different image.
