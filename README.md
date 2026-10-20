# Furry Mug Visual Effects

An independent COMP5405 course project that turns a centred mug photo into a fur-like composite using pretrained depth estimation, SAM segmentation, and procedural strand rendering. The course output is an exploratory approximation and does not match the quality of the reference paper.

This local checkout is on `improve/fur-quality-v2`, the current depth-precision experiment. The original course program is preserved by the `original-program` Git tag and GitHub Release. The input archive is tracked in `data/input-images/`; working copies in `image_folder/` and the reference PDF remain Git-ignored.

See [release and result archive](docs/versioning.md) for the version names and the private [Original program Release](https://github.com/YYYYYFFFFF/furry-mug-visual-effects/releases/tag/original-program) with the saved course results.

## Run the batch script

Use Python 3.10–3.12 and have Git available for the `segment-anything` dependency. The first run downloads pretrained model weights and needs internet access.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fur_rendering_batch.py --limit 1
```

Put one or more `.jpg` or `.png` inputs in `image_folder/`. The original input set and its checksums are stored separately from the program in [data/input-images/](data/README.md); copy the images you want to test into `image_folder/` after cloning. The v2 batch script saves results under `outputs/<timestamp>-<depth-source>/`. `Final_Project.ipynb` still contains the course baseline pipeline and has not received the v2 depth change. The four notebooks in `experiments/` document earlier method exploration and include Colab-specific code; they are not the main entry point. Notebook execution outputs were removed from these copies, while code cells were retained.

## First v2 experiment: depth precision

The batch script now uses the model's full-precision `predicted_depth` for surface geometry by default. Use `--depth-source preview8` to reproduce the original script's 8-bit depth input. On the same input, compare the normal map, fur layer and final composite from these two runs. Each run's output directory ends with its depth source:

```bash
python fur_rendering_batch.py --limit 1 --depth-source preview8
python fur_rendering_batch.py --limit 1 --depth-source float
```

The code change has passed syntax checks, but the complete model pipeline and resulting image quality have not yet been verified in this environment. Keep the two output directories and inspect the images before calling this a visual improvement.

## Current constraints

- Input should contain one centred, clearly bounded mug on a fairly simple background.
- A single centre-point SAM prompt can select only part of a patterned mug.
- The final fur appearance is recognisable but below the visual quality of the reference research.
- The course report and batch script differ in some model and rendering details. Describe the version actually run when presenting results.

The reference paper by Pouli et al., *Rendering fur directly into images*, is available locally at `docs/CAG2010_fur.pdf` and is ignored by Git.

See `docs/optimization-notes.md` for a focused next iteration. The original course program remains preserved under the `original-program` tag. The input photos are tracked in `data/input-images/` within this private archive; model weights and generated images remain Git-ignored. Only approved generated results should be attached to their matching GitHub Release. Check image reuse rights before making this repository public.
