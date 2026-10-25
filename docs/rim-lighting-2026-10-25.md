# Mug3 lip lighting and inner-wall separation

Date: 25 October 2026. Yifan found that cup-rim and inner-wall colours blended together, weakening the sense that the front lip sits in front of the cavity. She authorized a one-cup trial of directional rim illumination and a soft inner-wall shadow. This continues the mug3 cavity/short-pile candidate; it does not change its shape.

## Implementation

`fur_rim_lighting.py` builds two local fields from the transported opening guide, the current relative depth, and the renderer's existing estimated light direction. It runs after geometry generation and before strand rasterization.

- **Lip illumination:** a smooth curved cross-section around the opening supplies approximate lip normals. The brightness follows their orientation to the estimated light, with stronger exposure toward its projected direction. A compact feathered band confines the adjustment to the lip.
- **Inner contact shadow:** an interior band checks whether the nearby rim is closer to the camera than the receiving wall, using the same inverse-depth convention as the mesh. The shadow favours the front arc and the inner side behind the light-facing rim. A flat surface receives no contact shadow; the deep cavity and outer cup body are outside its scope.
- **Per-strand colour:** each primary strand samples one gain at its root after the existing contrast/highlight shader. Its original hue and shaft detail are retained; saturated values use a common channel gain limit. A front-lip strand keeps its own lighting where it projects over the darker inner wall. There is no final-image outline, alpha edit, geometry change or shared RNG consumption.

The existing backing and finishing fibres inherit nearby adjusted strand colours. Their geometry and coverage remain unchanged. Global colour sampling blur remains at its previous setting; separate rim/interior colour sampling has not been introduced in this first trial.

This is a guided 2.5D artistic light/contact-shadow approximation, not ray-traced cast shadows or recovered physical scene illumination. The bright-pixel centroid used to estimate lighting may also reflect the original material colour. Front-arc weighting assumes an upright cup with a visible opening. The directional and depth gates provide plausible local cues, not a validated light/material reconstruction.

## Settings and outputs

Use the [previous cavity command](cavity-depth-2026-10-25.md#reproduction) and append:

```bash
--rim-light 0.25 --rim-shadow 0.28
```

Both controls default to `0`, accept finite values in `[0, 0.5]`, and require a single selected image, fine fur and a rim guide. They reject the older exclusion/inner-wall styling masks. They can be enabled independently. The runner saves exact parameters, source hashes, highlight/shadow support PNGs, gain fields in `image_1_rim_lighting.npz`, and diagnostic JSON. The collection source manifest now includes this module; its ten-cup preset still uses the old default settings.

Baseline: `outputs/20261025-132719-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12-soft8-cavity0.055-pile0.6`.

Candidate: `outputs/20261025-153141-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12-soft8-cavity0.055-pile0.6-liplight0.25-shadow0.28`.

Candidate final SHA-256: `6566931ed900fd79904bf9aced82ad3815e364a2c8ebe64335c852ebaf9a8f8f`. Render elapsed time: 78.1 seconds in the existing local environment.

## Verification and review

- Disabled control: `outputs/20261025-153349-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12-soft8-cavity0.055-pile0.6`. Omitting both new flags reproduces the previous final PNG byte for byte (SHA-256 `2e041c78d68c966e35052209372a175505a652de1e28fdd2a4046bb36eacfa67`) with the same strand geometry hash. Control and candidate source hashes match the current implementation; CRLF line endings are retained.
- Thirty model-free tests pass. Five new tests cover disabled identity, deterministic immutable inputs, local/depth-gated shadow support, response to mirrored light direction, bounded hue-preserving strand gains, identical alpha and invalid inputs. Mirrored float32 shadow fields agree within `1e-5`.
- All 155,565 primary strands retain the same geometry hash. The saved soft-form and cavity geometry arrays match the baseline exactly.
- Object matte, primary fur alpha, final fur alpha, rim-detail alpha and rear-fringe alpha PNGs are byte-identical to the baseline. Backing-fibre count remains 37,698.
- Changes affect 23,461 RGB pixels, all within the mouth-area rectangle x=167–581, y=45–210. No final pixel outside this rectangle changes; the body, handle and lower silhouette remain unchanged.
- Applied root gain ranges from 0.720 to 1.242. These extrema are local scalar colour gains, not uniform changes to the whole rim or cavity.
- Native-size and enlarged visual inspection show clearer separation along the front lip, with individual bright lip fibres overlapping the darker inner-wall band. The lip retains its rounded shape. The result remains a local trial for user review; stronger separation also makes the boundary more conspicuous, and its preferred strength is subjective.

## Review artifacts

- [Full comparison](../outputs/comparisons/20261025-rim-lighting/before-after.png): previous cavity result on the left, lighting trial on the right.
- [Mouth comparison](../outputs/comparisons/20261025-rim-lighting/mouth-before-after.png).
- [Front-lip detail](../outputs/comparisons/20261025-rim-lighting/front-lip-before-after.png).
- [Measured comparison record](../outputs/comparisons/20261025-rim-lighting/run-record.json).

Previous outputs are preserved. No other input was rendered with the new settings. Generated results remain local and Git-ignored; no release, remote publication or new branch is created.
