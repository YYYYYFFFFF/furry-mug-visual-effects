# Depth and mask comparison — 20 October 2026

Status: local development experiment. No improved version or results have been published as a GitHub Release.

## Setup

- Two 602 × 602 inputs were used: `mug1.jpg` (simple) and `mug9.jpg` (patterned).
- For each input, the same batch renderer was run with `--depth-source preview8` and `--depth-source float`. The strand generator uses a fixed NumPy seed of 42. The `preview8` mode reproduces the earlier batch script's depth input, but these runs are not a reproduction of every setting in the course report.
- Both depth modes used cached Depth Anything V2 Small-hf weights (Hugging Face revision `5426e4f0f36572d16453bbda7a8389317b1bef99`) and the SAM ViT-B checkpoint (SHA-256 `ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912`).
- Runs used the course Python 3.9 environment because it already had the model packages. That environment contains macOS `._` metadata files, so a temporary local launcher skipped those files during import. A fresh install from `requirements.txt` has not yet been verified.
- The images and per-run checksums are under Git-ignored `outputs/comparisons/20261020-depth-ab/`; `run-record.json` gives the exact run directories, input checksums and output checksums. None of these new images is in the GitHub release.

## Observations

| Input and comparison | Observation |
| --- | --- |
| `mug1.jpg`: `preview8` versus `float` | The float normal map has much less visible stair-step banding. The final image changes modestly; the fur still has a coarse, layered texture. The centre-point mask covers the mug and handle in both runs. |
| `mug9.jpg`: `preview8` versus `float` | Float depth again smooths the normal map, but the final image still covers only the patterned lower part because the centre-point SAM mask selects only that area (20.6% of the frame). Depth precision does not fix the mask. |
| `mug9.jpg`: float depth, centre point versus box prompt | A SAM box at `(30, 75, 585, 560)` selects the full cup body and handle (42.7% of the frame). The new final image covers the whole mug. The fur still looks dense and coarse, especially along the rim and handle. |

The full-frame mean absolute RGB difference between depth modes is 4.224/255 for `mug1.jpg` and 4.015/255 for `mug9.jpg`. These values confirm that pixels changed; they are not image-quality scores. The visual conclusions above are qualitative judgments from the saved pipeline and final images.

After adding optional box prompting, the default centre-point `mug9.jpg` run was repeated. Its final PNG matched the previous float-centre result byte for byte (SHA-256 `4fe89fb702477877a6b331144837ab083cf12040543729df79908b9c5d51804c`). This confirms that the new option did not change that default output in this environment.

## Commands for the tested cases

```bash
python fur_rendering_batch.py --image mug1.jpg --depth-source preview8
python fur_rendering_batch.py --image mug1.jpg --depth-source float
python fur_rendering_batch.py --image mug9.jpg --depth-source preview8
python fur_rendering_batch.py --image mug9.jpg --depth-source float
python fur_rendering_batch.py --image mug9.jpg --depth-source float --mask-box 30 75 585 560
```

The `--mask-box` coordinates are pixel positions for the chosen image and require `--image`. Without a box, the batch script keeps its original centre-point SAM prompt. Each run writes `run_config.json`, `batch_summary.json`, a final image and a six-stage pipeline overview to a timestamped folder in `outputs/`.

## Next iteration

Test strand thickness, density and underlayer shading one factor at a time on these same inputs. Preserve both successful and failed examples. Before any public portfolio use, confirm reuse rights for the source photographs and derived images. The reference paper's visual quality has not been reached.
