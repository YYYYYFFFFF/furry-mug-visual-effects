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

Yifan has now reviewed the mug3 depth-order result and identified only the outer lip as still sparse, judging the other areas good. The [local rim-finishing experiment](rim-detail-2026-10-24.md) therefore preserves that result outside a narrow guided band. Earlier notes about dense bodies or dark interiors are historical observations, not instructions to change those accepted areas.

1. **Review the rear/top silhouette against the previous rim-surface result.** Yifan identified sparse protruding fibres there after the surface finish. The [rear-rim pass](rear-rim-2026-10-24.md) creates new outward coverage while preserving the front lip, body and handle. Compare the actual final image and final combined alpha; the primary fur-alpha file excludes these finishing layers.
2. **Preserve the accepted remainder.** Do not change the body, handle, right edge or deeper interior during this refinement. Broader direction, lighting and density changes need a new user request.
3. **Generalize only when requested.** The newest depth-order and rim-detail modes have been visually evaluated on mug3. Other inputs need separate checks and an appropriately aligned rim guide.
4. **Archive an approved version when requested.** Keep local commits and results traceable. Publish the agreed tag/result bundle only after the relevant release approval; development commits are not releases.

Do not claim an achieved reference-similarity percentage without supporting review.
