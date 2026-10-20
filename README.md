# Furry Mug Visual Effects

An independent COMP5405 course project that turns a centred mug photo into a fur-like composite using pretrained depth estimation, SAM segmentation, and procedural strand rendering. This repository is a clean starting point for a later visual and technical refinement. The current output is an exploratory approximation and does not match the quality of the reference paper.

## Run the course baseline

Use Python 3.10–3.12 and have Git available for the `segment-anything` dependency. The first run downloads pretrained model weights and needs internet access.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fur_rendering_batch.py --limit 1
```

Put one or more `.jpg` or `.png` inputs in `image_folder/`. The batch script saves results under `outputs/<timestamp>/`. `Final_Project.ipynb` is the notebook version. The four notebooks in `experiments/` document earlier method exploration and include Colab-specific code; they are not the main entry point. Notebook execution outputs were removed from these copies, while code cells were retained.

## Current constraints

- Input should contain one centred, clearly bounded mug on a fairly simple background.
- A single centre-point SAM prompt can select only part of a patterned mug.
- The final fur appearance is recognisable but below the visual quality of the reference research.
- The course report and batch script differ in some model and rendering details. Describe the version actually run when presenting results.

The reference paper by Pouli et al., *Rendering fur directly into images*, is available locally at `docs/CAG2010_fur.pdf` and is ignored by Git.

See `docs/optimization-notes.md` for a focused next iteration. The original course submission remains separate and unchanged. Input photos, model weights, and generated images are local and ignored by Git until their usage rights and presentation role are decided.
