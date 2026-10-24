"""Regression checks for optional matte and coverage repair."""
import unittest
import numpy as np
from matte_refinement import close_matte_gaps
from fur_strokes import FineFurCanvas


class FurCoverageTests(unittest.TestCase):
    def test_closing_fills_small_defects_without_removing_foreground(self):
        mask = np.zeros((80, 80), dtype=bool)
        mask[10:70, 10:70] = True
        mask[24:56, 24:56] = False  # real handle opening
        mask[60:62, 60:62] = False  # isolated small defect
        mask[45:48, 10:15] = False  # narrow cut from outside
        repaired = close_matte_gaps(mask, 3)
        self.assertTrue(repaired[mask].all())
        self.assertTrue(repaired[60:62, 60:62].all())
        self.assertTrue(repaired[46, 13])
        self.assertFalse(repaired[30:50, 30:50].any())
        self.assertFalse(repaired[:8].any())
        np.testing.assert_array_equal(close_matte_gaps(mask, 0), mask)

    def test_underfur_improves_gaps_preserves_exterior_and_covered_pixels(self):
        mask = np.zeros((32, 32), bool)
        mask[5:27, 5:27] = True
        mask[12:20, 12:20] = False
        image = np.full((32, 32, 3), 0.6, np.float32)
        normals = np.full_like(image, 0.5)
        normals[:, :, 0] = 0.9
        canvas = FineFurCanvas(image, mask)
        # Include fully covered pixels and transparent exterior hair pixels.
        canvas.alpha[24:32, 24:32] = 1
        canvas.rgb[24:32, 24:32] = 0.6
        canvas.alpha[12:16, 12:16] = 0.3
        canvas.rgb[12:16, 12:16] = 0.18
        before_color, before_alpha = canvas.finish()
        count = canvas.add_underfur(image, normals)
        color, alpha = canvas.finish()
        self.assertGreater(count, 0)
        self.assertGreater(alpha[mask].sum(), before_alpha[mask].sum())
        self.assertTrue(np.all(alpha >= before_alpha))
        self.assertTrue(np.isfinite(color).all())
        unchanged = (~mask) | (before_alpha >= 0.8)
        np.testing.assert_array_equal(alpha[unchanged], before_alpha[unchanged])
        np.testing.assert_array_equal(color[unchanged], before_color[unchanged])


if __name__ == '__main__':
    unittest.main()
