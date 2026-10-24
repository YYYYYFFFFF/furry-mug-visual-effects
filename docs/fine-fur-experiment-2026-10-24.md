# Fine fur, alpha correction and environment-tinted tips

Date: 24 October 2026. Status: agent-assisted local development experiment. In a subsequent review, Yifan identified sparse fur and a missing lower handle-joint patch in mug3 `200110`. The findings and corrective runs are in [the gap investigation](coverage-repair-2026-10-24.md). The initial full-frame transfer check did not establish clean close-up coverage. No new GitHub release.

## Target and controls

Yifan chose `outputs/20261021-120024-float-aa8-width0.5/` as an acceptable starting appearance, while identifying felt-like texture and a faint gray contour. She requested finer, softer tips that take on a little nearby environment colour. This experiment returns to that exact `mug1.jpg` baseline rather than the newer manual inner-wall treatment.

All mug1 comparisons retain float depth, centre-point SAM, width scale `0.5`, density `0.35`, seed `42`, and no exclusion or inner-wall guide. Geometry, strand roots, random colour variation and the existing shading model remain unchanged. Finish and undercoat are the controlled changes; `mug3.jpg` is a secondary check.

## What changed

1. **Alpha correction:** the earlier `aa8` pipeline draws on black, producing coverage-weighted edge colours, blurs RGB and coverage differently, and then multiplies those edge colours by alpha again in the final composite. This darkens partial-coverage pixels. The `alpha` finish filters RGB and its coverage with identical weights, then converts to straight colour before the existing compositor. A white-line-on-white test isolates this failure and passes with the correction.
2. **Fine strand rendering:** `fur_strokes.py` draws tapered subpixel ribbons on a 4x canvas using source-over premultiplied RGB/alpha. It downsamples both together and converts to straight RGB once. At width scale `0.5`, nominal root width is `0.9` output pixels with small deterministic variation; tips narrow to 6% of root width. Opacity falls toward the tip. This mode skips the older whole-layer blur. Final image dimensions remain 602 × 602.
3. **Fur-colour undercoat:** thinner coverage initially exposed pale speckles over the old flat backing. `--underlayer-mode fur` fills the object with a coverage-weighted local average of its rendered fur colour (Gaussian sigma 3), then retains the existing source-shading blend. It excludes exterior pixels from that average. This is different from the earlier `local` source-colour underlayer test.
4. **Environment tint:** only strands ending outside the SAM mask can sample background. Samples are sought 2, 4, 8 and 12 pixels beyond the tip along the projected strand direction, within an eroded background mask. A masked local colour average avoids directly sampling the cup. The final 35% of a strand can blend toward that colour, with a smoothly increasing weight capped by `--tip-environment-blend`. Only pixels outside the object are tinted. The tint mix uses linear RGB; the inherited shading and most other compositing remain approximations, not a physically based fur model.

The candidate uses a maximum tint weight of `0.12`. Transparent coverage already mixes tips with the underlying background; added tint is deliberately slight. It does not create volume or explain all of the visible improvement.

## Saved runs

All paths below are relative to `outputs/` and contain `run_config.json`, `batch_summary.json` and `image_1_final_project_furry_mug.png`.

| Run | Directory | Observation |
| --- | --- | --- |
| Accepted baseline | `20261021-120024-float-aa8-width0.5` | Starting appearance selected by Yifan. |
| Recovered runtime baseline | `20261024-195316-float-aa8-width0.5` | Byte-identical to `120024` before source changes. |
| Alpha correction only | `20261024-195641-float-aa8-width0.5-alpha` | Gray outline substantially reduced; old broad fibres remain. |
| Fine + flat backing | `20261024-195641-float-aa8-width0.5-fine4-env0` | Diagnostic failure: fine fibres reveal pale central speckles. |
| Fine + fur undercoat, tint off | `20261024-195855-float-aa8-width0.5-underlayer-fur-fine4-env0` | Pale central speckles removed; finer silhouette and handle fibres. |
| **Current mug1 candidate** | **`20261024-195855-float-aa8-width0.5-underlayer-fur-fine4-env0.12`** | Same finish with restrained exterior-tip tint. |
| Post-edit baseline regression | `20261024-200108-float-aa8-width0.5` | Still byte-identical to `120024`. |
| mug3 transfer check | `20261024-200110-float-aa8-width0.5-underlayer-fur-fine4-env0.12` | Fine fringe transfers; dark dense interior remains. |

