import unittest

import numpy as np
from ospgrillage.utils import solve_zeta_eta


class NaturalCoordinates(unittest.TestCase):
    def test_inverse_matches_independent_forward_mapping(self):
        for corners in (
            [(0, 0), (3, 0), (3.5, 2), (0.2, 2)],
            [(1, 1), (2, 3), (4, 3), (4.5, 1)],
            [(0, 0), (2, -0.1), (2.4, 2), (0.3, 2.1)],
        ):
            for u, v in ((0, 0), (1, -1), (-1, 1), (0.3, -0.4)):
                with self.subTest(corners=corners, u=u, v=v):
                    weights = np.array([(1-u)*(1-v), (1+u)*(1-v), (1+u)*(1+v), (1-u)*(1+v)]) / 4
                    point = weights @ np.array(corners)
                    coords = solve_zeta_eta(*point, *np.ravel(corners))
                    np.testing.assert_allclose(coords, (u, v), atol=1e-12)
