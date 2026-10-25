"""Interior relief must not flatten the lip, move the silhouette or expose holes."""
import unittest
import cv2
import numpy as np
from fur_cavity import refine_cavity


class CavityTests(unittest.TestCase):
    def setUp(self):
        self.mask = np.zeros((200, 240), np.uint8)
        cv2.rectangle(self.mask, (30, 25), (210, 185), 1, -1)
        self.opening = np.zeros_like(self.mask)
        cv2.ellipse(self.opening, (120, 65), (75, 30), 0, 0, 360, 1, -1)
        self.depth = np.full(self.mask.shape, 0.5, np.float32)

    def test_noop_is_exact_and_does_not_mutate_inputs(self):
        copies = [x.copy() for x in (self.depth, self.mask, self.opening)]
        result = refine_cavity(self.depth, self.mask, self.opening)
        np.testing.assert_array_equal(result.depth, self.depth)
        np.testing.assert_array_equal(result.length_scale, np.ones_like(self.depth))
        refine_cavity(self.depth, self.mask, self.opening, 0.055, 0.6)
        for original, current in zip(copies, (self.depth, self.mask, self.opening)):
            np.testing.assert_array_equal(original, current)

    def test_recedes_smoothly_only_beyond_the_protected_lip(self):
        result = refine_cavity(self.depth, self.mask, self.opening, 0.055, 0.6)
        distance = cv2.distanceTransform(self.opening, cv2.DIST_L2, 5)
        protected = distance <= result.diagnostics['protected_lip_px']
        np.testing.assert_array_equal(result.depth[protected], self.depth[protected])
        np.testing.assert_array_equal(result.length_scale[protected], np.ones(protected.sum()))
        self.assertLess(result.depth[65, 120], 0.45)
        self.assertAlmostEqual(float(result.length_scale[65, 120]), 0.6, places=6)
        self.assertTrue(np.all(np.diff(result.depth[37:66, 120]) <= 1e-6))
        self.assertLess(float(np.abs(np.diff(result.depth, axis=0)).max()), 0.005)

    def test_depth_and_pile_controls_can_be_isolated(self):
        short = refine_cavity(self.depth, self.mask, self.opening, 0, 0.6)
        relief = refine_cavity(self.depth, self.mask, self.opening, 0.055, 1)
        np.testing.assert_array_equal(short.depth, self.depth)
        np.testing.assert_array_equal(relief.length_scale, np.ones_like(self.depth))
        self.assertGreater(float(relief.recession.max()), 0.05)
        self.assertGreater(short.diagnostics['shortened_surface_pixels'], 0)

    def test_clips_to_object_and_limits_recession_without_negative_depth(self):
        self.mask[:, :120] = 0
        self.depth[:] = 0.01
        result = refine_cavity(self.depth, self.mask, self.opening, 0.12, 0.6)
        np.testing.assert_array_equal(result.depth[:, :120], self.depth[:, :120])
        self.assertTrue(np.isfinite(result.depth).all())
        self.assertGreater(float(result.depth.min()), 0)
        self.assertLessEqual(float(result.depth.max()), 1)
        a = refine_cavity(self.depth, self.mask, self.opening, 0.12, 0.6)
        np.testing.assert_array_equal(a.depth, result.depth)

    def test_invalid_settings_and_guides_fail_clearly(self):
        for amount, length in [(float('nan'), 0.6), (0.13, 0.6), (-1, 1),
                               (0.05, float('inf')), (0.05, 0), (0.05, 1.1)]:
            with self.assertRaises(ValueError):
                refine_cavity(self.depth, self.mask, self.opening, amount, length)
        with self.assertRaises(ValueError):
            refine_cavity(self.depth, self.mask, np.zeros_like(self.opening), 0.05, 0.6)
        with self.assertRaises(ValueError):
            refine_cavity(self.depth[:, :10], self.mask, self.opening, 0.05, 0.6)
        self.depth[65, 120] = np.nan
        with self.assertRaises(ValueError):
            refine_cavity(self.depth, self.mask, self.opening, 0.05, 0.6)


if __name__ == '__main__':
    unittest.main()
