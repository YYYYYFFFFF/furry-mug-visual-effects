# Coherent strand contrast and soft directional highlights

Date: 24 October 2026. Yifan judged the rear-rim result very good, then asked for stronger fur texture contrast and authorized the suggested A/B experiment. This is a newly authorized shading refinement across the mug, preserving its accepted geometry and soft coverage. It does not imply a release or reference-similarity score.

## Baseline and change

The accepted mug3 result is `outputs/20261024-212438-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85/`. Its fine fibres and outward rear rim remain the baseline. The existing shader samples broad colour from a blurred photograph, uses a root-to-tip brightness ramp, and shades by tangent/light orientation. Neighbouring strands can consequently read as a fairly even coat.

`fur_lighting.py` adds `shade_strand_detail` between primary strand shading and rasterization. The two default-off parameters are:

- `--strand-contrast 0.12`: one achromatic RGB gain in approximately `[0.88, 1.12]` per complete strand. Hashed strand IDs provide independent, repeatable values without consuming the main RNG. Adjacent segments retain the same factor, so this is coherent fibre detail rather than per-pixel noise.
- `--strand-highlight 0.12`: adds a broad, soft shaft highlight on approximately 30% of primary strands. Root normal/light alignment, tangent/half-vector orientation and a smooth along-shaft lobe attenuate the maximum gain. It fades before the translucent tip. This is an artistic approximation under the existing image-space +Z view convention, not a physical hair-scattering model or a paper implementation.

The same factor is applied to all RGB channels; gain is limited at the brightest channel rather than clipping each separately. The contrast keeps broad brightness nearly unchanged in this test. Geometry, root RNG, stroke width, density, draw order, antialiasing and opacity are unchanged. Underfur and rim passes retain their existing algorithms and receive updated local colours from the primary image. No whole-image sharpening, undercoat darkening or additional fur is applied.

## Controlled full runs

All three runs used the same cached models, mug3 input, manual opening guide and baseline parameters. Each pipeline completed successfully.

| Run | Contrast | Highlight | Output directory |
| --- | --- | --- | --- |
| Disabled control | 0 | 0 | `outputs/20261024-224206-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85` |
| A | 0.12 | 0 | `outputs/20261024-224338-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12` |
| B | 0.12 | 0.12 | `outputs/20261024-224511-float-aa8-width0.5-underlayer-fur-fine4-env0.12-close5-fillgaps-cap1-orderdepth-rim0.75-rear0.85-contrast0.12-highlight0.12` |

```bash
.venv/bin/python fur_rendering_batch.py --image mug3.jpg --depth-source float --stroke-rasterizer aa8 --stroke-width-scale 0.5 --fur-finish fine --underlayer-mode fur --tip-environment-blend 0.12 --matte-close-radius 5 --fill-fur-gaps --fur-alpha-cap 1 --fur-order depth --rim-guide-mask data/region-masks/mug3-interior.png --rim-detail-strength 0.75 --rear-rim-strength 0.85 --strand-contrast 0.12 --strand-highlight 0.12
```

Remove `--strand-highlight` for A, and both new options for the disabled control.

## Verification and visual inspection

- Disabled control final PNG is byte-identical to the user-accepted rear-rim result.
- All runs have 197,301 identical primary strands (same serialized geometry SHA-256). Existing backing, rim and rear-fringe counts remain 34,714 / 16,171 / 3,911.
- Primary matte, primary alpha, surface-rim alpha/support, rear-rim alpha/support and final combined alpha PNGs are byte-identical across all three runs. Coverage and silhouette have not changed.
- A changes 201,173 final pixels; B changes 201,323. Both candidates also change 215 pixels immediately adjacent to the saved 8-bit coverage by just one channel level (at most 1.4px away). This is consistent with sub-byte antialias coverage quantizing to zero; it is not an exact pixel-preservation claim outside the quantized alpha. No more distant background pixels change.
- In body crop `(270, 300, 470, 480)`, display-RGB luma residual RMS after a sigma-1.2 Gaussian rises from 0.015900 to 0.018767 (A) / 0.019083 (B). Mean luma changes from 0.340866 to 0.340930 / 0.342350. These are texture-change diagnostics, not aesthetic or reference-similarity scores.
- Fifteen model-free tests pass, including four new lighting checks for zero-setting identity, deterministic coherent variation, sparse/facing/tip-limited highlights, identical raster coverage, unchanged input arrays and channel-ratio preservation near white. Six invalid CLI combinations are rejected; tested A/B parameters are accepted. Main renderer CRLF line endings are preserved.

Visual inspection of the native full image and unsharpened enlarged crops shows more distinct light/dark fibres in A and B. B adds a slight brightness lift on selected fibres; its extra glint is subtle relative to A. The rear fringe retains its irregular soft silhouette, and the right-edge/handle comparisons do not show a new continuous dark outline. B is a reasonable first candidate to review, while A retains a more matte appearance.

Only mug3 has been evaluated with this shading pass. The baseline is already dense and fine, so the additional highlights are intentionally restrained and depend on the approximate inferred normals and lighting. Per-strand RGB changes can also affect the apparent texture of the locally averaged backing and the guided rim colours. The manual opening guide remains image-specific. User review of the new shading candidates is pending.

## Artifacts and traceability

`outputs/comparisons/20261024-strand-lighting/` contains the full baseline/A/B board, enlarged body comparisons, rear-rim/right-edge/handle checks, changed-pixel maps and `run-record.json`. The record includes exact settings, input/guide/source hashes, geometry hashes, final PNG hashes, unchanged alpha checks and local texture statistics. Enlargements use nearest-neighbour sampling, with no display sharpening or enhancement.

Older results are retained. Code is saved on the existing local branch; generated images remain Git-ignored. No new branch, GitHub tag or release is created by this experiment.
