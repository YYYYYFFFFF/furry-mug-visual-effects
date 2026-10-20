# Manually authored region masks

These 602 × 602 binary masks approximate visible cup interiors in their matching source photographs. White pixels are excluded from fur generation and compositing when passed to `--exclude-mask` with `--image`. They are image-specific art-direction inputs, not automatic segmentation or ground-truth annotations. Inspect rim alignment at full resolution before reuse.

- `mug3-interior.png`: hand-placed ellipse, bounding box `(188, 68, 560, 200)` for `mug3.jpg`.
- `mug1-interior.png`: hand-placed ellipse, bounding box `(147, 163, 394, 232)` for `mug1.jpg`.
