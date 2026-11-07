import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from game.config import PACKAGE_RETURN_POSITION, PACKAGE_RETURN_RADIUS
from game.world_city import WorldCityBuilder


class PlazaTests(unittest.TestCase):
    def test_plaza_has_no_christmas_tree_or_grass_decoration(self):
        game = SimpleNamespace(
            paving_model=object(),
            paving_texture=object(),
            concrete_texture=object(),
            wood_texture=object(),
            metal_texture=object(),
            cone_model=object(),
            apply_surface_material=Mock(),
        )

        with (
            patch("game.world_city.Entity") as entity,
            patch("game.world_city.Text") as text,
        ):
            WorldCityBuilder.build_plaza(game)

        self.assertFalse(
            any(
                call.kwargs.get("model") in (game.cone_model, "sphere")
                or call.kwargs.get("texture") == "grass"
                for call in entity.call_args_list
            )
        )
        station = next(
            call
            for call in entity.call_args_list
            if call.kwargs.get("name") == "package_return_station"
        )
        self.assertEqual(station.kwargs["position"], (6.0, 0, 5.0))
        zone = next(
            call
            for call in entity.call_args_list
            if call.kwargs.get("name") == "package_return_zone"
        )
        self.assertEqual(
            zone.kwargs["position"],
            (*PACKAGE_RETURN_POSITION[:1], 0.035, PACKAGE_RETURN_POSITION[1]),
        )
        self.assertEqual(
            max(
                (x * x + z * z) ** 0.5
                for x, _, z in zone.kwargs["model"].vertices
            ),
            PACKAGE_RETURN_RADIUS,
        )
        self.assertEqual(text.call_args.kwargs["text"], "PACKAGE\nRETURN")


if __name__ == "__main__":
    unittest.main()
