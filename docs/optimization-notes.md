# Next iteration

The current appearance baseline is Yifan's selected `mug1.jpg` result `20261021-120024-float-aa8-width0.5`. Preserve its depth, segmentation and overall appearance while reviewing refinements. The course submission remains preserved by `original-program`.

## Implemented and checked

- [Depth and mask controls](experiment-2026-10-20.md): float depth reduces normal-map banding; a manual box fixes the tested patterned-mug segmentation failure.
- [Stroke experiment](stroke-experiment-2026-10-20.md): `aa8`, half-width lines and density `0.35` are the accepted comparison settings. Reducing density exposed speckling.
- [Region and underlayer experiment](region-underlayer-experiment-2026-10-20.md): full-interior exclusion was rejected because it left visible ceramic and a broken rim. The source-colour underlayer had little visible benefit in that test.
- [Inner-wall correction](inner-wall-correction-2026-10-21.md): optional manual guides restore short inner-wall fur. These guides are not part of `120024` or the current candidate.
- [Fine-fur experiment](fine-fur-experiment-2026-10-24.md): optional corrected alpha, supersampled tapered strands, a fur-colour undercoat and restrained exterior-tip environment tint were rendered on `mug1.jpg` and `mug3.jpg`. The gray outline is substantially reduced. The new undercoat addresses gaps exposed specifically by finer rendering. Four focused tests pass, and the previous baseline output remains byte-identical.

A subsequent close-up review found a lower handle-joint segmentation gap and sparse coverage in mug3 `200110`. The [coverage repair](coverage-repair-2026-10-24.md) adds optional small-gap matte closing and short backing fibres. An independent alpha-cap comparison tests residual backing visibility in dense regions. Earlier full-frame inspection was insufficient to establish defect-free coverage.

## Next decisions

1. **Review the new mug3 repair beside `200110`, and retain `120024` as the mug1 appearance baseline.** Inspect the full image and enlarged left edge, handle and body. The main gain is finer strand rendering and correct edge compositing; tint alone is a small change. Results and exact source hashes are saved locally, with no release yet.
2. **Refine remaining dense material and rim direction if needed.** The central surface and inner wall can still read as dense fibres; some rim strands are brush-like. Local direction/length and shading need separate controlled comparisons. Keep density fixed initially, given the earlier low-density failure.
3. **Check harder inputs after selecting a finish.** The fine finish has only been checked on two simple-background mugs. Patterned `mug9.jpg`, imperfect mattes and detailed backgrounds need their own evaluation. Optional combinations with inner-wall guides have not been evaluated with the new finish.
4. **Prepare an approved result archive and concise case study.** Once Yifan approves a version, bundle its code tag, settings, inputs/model identifiers and generated results under the agreed release name. Show a failure and the actual corrective iteration; credit the paper and pretrained models. Local commits are not releases.

Do not describe proposed techniques as implemented or claim an achieved similarity percentage without supporting review.
