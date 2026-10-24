# Visual target for the next Furry Mug iteration

Status: updated on 24 October 2026 to use Yifan's selected `mug1.jpg` result `120024`. The original 20 October input choice was provisional. This is a visual evaluation plan, not a released version or a claim of 80% similarity.

## Reference appearance

Use Pouli et al., *Rendering fur directly into images* (`docs/CAG2010_fur.pdf`) as a qualitative style reference:

- **Figure 9, paper page 6:** short fur integrated into the original photograph. Assess overall material replacement and whether scene lighting still feels coherent.
- **Figure 3, paper page 3:** visible fine strands and a soft, irregular fur silhouette. Assess close-up fibre detail and edge quality.

These figures show different subjects and image scales from the mug photographs. Pixel similarity metrics between them and our output would not measure visual success. The paper PDF and a private reference board remain Git-ignored; do not publish cropped paper figures as project result assets.

## Input selection

All ten archived inputs are 602 × 602 pixels; a local contact sheet is at `outputs/comparisons/20261020-visual-target/input-contact-sheet.png`.

| Role | Input | Reason |
| --- | --- | --- |
| Development hero | `mug1.jpg` | Yifan judged the `20261021-120024-float-aa8-width0.5` result good enough to refine, and specifically requested finer fur, removal of the faint dark outline, and soft tips with a little nearby environment colour. |
| Secondary check | `mug3.jpg` | The earlier provisional hero provides a different shape, lighting and background for checking whether the new finish transfers. |
| Challenge case | `mug9.jpg` | High-contrast pattern exposes masking and colour-transfer failures. A manual SAM box previously selected the full mug after the centre prompt selected only part of it. Not rerun in the 24 October finish experiment. |

The accepted appearance baseline uses float depth, the centre-point SAM prompt, `aa8` stroke rasterization, width scale `0.5`, density `0.35`, flat underlayer and fixed seed `42`. It uses neither the exclusion mask nor the later inner-wall styling guide. Keep those settings for the baseline comparison:

```bash
python fur_rendering_batch.py --image mug1.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5
```

The baseline is under `outputs/20261021-120024-float-aa8-width0.5/`. After the 24 October renderer changes, the same parameters still produce a byte-identical final PNG. The current candidate and comparisons are documented in [the fine-fur experiment](fine-fur-experiment-2026-10-24.md), with boards and checksums under `outputs/comparisons/20261024-fine-fur/`. Generated boards remain Git-ignored.

The earlier `mug3.jpg` baseline (`outputs/20261020-225129-float-aa8-width0.5/`) and private reference board (`outputs/comparisons/20261020-visual-target/private-reference-board.png`) remain available as historical comparisons. The original selection of `mug3.jpg` was not a final portfolio-image decision.

## Proposed visual review gate

To make the requested “80% close” goal reviewable, score each item from 0 (poor) to 4 (close to the intended appearance), looking at the full image and a 100% crop. A provisional gate for the *development hero* is at least 16/20, with no obvious material-region or compositing failure. This is a subjective production rubric, not a scientific similarity metric or a score already achieved.

1. **Region control:** fur covers intended outer body and handle while the opening, handle hole and rim remain coherent.
2. **Silhouette:** short, varied fibres form a soft edge without large polygonal clumps or a uniform halo.
3. **Fibre detail:** fine individual strands remain visible in a 100% crop; the surface reads as fur at normal viewing size.
4. **Shape and light:** body curvature, colour variation and broad light-to-dark form survive material replacement.
5. **Integration:** background and contact shadow remain plausible, with no dark speckles, hard cutout edge or misplaced strands.

Yifan's own visual judgment should decide whether a result is close enough; the numeric gate is only a way to compare local iterations consistently.

## Current result and remaining target

The [region experiment](region-underlayer-experiment-2026-10-20.md) and [inner-wall correction](inner-wall-correction-2026-10-21.md) remain useful history. Full-interior exclusion was rejected by Yifan because it left ceramic visible and broke the furry rim. The later inner-wall styling is optional; it is not part of the user-selected `120024` baseline or the current fine-fur candidate.

The 24 October candidate makes the silhouette finer and substantially reduces the gray fringe on the two rendered mugs. Transparent tapered tips provide most of the softness; nearby environment tint is a restrained finishing adjustment. Fine rendering initially exposed pale gaps over the flat backing, so the candidate uses a locally averaged fur-colour undercoat. This differs from the earlier source-colour underlayer test, which had little visible effect.

Yifan has not yet reviewed this candidate. The surface is still dense in places, the inner wall remains coarse/dark, and some rim strands look long or brush-like. Assess those limits against the accepted baseline before further changes. No result has passed the subjective gate above, and no similarity percentage has been established.

## Follow-up: user review of mug3 coverage

Yifan found visible gaps in `200110`, particularly where the lower handle meets the body, and pointed to the underlayer and matte. A layer-by-layer investigation confirmed that the matte omitted cup pixels there. Sparse fine-fur coverage is a separate issue. See [the corrective experiment](coverage-repair-2026-10-24.md) for repaired masks, local backing fibres, opacity-cap comparisons and the remaining directional band on the right side. The earlier whole-image assessment did not validate these details.

The later [depth-order candidate](depth-order-2026-10-24.md) addresses the right-edge smooth strip through strand overlap order. A full mug3 rerender retains identical matte and alpha while exposing more fine-fibre detail. Yifan subsequently judged the rest of this mug3 result good and requested refinement only of its outer rim. Mug1's earlier selected appearance baseline remains `120024`.

## Current scope after the latest review

Yifan explicitly identified the outer lip as the only remaining requested issue in the mug3 depth-order result and said the other parts were well optimized. Use that exact `204114-...-orderdepth` result as the base for this local refinement. The [rim-detail candidate](rim-detail-2026-10-24.md) changes only a narrow guided rim band, with pixel-exact preservation outside it. Further changes to body, handle, right edge or deeper interior are outside the present request. The new lip texture still needs visual review; this does not set a release name or authorize publication.
