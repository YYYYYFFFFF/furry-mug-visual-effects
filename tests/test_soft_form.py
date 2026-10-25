"""Soft geometry must preserve background, foreground sampling and openings."""
import unittest
import cv2
import numpy as np
from soft_form import deform_soft_form


class SoftFormTests(unittest.TestCase):
    def setUp(self):
        self.mask = np.zeros((220, 240), np.uint8)
        cv2.rectangle(self.mask, (80, 52), (200, 185), 1, -1)
        cv2.ellipse(self.mask, (140, 52), (60, 24), 0, 0, 360, 1, -1)
        handle = np.zeros_like(self.mask)
        cv2.ellipse(handle, (60, 112), (36, 50), 0, 0, 360, 1, -1)
        cv2.ellipse(handle, (60, 112), (23, 36), 0, 0, 360, 0, -1)
        self.mask |= handle
        self.guide = np.zeros_like(self.mask)
        cv2.ellipse(self.guide, (140, 52), (54, 17), 0, 0, 360, 1, -1)
        self.rgb = np.full((220, 240, 3), [230, 245, 250], np.uint8)
        self.rgb[self.mask > 0] = [115, 80, 40]
        self.depth = np.where(self.mask > 0, 0.6, 0.02).astype(np.float32)

    def run_form(self, amount=8):
        return deform_soft_form(self.rgb, self.depth, self.mask, self.guide, amount)

    def test_zero_is_exact_identity(self):
        result = self.run_form(0)
        for got, original in [(result.rgb, self.rgb), (result.depth, self.depth),
                              (result.mask, self.mask), (result.opening, self.guide)]:
            np.testing.assert_array_equal(got, original)
        yy, xx = np.mgrid[:220, :240]
        np.testing.assert_array_equal(result.map_x, xx)
        np.testing.assert_array_equal(result.map_y, yy)

    def test_added_surface_samples_foreground_not_background(self):
        result = self.run_form()
        added = result.mask & (self.mask == 0)
        self.assertGreater(added.sum(), 100)
        np.testing.assert_array_equal(result.rgb[added], np.tile([115, 80, 40], (added.sum(), 1)))
        self.assertTrue(np.all(result.depth[added] >= 0.59999))
        union = result.mask | (self.mask > 0)
        np.testing.assert_array_equal(result.rgb[~union], self.rgb[~union])
        self.assertGreater(float(result.padding.max()), 0)

    def test_foot_and_handle_hole_survive_without_map_folds(self):
        result = self.run_form()
        start = int(np.ceil(result.diagnostics['bottom_anchor_from_row']))
        np.testing.assert_array_equal(result.mask[start:], self.mask[start:])
        np.testing.assert_array_equal(result.rgb[start:], self.rgb[start:])
        np.testing.assert_allclose(result.depth[start:], self.depth[start:], atol=1e-7)
        self.assertFalse(result.mask[112, 60])
        self.assertEqual(cv2.connectedComponents((~result.mask).astype(np.uint8), connectivity=8)[0],
                         cv2.connectedComponents((self.mask == 0).astype(np.uint8), connectivity=8)[0])
        self.assertGreater(result.diagnostics['opening_area_ratio'], 0.75)
        self.assertGreater(result.diagnostics['min_inverse_jacobian'], 0.1)
        self.assertLess(result.diagnostics['inverse_residual_px'], 0.1)

    def test_repeatable_and_does_not_mutate_inputs(self):
        copies = [a.copy() for a in [self.rgb, self.depth, self.mask, self.guide]]
        a, b = self.run_form(), self.run_form()
        for x, y in [(a.rgb, b.rgb), (a.depth, b.depth), (a.map_x, b.map_x)]:
            np.testing.assert_array_equal(x, y)
        self.assertTrue(np.isfinite(a.depth).all())
        for original, current in zip(copies, [self.rgb, self.depth, self.mask, self.guide]):
            np.testing.assert_array_equal(original, current)

    def test_invalid_amount_and_nonfinite_depth_are_rejected(self):
        for value in [float('nan'), float('inf'), -1, 13]:
            with self.assertRaises(ValueError):
                self.run_form(value)
        self.depth[70, 100] = np.nan
        with self.assertRaises(ValueError):
            self.run_form()


if __name__ == '__main__':
    unittest.main()
