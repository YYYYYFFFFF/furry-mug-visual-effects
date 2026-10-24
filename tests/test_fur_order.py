"""Depth ordering must preserve strand attributes and actual overlap behaviour."""
import unittest
import numpy as np
from fur_strokes import FineFurCanvas, depth_ordered_strands


class FurOrderTests(unittest.TestCase):
    def records(self):
        near = np.array([[4, 16, 9], [28, 16, 9]], np.float32)
        far = np.array([[16, 4, 2], [16, 28, 2]], np.float32)
        return [(near, np.array([[0.9, 0.1, 0.1]], np.float32), 7),
                (far, np.array([[0.1, 0.1, 0.9]], np.float32), 19)]

    def render(self, records):
        image = np.ones((32, 32, 3), np.float32)
        canvas = FineFurCanvas(image, np.ones((32, 32), np.uint8))
        for hair, color, original_index in depth_ordered_strands(records):
            canvas.draw_strand(hair, color, original_index)
        return canvas.finish()

    def test_nearer_red_fibre_covers_farther_blue_regardless_of_input_order(self):
        records = self.records()
        rgb, alpha = self.render(records)
        reversed_rgb, reversed_alpha = self.render(records[::-1])
        np.testing.assert_array_equal(rgb, reversed_rgb)
        np.testing.assert_array_equal(alpha, reversed_alpha)
        self.assertGreater(rgb[16, 16, 0], rgb[16, 16, 2])



if __name__ == '__main__':
    unittest.main()
