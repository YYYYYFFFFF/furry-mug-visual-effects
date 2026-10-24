"""Lighting must add coherent detail without changing coverage or colour hue."""
import unittest
import numpy as np
from fur_lighting import shade_strand_detail
from fur_strokes import FineFurCanvas


class StrandLightingTests(unittest.TestCase):
    def setUp(self):
        self.hair = np.stack([np.linspace(12, 32, 13),
                              np.linspace(15, 18, 13), np.ones(13)], axis=1).astype(np.float32)
        self.colors = np.tile([0.5, 0.3, 0.15], (12, 1)).astype(np.float32)
        self.light = np.array([0, 0, 1], np.float32)

    def shade(self, index=1, contrast=0, highlight=0, normal=None, colors=None):
        return shade_strand_detail(self.hair, self.colors if colors is None else colors,
                                   index, self.light, self.light if normal is None else normal,
                                   contrast, highlight)

    def test_disabled_identity_and_deterministic_coherent_variation(self):
        np.testing.assert_array_equal(self.shade(), self.colors)
        gains = []
        for index in range(512):
            changed = self.shade(index, contrast=0.12)
            np.testing.assert_array_equal(changed, self.shade(index, contrast=0.12))
            ratios = changed / self.colors
            np.testing.assert_allclose(ratios, np.full_like(ratios, ratios[0, 0]), atol=1e-6)
            gains.append(float(ratios[0, 0]))
        self.assertGreater(np.std(gains), 0.06)
        self.assertLess(abs(np.mean(gains) - 1), 0.01)
        self.assertTrue(all(0.879 <= g <= 1.121 for g in gains))

    def test_highlight_is_sparse_directional_and_fades_at_tip(self):
        selected = [i for i in range(100) if np.any(self.shade(i, highlight=0.1) > self.colors)]
        self.assertTrue(15 <= len(selected) <= 45)
        i = selected[0]
        lit = self.shade(i, highlight=0.1)
        np.testing.assert_array_equal(self.shade(i, highlight=0.1, normal=-self.light), self.colors)
        np.testing.assert_array_equal(lit[-1], self.colors[-1])
        self.assertTrue(np.all(lit >= self.colors))
        self.assertLessEqual(float(np.max(lit / self.colors)), 1.10001)

    def test_same_geometry_keeps_exact_alpha_and_background(self):
        mask = np.zeros((48, 48), np.uint8)
        mask[10:40, 10:40] = 1
        source = np.full((48, 48, 3), 0.8, np.float32)
        before, after = (FineFurCanvas(source, mask) for _ in range(2))
        original_hair, original_colors = self.hair.copy(), self.colors.copy()
        for i in range(1, 30):
            before.draw_strand(self.hair, self.colors, i)
            after.draw_strand(self.hair, self.shade(i, contrast=0.12, highlight=0.1), i)
        rgb0, a0 = before.finish()
        rgb1, a1 = after.finish()
        np.testing.assert_array_equal(a0, a1)
        np.testing.assert_array_equal(rgb0[a0 == 0], rgb1[a0 == 0])
        self.assertTrue(np.any(rgb0 != rgb1))
        np.testing.assert_array_equal(self.hair, original_hair)
        np.testing.assert_array_equal(self.colors, original_colors)

    def test_bright_colours_preserve_channel_ratios_without_clipping(self):
        colors = np.tile([0.99, 0.7, 0.1], (12, 1)).astype(np.float32)
        for i in range(100):
            shaded = self.shade(i, contrast=0.4, highlight=0.3, colors=colors)
            self.assertTrue(np.isfinite(shaded).all())
            self.assertTrue(np.all((shaded >= 0) & (shaded <= 1)))
            np.testing.assert_allclose(shaded[:, 0] / shaded[:, 2], 9.9, atol=2e-6)


if __name__ == '__main__':
    unittest.main()
