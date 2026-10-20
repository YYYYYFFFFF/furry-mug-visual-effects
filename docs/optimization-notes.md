# Next iteration

This is a proposed plan for a portfolio-oriented refinement, not a record of completed changes. Keep the original course submission unchanged and compare each iteration with the same input images.

1. **Establish a trustworthy baseline.** Run the current script on a small set of simple and patterned mugs; retain the input, mask, depth, fur layer, final composite, elapsed time, and failure reason locally. Resolve report/code differences before making implementation claims.
2. **Improve segmentation control.** Test a small manual correction path such as a box or extra foreground/background points for the cases where the centre prompt selects a stripe. Show the trade-off between automation and control.
3. **Improve the visual result.** Inspect strand silhouette, density, direction, colour, highlights, and edge blending at full resolution. Change one factor at a time and keep side-by-side comparisons.
4. **Build a concise case study.** Show one strong example, one failure and the iteration that addresses it. State clearly what remains imperfect and credit the reference paper and pretrained models.

Do not describe any proposed technique as implemented until it is in code and a new output has been checked.
