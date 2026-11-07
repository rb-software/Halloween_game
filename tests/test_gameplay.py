import unittest
from types import SimpleNamespace
from unittest.mock import patch

from game.config import create_map
from game.gameplay import GameplayMixin


class GameplayMapTests(unittest.TestCase):
    def setUp(self):
        self.game = GameplayMixin()
        self.game.grid = create_map()
        self.game.map_height = len(self.game.grid)
        self.game.map_width = len(self.game.grid[0])

    def test_map_dimensions_and_closed_border(self):
        self.assertEqual((self.game.map_width, self.game.map_height), (35, 47))
        self.assertTrue(all(cell == "#" for cell in self.game.grid[0]))
        self.assertTrue(all(cell == "#" for cell in self.game.grid[-1]))
        self.assertTrue(all(row[0] == row[-1] == "#" for row in self.game.grid))

    def test_path_avoids_walls_and_reaches_destination(self):
        path = self.game.shortest_path((1, 2), (3, 2))

        self.assertEqual(path[-1], (3, 2))
        self.assertEqual(len(path), 2)
        self.assertTrue(all(not self.game.is_wall(x + 0.5, z + 0.5) for x, z in path))

    def test_path_rejects_wall_destination(self):
        self.assertEqual(self.game.shortest_path((1, 1), (0, 0)), [])

    def test_recenter_captured_mouse_resets_pointer_and_previous_position(self):
        self.game.mouse_captured = True
        self.game.app = SimpleNamespace(
            win=SimpleNamespace(has_pointer=lambda pointer: pointer == 0)
        )

        with patch("game.gameplay.mouse") as mouse:
            self.game.recenter_captured_mouse()

        self.assertEqual(mouse.position, (0, 0))
        self.assertEqual(mouse.prev_x, 0)
        self.assertEqual(mouse.prev_y, 0)

    def test_recenter_does_not_move_released_mouse(self):
        self.game.mouse_captured = False
        fake_mouse = SimpleNamespace(position="unchanged", prev_x=1, prev_y=1)

        with patch("game.gameplay.mouse", fake_mouse):
            self.game.recenter_captured_mouse()

        self.assertEqual(fake_mouse.position, "unchanged")
        self.assertEqual(fake_mouse.prev_x, 1)
        self.assertEqual(fake_mouse.prev_y, 1)


if __name__ == "__main__":
    unittest.main()
