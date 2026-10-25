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

The full-set test is complete. Yifan then clarified that a plush cup should have a softer, rounder underlying shape; adding fur to the unchanged ceramic shape is insufficient. She authorized a one-cup geometry experiment. The [mug3 soft-form trial](soft-form-2026-10-25.md) changes silhouette/depth before regenerating the existing fur finish. The ten-cup gallery and B preset remain intact.

1. **Review shape softness on mug3.** Compare the rendered result, contour overlay and neutral shaded-depth diagnostic. The current trial is modest; the lip is rounder and the body/handle slightly fuller, with cup structure retained.
2. **Separate geometry changes from hair styling.** Width, density parameter and B lighting remain fixed, but new surface area and normals regenerate different strands. Do not describe the result as a pixel-matched edit of the old fur.
3. **Preserve openings and support.** Keep the handle hole and cup opening coherent and the geometric foot anchored. Transfer to other images needs separate review.
4. **Await visual direction before broader changes.** This trial does not enable deformation for all ten cups or publish a release.

Do not claim an achieved reference-similarity percentage without supporting review.
