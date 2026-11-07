import unittest

from game.geometry import create_gable_roof_mesh, create_ocean_mesh


class GableRoofMeshTests(unittest.TestCase):
    def test_roof_has_two_slopes_and_respects_dimensions(self):
        width, depth, height, thickness = 3.42, 2.12, 0.86, 0.14
        roof = create_gable_roof_mesh(width, depth, height, thickness)

        self.assertEqual(len(roof.vertices), 16)
        self.assertEqual(len(roof.triangles), 20)
        self.assertAlmostEqual(min(vertex[0] for vertex in roof.vertices), -width / 2)
        self.assertAlmostEqual(max(vertex[0] for vertex in roof.vertices), width / 2)
        self.assertAlmostEqual(min(vertex[2] for vertex in roof.vertices), -depth / 2)
        self.assertAlmostEqual(max(vertex[2] for vertex in roof.vertices), depth / 2)
        self.assertAlmostEqual(min(vertex[1] for vertex in roof.vertices), -thickness)
        self.assertAlmostEqual(max(vertex[1] for vertex in roof.vertices), height)
        for triangle in roof.triangles[:2] + roof.triangles[10:12]:
            first, second, third = (roof.vertices[index] for index in triangle)
            edge_a = tuple(second[index] - first[index] for index in range(3))
            edge_b = tuple(third[index] - first[index] for index in range(3))
            normal_y = edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2]
            self.assertGreater(normal_y, 0)


class OceanMeshTests(unittest.TestCase):
    def test_ocean_mesh_uses_coarse_grid_for_shader_waves(self):
        segments = 48
        ocean = create_ocean_mesh(185, 150)

        self.assertEqual(len(ocean.vertices), (segments + 1) ** 2)
        self.assertEqual(len(ocean.triangles), segments**2 * 2)


if __name__ == "__main__":
    unittest.main()
