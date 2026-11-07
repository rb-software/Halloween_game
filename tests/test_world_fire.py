import math
import unittest
from types import SimpleNamespace

from game.config import CAMPFIRE_POSITION
from game.world_fire import WorldFireBuilder


class CampfireAmbienceTests(unittest.TestCase):
    def test_fireflies_move_and_change_brightness_over_time(self):
        glow = SimpleNamespace(position=None, scale=0, color=None)
        orb = SimpleNamespace(position=None, scale=0, color=None)
        firefly = {
            "glow": glow,
            "orb": orb,
            "radius_x": 2.5,
            "radius_z": 2.0,
            "height": 1.4,
            "phase": 0.7,
            "speed": 0.6,
            "drift": 0.9,
        }
        game = SimpleNamespace(
            campfire_fireflies=[firefly],
        )

        WorldFireBuilder.update_campfire_ambience(game, 0.0)
        first_position = glow.position
        first_scale = glow.scale
        first_color = glow.color
        WorldFireBuilder.update_campfire_ambience(game, 1.0)

        self.assertAlmostEqual(
            first_position[0],
            CAMPFIRE_POSITION[0] + math.cos(firefly["phase"]) * firefly["radius_x"],
        )
        self.assertNotEqual(glow.position, first_position)
        self.assertNotEqual(glow.scale, first_scale)
        self.assertNotEqual(glow.color, first_color)
        self.assertEqual(glow.position, orb.position)


if __name__ == "__main__":
    unittest.main()
