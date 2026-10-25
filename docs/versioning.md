# Release and result archive

Only versions Yifan has reviewed and approved are published as GitHub Releases. Development commits are not releases on their own. **Furry Mug V1.0** records the mug3 result from `20261025-153141`, approved for publication on 25 October 2026. See [its release record](releases/v1.0.md). The `original-program` tag and its archived course results remain in the private GitHub repository.

## Names and version numbers

| Release title | Git tag | Meaning |
| --- | --- | --- |
| `Original program` | `original-program` | Course-program code and input archive at commit `8094479` |
| `Furry Mug V1.0` | `v1.0` | First approved improved version |
| `Furry Mug V1.1` | `v1.1` | A smaller approved change after V1.0 |
| `Furry Mug V2.0` | `v2.0` | A substantial approved change after V1.x |

Increase the first number for a substantial change to the visual result or method, and reset the second number to zero. Increase the second number for a smaller refinement. These are integer counters: V1.10 follows V1.9. Yifan confirms the size and release name before publication.

## What travels with each release

For each approved version, create a GitHub Release from its tag and attach a result bundle, for example `furry-mug-v1.0-results.zip`. Include the final images, useful pipeline views, and a small manifest recording the code commit, input image identifiers and checksums, model identifiers or checkpoint checksums, key settings, and output checksums. Keep older releases and their assets intact so the code and the images shown for that version remain together.

Store source mug images in the same private repository under `data/input-images/`, apart from the program files. `data/manifest.json` records their SHA-256 checksums; refer to those exact files from each result manifest. Confirm reuse rights before making any source image or derived output public. The reference-paper PDF stays local; repository documentation may cite and link to the paper.

Pretrained model weights are runtime dependencies, not release images. The script obtains Depth Anything V2 through Transformers and downloads the SAM ViT-B checkpoint when absent. Record the exact model source and version or file checksum used for an approved run. Do not upload weight copies by default.

The private [Original program Release](https://github.com/YYYYYFFFFF/furry-mug-visual-effects/releases/tag/original-program) includes ten saved full-pipeline PNGs from the course report materials in `original-program-results.zip`, with source notes and checksums. They were not regenerated from the tagged code, and their numbered mapping to individual input files has not been independently verified. The first improved release, **Furry Mug V1.0** (`v1.0`), adds the approved mug3 final and its reproducibility bundle. Intermediate development outputs are not separate approved releases.
