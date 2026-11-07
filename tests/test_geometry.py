import math
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image as PILImage
from PIL import ImageStat

from game.app import NeonFPS
from game.config import AMBIENTCG_DIR
from game.geometry import (
    create_gable_roof_mesh,
    create_ocean_mesh,
    create_shirt_front_mesh,
    create_sky_hemisphere_mesh,
)


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


class SkyHemisphereMeshTests(unittest.TestCase):
    def test_sky_mesh_covers_only_the_upper_hemisphere_and_uses_full_uv_range(self):
        longitude_segments = 64
        latitude_segments = 32
        sky = create_sky_hemisphere_mesh(
            radius=350,
            longitude_segments=longitude_segments,
            latitude_segments=latitude_segments,
        )

        self.assertEqual(
            len(sky.vertices),
            latitude_segments * (longitude_segments + 1) + longitude_segments,
        )
        self.assertEqual(
            len(sky.triangles),
            longitude_segments * (latitude_segments * 2 - 1),
        )
        self.assertAlmostEqual(min(vertex[1] for vertex in sky.vertices), 0)
        self.assertAlmostEqual(max(vertex[1] for vertex in sky.vertices), 350)
        self.assertEqual(min(uv[1] for uv in sky.uvs), 0)
        self.assertEqual(max(uv[1] for uv in sky.uvs), 1)


class ShirtFrontMeshTests(unittest.TestCase):
    def test_shirt_panel_follows_the_front_of_the_torso(self):
        shirt = create_shirt_front_mesh()

        self.assertEqual(len(shirt.vertices), 6)
        self.assertEqual(len(shirt.triangles), 4)
        self.assertAlmostEqual(min(vertex[0] for vertex in shirt.vertices), -0.18)
        self.assertAlmostEqual(max(vertex[0] for vertex in shirt.vertices), 0.18)
        self.assertAlmostEqual(min(vertex[1] for vertex in shirt.vertices), 0.98)
        self.assertAlmostEqual(max(vertex[1] for vertex in shirt.vertices), 1.48)
        self.assertTrue(all(vertex[2] > 0 for vertex in shirt.vertices))


class DisplacedBoxTests(unittest.TestCase):
    def test_surface_relief_adds_low_frequency_mesh_deformation(self):
        height_map = AMBIENTCG_DIR / "Plaster001_1K-JPG_Displacement.jpg"
        normal_map = AMBIENTCG_DIR / "Plaster001_1K-JPG_NormalGL.jpg"
        smooth = NeonFPS.create_displaced_box(
            height_map,
            normal_map,
            resolution=6,
        )
        irregular = NeonFPS.create_displaced_box(
            height_map,
            normal_map,
            resolution=6,
            surface_relief=0.012,
        )

        offsets = [
            math.dist(smooth.vertices[index], vertex)
            for index, vertex in enumerate(irregular.vertices)
        ]
        self.assertEqual(len(smooth.vertices), len(irregular.vertices))
        self.assertGreater(max(offsets), 0.001)
        self.assertLessEqual(max(offsets), 0.012)

    def test_surface_materials_enable_subtle_relief_for_every_environment_type(self):
        materials = (
            "asphalt",
            "paving",
            "concrete",
            "roofing",
            "plaster",
            "brick",
        )
        game = SimpleNamespace(
            material_shader=object(),
            material_maps={
                material: {"roughness": object()}
                for material in materials
            },
            fog_color=object(),
            fog_density=0.0,
            photo_mode=False,
            sky_texture=object(),
            pbr_entities=[],
        )
        relief_values = []
        reflection_values = []

        for material in materials:
            entity = SimpleNamespace(set_shader_input=Mock())
            NeonFPS.apply_surface_material(game, entity, material)
            shader_inputs = {
                call.args[0]: call.args[1]
                for call in entity.set_shader_input.call_args_list
            }
            relief_values.append(shader_inputs["mesh_relief"])
            reflection_values.append(shader_inputs["reflection_strength"])

        self.assertTrue(all(value > 0 for value in relief_values))
        self.assertEqual(reflection_values[0], 0.68)
        self.assertEqual(reflection_values[1], 0.50)
        self.assertGreater(reflection_values[0], reflection_values[-1])
        self.assertGreater(reflection_values[0], reflection_values[-2])
        self.assertEqual(len(game.pbr_entities), len(materials))

    def test_quality_mode_keeps_effects_static_until_mode_is_changed(self):
        entity = SimpleNamespace(set_shader_input=Mock())
        ao_quad = SimpleNamespace(setShaderInput=Mock())
        set_message = Mock()
        game = SimpleNamespace(
            photo_mode=False,
            sunlight=SimpleNamespace(shadows=False, update_bounds=Mock()),
            set_ambient_occlusion=Mock(),
            ao_available=True,
            ao_quad=ao_quad,
            shadow_bounds=object(),
            pbr_entities=[entity],
            ambient=SimpleNamespace(color=None),
            _apply_quality_effects=lambda: NeonFPS._apply_quality_effects(game),
            set_message=set_message,
        )

        NeonFPS.set_photo_mode(game, True)
        self.assertTrue(game.sunlight.shadows)
        game.set_ambient_occlusion.assert_called_once_with(True)
        self.assertEqual(ao_quad.setShaderInput.call_args.args, ("cinematic_enabled", 1.0))
        self.assertEqual(entity.set_shader_input.call_args.args, ("shadow_strength", 1.0))
        game.sunlight.update_bounds.assert_called_once_with(game.shadow_bounds)
        self.assertFalse(hasattr(NeonFPS, "update_quality_performance"))

        NeonFPS.set_photo_mode(game, False)
        self.assertFalse(game.sunlight.shadows)
        self.assertEqual(game.set_ambient_occlusion.call_args.args, (False,))
        self.assertEqual(ao_quad.setShaderInput.call_args.args, ("cinematic_enabled", 0.0))
        self.assertEqual(entity.set_shader_input.call_args.args, ("shadow_strength", 0.0))


class MilkyWaySkyTests(unittest.TestCase):
    def test_texture_uses_the_unsplash_image_on_the_upper_hemisphere_only(self):
        sky_path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "textures"
            / "milky_way_unsplash.jpg"
        )
        with PILImage.open(sky_path) as sky:
            self.assertEqual(sky.size, (4096, 2048))
            zenith = sky.crop((0, 0, sky.width, 1))
            self.assertLess(max(ImageStat.Stat(zenith).stddev), 5)
            upper_half = sky.crop((0, 0, sky.width, sky.height // 2))
            lower_half = sky.crop((0, sky.height // 2, sky.width, sky.height))
            self.assertGreater(min(ImageStat.Stat(upper_half).stddev), 20)
            self.assertGreater(min(ImageStat.Stat(lower_half).stddev), 20)

        with patch("game.app.Texture", side_effect=lambda texture: texture):
            textures = NeonFPS.create_textures()

        self.assertEqual(len(textures), 13)
        self.assertEqual(textures[-1], str(sky_path))


if __name__ == "__main__":
    unittest.main()