The mug1 candidate took about 55 seconds and the final baseline check about 30 seconds in this local runtime; mug3 took about 83 seconds. These runs include different workloads and some concurrent execution, so they are not controlled performance benchmarks.

## Review images and provenance

Under `outputs/comparisons/20261024-fine-fur/`:

- `mug1-before-after.png`: accepted baseline and current candidate at original size.
- `mug1-full-comparison.png`: baseline, alpha-only, fine without tint, fine with tint.
- `mug1-detail-comparison.png`: left edge, handle and body at 2x nearest-neighbour enlargement; columns are baseline, alpha-only and candidate.
- `mug3-before-after.png`: secondary input using its earlier `20261020-225129` baseline.
- `run-record.json`: input, model, renderer, output and board SHA-256 checksums; exact settings, runtime versions and scope measurements.

These generated files remain Git-ignored. Each new run also records the renderer and `fur_strokes.py` source hashes, so a result can be matched to its code even before a release is approved. The fine/alpha modes save separate fur colour, alpha and matte images for diagnosis; the fur undercoat is also saved.

Between tint `0` and `0.12` on mug1, zero pixels inside the object changed and the alpha PNGs were byte-identical. 9,856 exterior pixels changed, with a largest channel difference of 6/255 and mean absolute channel difference of approximately 0.58/255 among changed pixels. This confirms a subtle, exterior-only adjustment for this input rather than body recolouring.

The accepted baseline and post-edit baseline both have final PNG SHA-256:

`a6fa4e56389ab5b3b62ce01a666bbe84560dc43ff700f3a2aa11927f57f184eb`

## Reproduce and verify

```bash
.venv/bin/python fur_rendering_batch.py --image mug1.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

The four model-free tests cover white AA edges without darkening, colour preservation and fading partial coverage, exterior-only tint with unchanged alpha, and no environment sampling for an internal strand. All four passed. The actual old-parameter rerender verifies baseline compatibility beyond the unit tests.

The external course drive was unavailable. A local `.venv` was recovered using `--system-site-packages` and existing cached weights. Actual runtime: Python 3.9.6, torch 2.8.0, torchvision 0.23.0, NumPy 2.0.2, OpenCV 4.11.0.86, Pillow 11.3.0, matplotlib 3.9.4, transformers 4.51.3, segment-anything 1.0, huggingface-hub 0.36.2, safetensors 0.7.0 and tokenizers 0.21.4. Renders used offline cached Depth Anything V2 Small and SAM ViT-B. This establishes local execution, not a clean portable installation; `requirements.txt` has not been changed or clean-install validated.

## Remaining limits

- The body remains dense in places; mug3's interior is still dark and coarse. Some rim strands are long or brush-like.
- The fine finish changes the undercoat and apparent surface texture as well as the outline, so user review is still needed.
- Environment sampling relies on the segmentation mask and nearby visible background. Incorrect masks or detailed backgrounds may give unwanted colours. Two simple-background inputs do not establish general performance.
- This remains an image-space approximation with inherited geometry/shading and strand order, not the reference paper's full rendering pipeline. No achieved “80% similarity” claim is supported.
- Fine rendering with the older manual inner-wall guide or exclusion options has not been visually evaluated in this experiment.

`--fur-finish original` remains the default. The original-program tag, accepted baseline PNG and all older output directories remain intact. A release name and result archive should be created only after Yifan approves the visual result.
