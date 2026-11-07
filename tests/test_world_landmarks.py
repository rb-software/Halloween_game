import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from game.world_landmarks import WorldLandmarkBuilder


class LandmarkTests(unittest.TestCase):
    def setUp(self):
        self.builder = SimpleNamespace(
            displaced_concrete_model=object(),
            concrete_texture=object(),
            stone_texture=object(),
            metal_texture=object(),
            cone_model=object(),
            cylinder_model=object(),
            apply_surface_material=Mock(),
        )

    def test_tower_has_clock_and_rooftop_finial(self):
        with (
            patch("game.world_landmarks.Entity") as entity,
            patch("game.world_landmarks.Text") as text,
        ):
            WorldLandmarkBuilder.build_landmark(self.builder)

        self.assertTrue(
            any(
                call.kwargs.get("position") == (12.5, 19.88, 21.5)
                and call.kwargs.get("color") is not None
                for call in entity.call_args_list
            )
        )
        self.assertIn("XII", [call.kwargs["text"] for call in text.call_args_list])
        self.assertGreater(len(entity.call_args_list), 30)

    def test_police_car_uses_polish_radio_car_markings(self):
        with (
            patch("game.world_landmarks.Entity") as entity,
            patch("game.world_landmarks.Text") as text,
        ):
            WorldLandmarkBuilder.build_police_car(self.builder)

        labels = [call.kwargs["text"] for call in text.call_args_list]
        self.assertIn("POLICJA", labels)
        self.assertIn("RADIOWÓZ", labels)
        self.assertGreater(len(entity.call_args_list), 25)


if __name__ == "__main__":
    unittest.main()
