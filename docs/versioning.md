# Release and result archive

Only versions Yifan has reviewed and approved are published as GitHub Releases. Development commits, including the current depth-precision experiment, are not releases. The local `original-program` tag identifies the baseline code while its result archive is still pending.

## Names and version numbers

| Release title | Git tag | Meaning |
| --- | --- | --- |
| `Original program` | `original-program` | Course-program baseline at commit `b1bedba` |
| `Furry Mug V1.0` | `v1.0` | First approved improved version |
| `Furry Mug V1.1` | `v1.1` | A smaller approved change after V1.0 |
| `Furry Mug V2.0` | `v2.0` | A substantial approved change after V1.x |

Increase the first number for a substantial change to the visual result or method, and reset the second number to zero. Increase the second number for a smaller refinement. These are integer counters: V1.10 follows V1.9. Yifan confirms the size and release name before publication.

## What travels with each release

For each approved version, create a GitHub Release from its tag and attach a result bundle, for example `furry-mug-v1.0-results.zip`. Include the final images, useful pipeline views, and a small manifest recording the code commit, input image identifiers and checksums, model identifiers or checkpoint checksums, key settings, and output checksums. Keep older releases and their assets intact so the code and the images shown for that version remain together.

Store source mug images in a separate private image-data location with its own version or checksums; refer to that exact data version from each result manifest. Confirm reuse rights before making any source image or derived output public. The reference-paper PDF stays local; repository documentation may cite and link to the paper.

Pretrained model weights are runtime dependencies, not release images. The script obtains Depth Anything V2 through Transformers and downloads the SAM ViT-B checkpoint when absent. Record the exact model source and version or file checksum used for an approved run. Do not upload weight copies by default.

The `original-program` tag exists locally. No GitHub remote or Release has been created yet. Original-program result files have not been located in this worktree, so its Release should wait until matching outputs are found or regenerated and checked. The current v2 depth experiment has not passed visual review and has no release tag.
