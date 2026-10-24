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

Yifan judged the latest texture close to the desired state and requested deletion of previous local outputs followed by a test of every current cup. The [25 October collection test](all-mugs-2026-10-25.md) uses the recommended B settings and image-specific placement controls. All older generated outputs/comparison files were removed as requested; their dated experiment documents remain historical records.

1. **Review the full set.** Compare each new result against its source photograph in the generated gallery, including handle coverage, visible opening, silhouette, broad colour and surface texture.
2. **Keep the accepted shared styling.** Do not retune density, stroke width, alpha or lighting separately for each image during the transfer check. SAM boxes and manual rim placements correct image-specific region control.
3. **Record transfer limitations.** Mug7 has no visible opening; mug10 has a notched/asymmetric rim. The algorithm still uses approximate depth and image-specific guidance.
4. **Publish only after the relevant release instruction.** User satisfaction with an effect and this local collection test do not assign a release name or trigger publication.

Do not claim an achieved reference-similarity percentage without supporting review.
