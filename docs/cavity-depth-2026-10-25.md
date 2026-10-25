# Mug3 inner-cavity refinement

Date: 25 October 2026. After the rounded-form trial, Yifan found that the cup opening looked too shallow and authorized separating exterior fullness from interior depth: shorten the inner pile and add an inward recess while retaining the rounded lip.

## Change and scope

`fur_cavity.py` adds local inward relief after soft-form transport and before mesh normals and hair generation. It uses the **transported opening guide**, not the original ellipse or the older `--inner-wall-mask` compositing mode. A smooth interior profile reduces normalized inverse depth (larger values are nearer); a 5px lip band is protected at 602px resolution. The centre is recessed by up to 0.055, about 33 units in the renderer's pixel-scaled relative z convention. This is not a physical depth measurement.

Inner strand length blends from the original length at the lip to 60% further inside. Interior fibres also follow the locally recomputed normals instead of the cup-wide outward radial bias. Root sampling, original length variation and the body-wide reference centre use the pre-cavity surface. This retains root density, IDs and the primary RNG schedule instead of resampling the whole cup when inner surface area changes. Exterior matte, deformed source RGB, opening guide and soft-form mapping remain identical.

The existing strand lighting, opacity, contrast, width, outer tip tint, gap filling and guided rim passes remain enabled. No extra cavity darkening or shadow overlay is applied. Backing fibres regenerate from sparse coverage; therefore the final exterior RGB is not promised to be pixel-identical even though the exterior geometry is unchanged.

Both new controls default off: `--cavity-depth 0` and `--cavity-length-scale 1`. They require a single selected fine-fur image and an opening guide, and cannot be combined with the older exclusion/inner-wall styling masks. Depth accepts finite values in `[0, 0.12]`; length accepts `[0.2, 1]`. They can be used with or without soft form. The ten-image preset remains unchanged.

## Reproduction

```bash
HF_HUB_OFFLINE=1 .venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1 --fur-order depth --rim-guide-mask data/region-masks/mug3-interior.png --rim-detail-strength 0.75 --rear-rim-strength 0.85 --strand-contrast 0.12 --strand-highlight 0.12 --soft-form 8 --cavity-depth 0.055 --cavity-length-scale 0.6
```

`HF_HUB_OFFLINE=1` assumes the pretrained models already exist in the local cache. Omit both cavity flags to repeat the rounded-form baseline. New runs save cavity support, before/after depth, recession, length multipliers, diagnostics, parameters and source hashes. The collection source manifest also includes the new module.

- Previous rounded baseline: `outputs/20261025-125327-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12-soft8`.
- New candidate: `outputs/20261025-132719-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12-soft8-cavity0.055-pile0.6`.
- Candidate final PNG SHA-256: `2e041c78d68c966e35052209372a175505a652de1e28fdd2a4046bb36eacfa67`.
- Candidate elapsed render time: 81.5 seconds on the existing local environment.

## Measured checks

- Disabled control: `outputs/20261025-132920-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12-soft8`. With both new options omitted, the final PNG and primary geometry hash match the previous rounded-form baseline exactly (final SHA-256 `528db07fb4c09a20b5e9eace3481d9757e7b3e075bb181d26cedb60f2404fa39`). Control and candidate source hashes match the current renderer files.
- All arrays in the saved soft-form geometry archive are identical to the previous run. The cavity uses exactly its transported opening guide.
- Zero depth pixels outside the opening change; the object matte is identical. The added inward relief affects 34,310 interior pixels, with a maximum relative decrement of 0.055.
- Primary root count remains 155,565. Shorter projected fibres reduce mean final interior fur alpha from 0.9781 to 0.9715. Pixels with alpha below 0.8 increase from 594 to 971; this is a coverage tradeoff, not a removed region or a hole in the matte. The fur-colour undercoat and backing fibres still fill these areas.
- Beyond the opening plus a 24px margin, mean absolute RGB difference is 0.2143 on the 0–255 scale, with 23,277 pixels changing by at least one channel value. These are principally regenerated sparse backing fibres; no exterior deformation was added.
- Twenty-five model-free tests pass, including five cavity tests for identity, protected lip/exterior, continuous recession, independent depth/length controls, bounded low-depth behavior, immutability, determinism and invalid input rejection. Main renderer CRLF line endings are preserved.

## Visual review

Native-size and enlarged mouth comparisons show shorter interior fibres and a clearer concave flow toward the centre. The opening appears less filled by long tangled fibres while the thick rounded lip is retained. The exterior and handle retain their previous shape. No bare ceramic patch or new outline gap was apparent in this mug3 review.

The result is still a guided 2.5D stylization of a single image. It does not reconstruct an unseen deep cup or validate physical occlusion. Only mug3 has been rendered with this new option, and the user has not yet reviewed this candidate. Increasing depth or reducing pile further is not automatically better; the interior could become excessively smooth or bowl-like.

## Review files

- [Full comparison](../outputs/comparisons/20261025-cavity/before-after.png), before left and new candidate right.
- [Enlarged mouth comparison](../outputs/comparisons/20261025-cavity/mouth-before-after.png), using the same crop and scale.
- [Machine-readable measurements](../outputs/comparisons/20261025-cavity/run-record.json).

All previous outputs remain in place. New outputs remain local and Git-ignored, with implementation and this record on the existing branch. No release or remote publication is implied.
