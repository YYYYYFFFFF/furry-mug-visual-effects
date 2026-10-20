# Next iteration

This is the remaining plan for a portfolio-oriented refinement. Depth precision, a manual SAM box prompt, antialiased stroke drawing, line width and density were tested on 20 October 2026; see [the depth and mask record](experiment-2026-10-20.md) and [the stroke record](stroke-experiment-2026-10-20.md). Keep the original course submission preserved and compare each iteration with the same input images.

1. **Establish a trustworthy baseline.** Run the current script on a small set of simple and patterned mugs; retain the input, mask, depth, fur layer, final composite, elapsed time, and failure reason locally. Resolve report/code differences before making implementation claims.
2. **Improve segmentation control.** Test a small manual correction path such as a box or extra foreground/background points for the cases where the centre prompt selects a stripe. Show the trade-off between automation and control.
3. **Improve the visual result.** The first stroke comparison favours 8-bit antialiasing with half-width lines at the original 0.35 density on two tested mugs; reducing density to 0.15 made one patterned mug worse. Next, test an underlayer that preserves broad light and shadow while suppressing the original pattern, then inspect strand direction, colour, highlights and edge blending at full resolution. Change one factor at a time and keep side-by-side comparisons.
4. **Build a concise case study.** Show one strong example, one failure and the iteration that addresses it. State clearly what remains imperfect and credit the reference paper and pretrained models.

Do not describe any proposed technique as implemented until it is in code and a new output has been checked.
