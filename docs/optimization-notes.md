# Next iteration

The current appearance baseline is Yifan's selected `mug1.jpg` result `20261021-120024-float-aa8-width0.5`. Preserve its depth, segmentation and overall appearance while reviewing refinements. The course submission remains preserved by `original-program`.

## Implemented and checked

- [Depth and mask controls](experiment-2026-10-20.md): float depth reduces normal-map banding; a manual box fixes the tested patterned-mug segmentation failure.
- [Stroke experiment](stroke-experiment-2026-10-20.md): `aa8`, half-width lines and density `0.35` are the accepted comparison settings. Reducing density exposed speckling.
- [Region and underlayer experiment](region-underlayer-experiment-2026-10-20.md): full-interior exclusion was rejected because it left visible ceramic and a broken rim. The source-colour underlayer had little visible benefit in that test.
- [Inner-wall correction](inner-wall-correction-2026-10-21.md): optional manual guides restore short inner-wall fur. These guides are not part of `120024` or the current candidate.
- [Fine-fur experiment](fine-fur-experiment-2026-10-24.md): optional corrected alpha, supersampled tapered strands, a fur-colour undercoat and restrained exterior-tip environment tint were rendered on `mug1.jpg` and `mug3.jpg`. The gray outline is substantially reduced. The new undercoat addresses gaps exposed specifically by finer rendering. Four focused tests pass, and the previous baseline output remains byte-identical.

A subsequent close-up review found a lower handle-joint segmentation gap and sparse coverage in mug3 `200110`. The [coverage repair](coverage-repair-2026-10-24.md) adds optional small-gap matte closing and short backing fibres. An independent alpha-cap comparison tests residual backing visibility in dense regions. Earlier full-frame inspection was insufficient to establish defect-free coverage.

The [depth-order comparison](depth-order-2026-10-24.md) then isolated a major cause of the remaining right-side smooth strip: traversal-order overpainting suppresses visible strand detail. Optional root-depth ordering improves that edge on mug3 with identical saved matte/alpha and unchanged primary strands. It also changes body/rim texture; review the whole image. Generalized direction/length or lighting refinement remains separate work.

## Current scope and next decisions

Yifan accepted the rear-rim result and then authorized stronger fur texture through coherent strand brightness variation and restrained highlights. The previous restriction to rim-only changes applied to the completed rim refinement; the current request authorizes shading changes across the mug while retaining its geometry and coverage.

1. **Review texture contrast.** The [strand-lighting A/B experiment](strand-lighting-2026-10-24.md) compares the accepted baseline with per-strand contrast and optional soft glints. Inspect both native size and enlarged body detail.
2. **Keep the accepted fur structure.** Density, thickness, geometry, alpha, soft tips and the rear-rim silhouette remain fixed. No undercoat darkening or global sharpening is part of this comparison.
3. **Generalize only when requested.** Latest shading and guided-rim modes have been visually evaluated on mug3. Other images need separate checks and aligned guides.
4. **Archive an approved version when requested.** Local commits and outputs remain traceable. Publishing an agreed tag/result bundle is a separate release step.

Do not claim an achieved reference-similarity percentage without supporting review.
