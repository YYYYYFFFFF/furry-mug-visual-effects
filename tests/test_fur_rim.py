"""Rim finishing must respect the accepted appearance outside its local band."""
import unittest
import cv2
import numpy as np
from fur_rim import apply_rim_detail, rim_band


class RimDetailTests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((96, 128, 3), [145, 111, 75], np.uint8)
        self.guide = np.zeros((96, 128), np.uint8)
        cv2.ellipse(self.guide, (64, 35), (40, 15), 0, 0, 360, 1, -1)
        self.coverage = np.ones((96, 128), np.float32)
        self.coverage[:, :15] = 0

    def test_detail_preserves_all_pixels_outside_the_feathered_rim(self):
        result, alpha, support, count = apply_rim_detail(
            self.image, self.guide, self.coverage)
        self.assertGreater(count, 0)
        self.assertTrue(np.any(result != self.image))
        np.testing.assert_array_equal(result[support == 0], self.image[support == 0])
        np.testing.assert_array_equal(result[60:], self.image[60:])  # body
        np.testing.assert_array_equal(result[35, 64], self.image[35, 64])  # deep opening
        self.assertTrue(np.all(alpha[self.coverage == 0] == 0))
        self.assertTrue(np.all((alpha >= 0) & (alpha <= 0.75)))

    def test_zero_strength_is_an_exact_no_op_and_guide_must_be_valid(self):
        result, alpha, _, count = apply_rim_detail(
            self.image, self.guide, self.coverage, strength=0)
        np.testing.assert_array_equal(result, self.image)
        self.assertEqual(count, 0)
        self.assertFalse(alpha.any())
        with self.assertRaises(ValueError):
            rim_band(np.ones((96, 128), bool), self.coverage)
        with self.assertRaises(ValueError):
            rim_band(self.guide[:20], self.coverage)


if __name__ == '__main__':
    unittest.main()
