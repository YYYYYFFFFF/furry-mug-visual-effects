"""Small rendering invariants; no model weights or inference required."""
import unittest

import cv2
import numpy as np

from fur_strokes import FineFurCanvas, repair_aa_color


class FurStrokeTests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((32, 32, 3), [0.2, 0.7, 0.9], np.float32)
        self.mask = np.zeros((32, 32), np.uint8)
        self.mask[:, :16] = 1
        self.hair = np.column_stack([
            np.linspace(6, 27, 13), np.full(13, 15.0), np.zeros(13)
        ]).astype(np.float32)
        self.colors = np.tile([0.8, 0.4, 0.2], (12, 1)).astype(np.float32)

    def render(self, tint=0, hair=None, colors=None):
        canvas = FineFurCanvas(self.image, self.mask, environment_blend=tint)
        canvas.draw_strand(self.hair if hair is None else hair,
                           self.colors if colors is None else colors, 5)
        return canvas.finish()

    def test_white_aa_line_on_white_background_has_no_dark_fringe(self):
        alpha = np.zeros((32, 32), np.uint8)
        cv2.line(alpha, (4, 3), (19, 25), 255, 1, cv2.LINE_AA)
        a = alpha.astype(np.float32) / 255
        rgb = np.repeat(a[..., None], 3, axis=2)
        corrected = repair_aa_color(rgb, a)
        composite = (1 - a[..., None]) + corrected * a[..., None]
        np.testing.assert_allclose(composite, 1, atol=1e-6)

    def test_fine_color_survives_partial_coverage_and_tip_fades(self):
        rgb, alpha = self.render()
        np.testing.assert_allclose(rgb[alpha > 1e-4],
                                   np.broadcast_to(self.colors[0], rgb[alpha > 1e-4].shape), atol=1e-5)
        self.assertGreater(alpha[:, 8:12].sum(), alpha[:, 23:27].sum())
        white, coverage = self.render(colors=np.ones_like(self.colors))
        np.testing.assert_allclose(1 - coverage[..., None] + white * coverage[..., None], 1, atol=1e-6)

    def test_environment_tint_only_changes_exterior_color(self):
        plain, alpha = self.render()
        tinted, tinted_alpha = self.render(tint=0.12)
        np.testing.assert_array_equal(alpha, tinted_alpha)
        np.testing.assert_array_equal(plain[self.mask > 0], tinted[self.mask > 0])
        self.assertTrue(np.any(plain[self.mask == 0] != tinted[self.mask == 0]))

    def test_internal_hair_does_not_sample_object_as_environment(self):
        hair = self.hair.copy()
        hair[:, 0] = np.linspace(3, 12, len(hair))
        plain, alpha = self.render(hair=hair)
        tinted, tinted_alpha = self.render(tint=0.12, hair=hair)
        np.testing.assert_array_equal(plain, tinted)
        np.testing.assert_array_equal(alpha, tinted_alpha)


if __name__ == '__main__':
    unittest.main()
