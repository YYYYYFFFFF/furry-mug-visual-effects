# Furry Mug Visual Effects — v2 worktree

An independent COMP5405 course project that turns a centred mug photo into a fur-like composite using pretrained depth estimation, SAM segmentation, and procedural strand rendering. The course output is an exploratory approximation and does not match the quality of the reference paper.

This directory is the `improve/fur-quality-v2` Git worktree. The original course submission and the desktop `main` worktree remain separate. Local input photos and the reference PDF were copied here for comparison; Git ignores them.

## Run the batch script

Use Python 3.10–3.12 and have Git available for the `segment-anything` dependency. The first run downloads pretrained model weights and needs internet access.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fur_rendering_batch.py --limit 1
```

Put one or more `.jpg` or `.png` inputs in `image_folder/`. The batch script saves results under `outputs/<timestamp>/`. `Final_Project.ipynb` is the notebook version. The four notebooks in `experiments/` document earlier method exploration and include Colab-specific code; they are not the main entry point. Notebook execution outputs were removed from these copies, while code cells were retained.

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

See `docs/optimization-notes.md` for a focused next iteration. The original course submission remains separate and unchanged. Input photos, model weights, and generated images are local and ignored by Git until their usage rights and presentation role are decided.
