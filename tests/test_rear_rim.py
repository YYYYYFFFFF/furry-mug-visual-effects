"""Rear-lip fibres must extend coverage without disturbing the accepted cup."""
import unittest
import cv2
import numpy as np
from fur_rim import apply_rear_rim_fringe


class RearRimTests(unittest.TestCase):
    def setUp(self):
        self.mask = np.zeros((200, 200), np.uint8)
        cv2.ellipse(self.mask, (100, 60), (70, 30), 0, 0, 360, 1, -1)
        self.mask[60:180, 30:171] = 1
        self.guide = np.zeros_like(self.mask)
        cv2.ellipse(self.guide, (100, 60), (65, 25), 0, 0, 360, 1, -1)
        self.image = np.full((200, 200, 3), 230, np.uint8)
        self.image[self.mask > 0] = [135, 105, 70]
        self.source = self.image.astype(np.float32) / 255

    def test_new_coverage_extends_beyond_old_silhouette_but_is_local(self):
        result, alpha, support, count = apply_rear_rim_fringe(
            self.image, self.source, self.mask, self.guide)
        self.assertGreater(count, 0)
        exterior = (self.mask == 0) & (alpha > 0.01)
        self.assertTrue(exterior.any())
        self.assertTrue(np.any(result[exterior] != self.image[exterior]))
        np.testing.assert_array_equal(result[support == 0], self.image[support == 0])
        np.testing.assert_array_equal(result[60:], self.image[60:])
        self.assertFalse(alpha[60:].any())
        self.assertTrue(np.isfinite(alpha).all())
        self.assertTrue(np.all((alpha >= 0) & (alpha <= 0.85)))

    def test_disabled_fringe_is_byte_identical(self):
        result, alpha, _, count = apply_rear_rim_fringe(
            self.image, self.source, self.mask, self.guide, strength=0)
        np.testing.assert_array_equal(result, self.image)
        self.assertEqual(count, 0)
        self.assertFalse(alpha.any())


if __name__ == '__main__':
    unittest.main()
