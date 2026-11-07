import unittest
from types import SimpleNamespace
from unittest.mock import patch

from game.world_nature import WorldNatureBuilder


class OceanShipTests(unittest.TestCase):
    def test_ocean_has_three_ships_outside_the_playable_shore(self):
        game = SimpleNamespace(
            cylinder_model=object(),
            wood_texture=object(),
        )

        with patch("game.world_nature.Entity") as entity:
            WorldNatureBuilder.build_ocean_ships(game)

        self.assertEqual(len(game.ocean_ships), 3)
        self.assertTrue(all(ship["z"] < 0 for ship in game.ocean_ships))
        hulls = [
            call
            for call in entity.call_args_list
            if len(getattr(call.kwargs.get("model"), "vertices", ())) > 5
        ]
        sails = [
            call
            for call in entity.call_args_list
            if len(getattr(call.kwargs.get("model"), "vertices", ())) == 3
        ]
        self.assertEqual(len(hulls), 3)
        self.assertEqual(len(sails), 6)
        vertices = hulls[0].kwargs["model"].vertices
        bow_width = max(abs(vertex[2]) for vertex in vertices if vertex[0] == -2.5)
        body_width = max(abs(vertex[2]) for vertex in vertices if vertex[0] == 1.55)
        self.assertLess(bow_width, body_width)

    def test_ships_bob_and_drift_over_time(self):
        entity = SimpleNamespace(
            x=0,
            y=0,
            z=0,
            rotation_z=0,
            rotation_y=0,
        )
        ship = {
            "entity": entity,
            "x": 5.5,
            "y": 0.12,
            "z": -12.0,
            "heading": -12,
            "phase": 0,
            "speed": 0.42,
            "direction": 1,
            "roll": -1,
        }
        game = SimpleNamespace(ocean_ships=[ship])

        WorldNatureBuilder.update_ocean_ships(game, 0.0)
        initial_position = (entity.x, entity.y, entity.z)
        WorldNatureBuilder.update_ocean_ships(game, 2.0)

        self.assertNotEqual(
            (entity.x, entity.y, entity.z),
            initial_position,
        )
        self.assertNotEqual(entity.rotation_z, 0)
        self.assertNotEqual(entity.rotation_y, ship["heading"])


if __name__ == "__main__":
    unittest.main()
