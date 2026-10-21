# Visual target for the next Furry Mug iteration

Status: provisional local development target, chosen on 20 October 2026. This is a visual evaluation plan, not a released version or a claim of 80% similarity.

## Reference appearance

Use Pouli et al., *Rendering fur directly into images* (`docs/CAG2010_fur.pdf`) as a qualitative style reference:

- **Figure 9, paper page 6:** short fur integrated into the original photograph. Assess overall material replacement and whether scene lighting still feels coherent.
- **Figure 3, paper page 3:** visible fine strands and a soft, irregular fur silhouette. Assess close-up fibre detail and edge quality.

These figures show different subjects and image scales from the mug photographs. Pixel similarity metrics between them and our output would not measure visual success. The paper PDF and a private reference board remain Git-ignored; do not publish cropped paper figures as project result assets.

## Input selection

All ten archived inputs are 602 × 602 pixels; a local contact sheet is at `outputs/comparisons/20261020-visual-target/input-contact-sheet.png`.

| Role | Input | Reason |
| --- | --- | --- |
| Development hero | `mug3.jpg` | Mostly matte beige surface, simple background, clear body, open rim and handle. These make the fur material and preservation of shape easier to judge. This is a provisional test input, not yet the final portfolio hero image. |
| Secondary check | `mug1.jpg` | Its softer pink colour and different cup shape reveal whether improvements carry over to another input. An earlier render under the same stroke settings already exists. |
| Challenge case | `mug9.jpg` | High-contrast pattern exposes masking and colour-transfer failures. A manual SAM box previously selected the full mug after the centre prompt selected only part of it. |

The baseline for `mug3.jpg` used float depth, the centre-point SAM prompt, `aa8` stroke rasterization, width scale `0.5`, density `0.35` and fixed seed `42`. The mask covered 53.1% of the frame and the renderer generated 196,968 strands. It includes the cup interior as part of the mug region, and the final cup appears much darker and more uniform than the original. A controlled test later found that the single-colour underlayer was not the main visible cause; see the region and underlayer experiment. Inspect the saved pipeline rather than treating the mask as a perfect material-region label.

```bash
python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5
```

The baseline is under `outputs/20261020-225129-float-aa8-width0.5/`. Local boards at `outputs/comparisons/20261020-visual-target/mug1-mug3-baseline.png` and `private-reference-board.png` show the selected inputs, current renders and private paper reference crops. `run-record.json` records checksums. All generated boards are Git-ignored.

## Proposed visual review gate

To make the requested “80% close” goal reviewable, score each item from 0 (poor) to 4 (close to the intended appearance), looking at the full image and a 100% crop. A provisional gate for the *development hero* is at least 16/20, with no obvious material-region or compositing failure. This is a subjective production rubric, not a scientific similarity metric or a score already achieved.

1. **Region control:** fur covers intended outer body and handle while the opening, handle hole and rim remain coherent.
2. **Silhouette:** short, varied fibres form a soft edge without large polygonal clumps or a uniform halo.
3. **Fibre detail:** fine individual strands remain visible in a 100% crop; the surface reads as fur at normal viewing size.
4. **Shape and light:** body curvature, colour variation and broad light-to-dark form survive material replacement.
5. **Integration:** background and contact shadow remain plausible, with no dark speckles, hard cutout edge or misplaced strands.

Yifan's own visual judgment should decide whether a result is close enough; the numeric gate is only a way to compare local iterations consistently.

## Controlled region test and next target

The planned [2 × 2 region and underlayer test](region-underlayer-experiment-2026-10-20.md) exposed an evaluation mistake: full-interior exclusion made the opening legible but left a ceramic inner wall and a broken fur rim. Yifan rejected that result. The later [inner-wall correction](inner-wall-correction-2026-10-21.md) keeps the inner wall furry while preserving more recess shading; its quality is still provisional. A local-colour underlayer had little visible effect, so flat remains the default. The masks are per-image manual inputs, and no result has passed the subjective review gate above. Next, refine the dark/dense inner-wall material and irregular rim tufts. `mug9.jpg` remains a later challenge case.
