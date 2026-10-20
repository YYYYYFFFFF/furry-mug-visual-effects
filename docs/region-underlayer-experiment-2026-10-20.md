# Region and underlayer experiment — 20 October 2026

Status: local development experiment on `improve/fur-quality-v2`. This is not an approved release or a measured percentage of similarity to Pouli et al.

## Question and setup

The `mug3.jpg` baseline covered the dark cup interior with fur. We tested whether preserving the interior and using a spatially varying colour underlayer would improve the result. All `mug3.jpg` runs kept float depth, the centre-point SAM prompt, `aa8` strands, width scale `0.5`, density `0.35`, and seed `42`. The underlayer and exclusion mask were varied separately in a 2 × 2 comparison. A second mug checked whether the region-control result carried over.

| Input | Underlayer | Interior exclusion | Local output folder | Observation |
| --- | --- | --- | --- | --- |
| `mug3.jpg` | Flat | None | `outputs/20261020-225129-float-aa8-width0.5/` | Baseline: 53.1% matte coverage, 196,968 strands; interior appears furry. |
| `mug3.jpg` | Local | None | `outputs/20261020-225846-float-aa8-width0.5-underlayer-local/` | Broad shading changes little in the final image; interior still furry. |
| `mug3.jpg` | Flat | `mug3-interior.png` | `outputs/20261020-230201-float-aa8-width0.5-exclude/` | Interior remains ceramic; 42.3% matte coverage, 177,956 strands. |
| `mug3.jpg` | Local | `mug3-interior.png` | `outputs/20261020-230050-float-aa8-width0.5-underlayer-local-exclude/` | Region improvement remains; little visible benefit from the local underlayer. |
| `mug1.jpg` | Flat | None | `outputs/20261020-192831-float-aa8-width0.5/` | Earlier baseline for a second cup. |
| `mug1.jpg` | Flat | `mug1-interior.png` | `outputs/20261020-230353-float-aa8-width0.5-exclude/` | The pink interior and opening are clearer; 23.7% matte coverage, 113,726 strands. |

The [four-way `mug3` board](../outputs/comparisons/20261020-region-underlayer-ab/mug3-ab.png), [`mug1` board](../outputs/comparisons/20261020-region-underlayer-ab/mug1-ab.png), and [machine-readable run record](../outputs/comparisons/20261020-region-underlayer-ab/run-record.json) are local generated artifacts and are Git-ignored. Each run directory also contains `run_config.json` and pipeline images. The input-specific binary exclusion masks are tracked under [`data/region-masks/`](../data/region-masks/README.md).

## What changed

`--exclude-mask` subtracts white pixels from the selected SAM matte before geometry and strand generation. It also clears any stray fur alpha inside that region after rasterization. For both tested cups, every excluded final-image pixel matched the corresponding original RGB pixel byte for byte: 38,957 pixels on `mug3.jpg` and 13,640 on `mug1.jpg`. The masks were manually placed ellipses, so this demonstrates an art-directed correction path, not automatic identification of a cup interior. Their edges need review for each photograph.

`--underlayer-mode local` computes a normalized, mask-weighted Gaussian blur of the source image (`sigma = 32` pixels), preserving broad regional colour while avoiding direct background sampling. On `mug3.jpg` with the same interior exclusion, flat versus local final images differed by a full-frame mean absolute RGB value of 1.001 on a 0–255 scale. This describes change magnitude, not visual quality; inspection found no compelling improvement. The flat underlayer remains the default and the better-supported setting for this iteration.

A default-parameter `mug3.jpg` rerun after the change produced exactly the same final PNG SHA-256 as the earlier baseline (`5568542f93fa40b098002d9ed02c88a8a047d037e757cc950b3ec1bf4d6be935`). The new options therefore did not change this tested default output.

## Reproduce the preferred tested configuration

Copy `mug3.jpg` or `mug1.jpg` from `data/input-images/` to `image_folder/` first. Then run one image with its matching mask:

```bash
python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --exclude-mask data/region-masks/mug3-interior.png
```

For `mug1.jpg`, replace both the input filename and mask filename. The experimental local underlayer can be added with `--underlayer-mode local`; it is optional and not recommended as the current visual default.

## Remaining limits and next test

Both cups still have overlong or irregular tufts around parts of the rim. The body reads more like dense, somewhat stiff fur than the soft reference examples, and lighting and strand colour remain dark or flat in places. The input photos and renderer differ from the paper's examples, so this A/B cannot isolate every reason for the quality gap. Next, keep the preferred region mask and stroke settings fixed while testing strand colour and shading, then direction and length near the rim. Compare full frames and 100% crops before deciding whether any change merits a named version. No “80% close” milestone has been validated.
