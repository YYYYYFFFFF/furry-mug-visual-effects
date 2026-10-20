# Next iteration

This is the remaining plan for a portfolio-oriented refinement. Depth precision, a manual SAM box prompt, antialiased stroke drawing, line width, density, cup-interior exclusion and a local-colour underlayer were tested on 20 October 2026; see [the depth and mask record](experiment-2026-10-20.md), [the stroke record](stroke-experiment-2026-10-20.md), and [the region and underlayer record](region-underlayer-experiment-2026-10-20.md). Keep the original course submission preserved and compare each iteration with the same input images.

1. **Establish a trustworthy baseline.** Run the current script on a small set of simple and patterned mugs; retain the input, mask, depth, fur layer, final composite, elapsed time, and failure reason locally. Resolve report/code differences before making implementation claims.
2. **Improve segmentation control.** A manual box corrected the tested patterned mug, and image-specific binary masks kept the interiors of two other mugs free of fur. Both require user placement. Further foreground/background controls or automatic region detection remain untested. Show the trade-off between automation and control.
3. **Improve the visual result.** The first stroke comparison favours 8-bit antialiasing with half-width lines at the original 0.35 density on two tested mugs; reducing density to 0.15 made one patterned mug worse. The local-colour underlayer made little visible difference, while manual interior exclusion improved cup readability. Next, hold those settings fixed and test strand colour and shading, then direction and length around the rim. Inspect full frames and 100% crops, changing one factor at a time.
4. **Build a concise case study.** Show one strong example, one failure and the iteration that addresses it. State clearly what remains imperfect and credit the reference paper and pretrained models.

Do not describe any proposed technique as implemented until it is in code and a new output has been checked.
