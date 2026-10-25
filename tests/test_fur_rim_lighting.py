"""Rim lighting changes colour locally, without changing coverage or geometry."""
import unittest
import numpy as np
from fur_rim_lighting import rim_light_maps, shade_rim_strand
from fur_strokes import FineFurCanvas


class RimLightingTests(unittest.TestCase):
    def setUp(self):
        y, x = np.mgrid[:181, :201]
        self.opening = ((x-100)/76)**2+((y-60)/32)**2 <= 1
        self.mask = ((x>14)&(x<187)&(y>20)&(y<170))
        ellipse = ((x-100)/76)**2+((y-60)/32)**2
        self.depth = (0.7-0.25*np.clip(1-ellipse, 0, 1)).astype(np.float32)
        self.light = [-0.4, 0, 0.92]

    def maps(self, light=0.25, shadow=0.28, direction=None, depth=None):
        return rim_light_maps(self.depth if depth is None else depth, self.mask,
                              self.opening, self.light if direction is None else direction,
                              light, shadow)

    def test_noop_repeatability_and_inputs_unchanged(self):
        copies = [v.copy() for v in (self.depth, self.mask, self.opening)]
        np.testing.assert_array_equal(self.maps(0, 0).gain, np.ones_like(self.depth))
        np.testing.assert_array_equal(self.maps().gain, self.maps().gain)
        for before, after in zip(copies, (self.depth, self.mask, self.opening)):
            np.testing.assert_array_equal(before, after)

    def test_shadow_only_on_recessed_wall_and_outer_body_is_untouched(self):
        result = self.maps()
        self.assertGreater(float(result.shadow.max()), 0.5)
        self.assertEqual(np.count_nonzero(result.shadow[~self.opening]), 0)
        np.testing.assert_array_equal(self.maps(depth=np.full_like(self.depth, 0.7)).shadow,
                                      np.zeros_like(self.depth))
        np.testing.assert_array_equal(result.gain[~self.mask], np.ones((~self.mask).sum()))
        np.testing.assert_array_equal(result.gain[125:], np.ones_like(result.gain[125:]))
        self.assertEqual(float(result.shadow[60, 100]), 0)
        self.assertGreaterEqual(float(result.gain.min()), 0.72-1e-6)
        self.assertLessEqual(float(result.gain.max()), 1.25+1e-6)

    def test_light_direction_moves_bright_side_and_shadow(self):
        a = self.maps(direction=[-0.4, 0, 0.92])
        b = self.maps(direction=[0.4, 0, 0.92])
        np.testing.assert_allclose(a.highlight[:, ::-1], b.highlight, atol=2e-6)
        # Float32 remap/gradient rounding may differ by a few millionths.
        np.testing.assert_allclose(a.shadow[:, ::-1], b.shadow, atol=1e-5)
        self.assertGreater(float(a.highlight[:, :100].sum()), float(a.highlight[:, 101:].sum()))

    def test_same_hairs_retain_alpha_and_coherent_colour_detail(self):
        colors = np.tile([0.50, 0.30, 0.15], (12, 1)).astype(np.float32)
        hair = np.stack([np.linspace(30, 45, 13),np.linspace(45, 47, 13),np.ones(13)],axis=1).astype(np.float32)
        source = np.full((181, 201, 3), 0.8, np.float32)
        before, after = (FineFurCanvas(source, self.mask) for _ in range(2))
        for i in range(1, 20):
            before.draw_strand(hair, colors, i)
            after.draw_strand(hair, shade_rim_strand(colors, 1.2), i)
        rgb0,a0=before.finish();rgb1,a1=after.finish()
        np.testing.assert_array_equal(a0,a1)
        np.testing.assert_array_equal(rgb0[a0==0],rgb1[a0==0])
        np.testing.assert_allclose(shade_rim_strand(colors, .8), colors*.8, atol=1e-7)
        bright=shade_rim_strand(np.array([[.98,.7,.1]],np.float32),1.5)
        self.assertLessEqual(float(bright.max()),1)
        self.assertAlmostEqual(float(bright[0,0]/bright[0,2]),9.8,places=5)

    def test_invalid_parameters_fail_clearly(self):
        for value in [float('nan'), float('inf'), -0.1, 0.6]:
            with self.assertRaises(ValueError):
                self.maps(light=value)
            with self.assertRaises(ValueError):
                self.maps(shadow=value)
        for direction in [[0,0,0],[1,0], [float('nan'),0,1]]:
            with self.assertRaises(ValueError):
                self.maps(direction=direction)
        with self.assertRaises(ValueError):
            self.maps(depth=self.depth[:10])
        self.depth[50,50]=np.nan
        with self.assertRaises(ValueError):
            self.maps()


if __name__ == '__main__':
    unittest.main()
