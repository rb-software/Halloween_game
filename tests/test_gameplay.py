import queue
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from game.config import NEIGHBOR_COUNT, create_map
from game.gameplay import GameplayMixin


class GameplayMapTests(unittest.TestCase):
    def setUp(self):
        self.game = GameplayMixin()
        self.game.grid = create_map()
        self.game.map_height = len(self.game.grid)
        self.game.map_width = len(self.game.grid[0])
        self.game.greeting_cooldowns = {}

    def test_map_dimensions_and_closed_border(self):
        self.assertEqual((self.game.map_width, self.game.map_height), (35, 47))
        self.assertTrue(all(cell == "#" for cell in self.game.grid[0]))
        self.assertTrue(all(cell == "#" for cell in self.game.grid[-1]))
        self.assertTrue(all(row[0] == row[-1] == "#" for row in self.game.grid))

    def test_game_spawns_twenty_neighbors(self):
        self.assertEqual(NEIGHBOR_COUNT, 20)
        self.game.player = SimpleNamespace(x=17.5, z=12.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]

        positions = self.game.random_neighbor_positions(NEIGHBOR_COUNT)

        self.assertEqual(len(positions), 20)
        self.assertEqual(len(set(positions)), 20)

    def test_twenty_neighbors_receive_distinct_reachable_patrol_targets(self):
        self.game.player = SimpleNamespace(x=17.5, z=12.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]
        rng = random.Random(42)
        with patch("game.gameplay.random.shuffle", side_effect=rng.shuffle):
            starts = self.game.random_neighbor_positions(NEIGHBOR_COUNT)
            self.game.guard_entities = [
                {
                    "x": x,
                    "z": z,
                    "patrol_target": (int(x), int(z)),
                }
                for x, z in starts
            ]

            for index, guard in enumerate(self.game.guard_entities):
                guard["patrol_target"] = self.game.choose_guard_patrol_target(index)

        targets = [guard["patrol_target"] for guard in self.game.guard_entities]
        self.assertEqual(len(set(targets)), NEIGHBOR_COUNT)
        self.assertTrue(
            all(not self.game.is_wall(x + 0.5, z + 0.5) for x, z in targets)
        )

    def test_path_avoids_walls_and_reaches_destination(self):
        path = self.game.shortest_path((1, 2), (3, 2))

        self.assertEqual(path[-1], (3, 2))
        self.assertEqual(len(path), 2)
        self.assertTrue(all(not self.game.is_wall(x + 0.5, z + 0.5) for x, z in path))

    def test_path_rejects_wall_destination(self):
        self.assertEqual(self.game.shortest_path((1, 1), (0, 0)), [])

    def test_neighbors_continue_moving_when_their_paths_cross(self):
        guards = [
            {
                "x": 10.25,
                "z": 10.5,
                "root": SimpleNamespace(position=None, rotation_y=0),
                "head": SimpleNamespace(rotation_y=0),
                "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
                "greeting_bubble": SimpleNamespace(enabled=False),
                "greeting_until": 0.0,
                "path": [(11, 10)],
                "repath_at": 100.0,
                "patrol_target": (11, 10),
                "phase": 0,
                "speed": 1.0,
                "chase_speed": 1.0,
                "chase_radius": 0,
                "model_controlled": False,
            },
            {
                "x": 10.75,
                "z": 10.5,
                "root": SimpleNamespace(position=None, rotation_y=0),
                "head": SimpleNamespace(rotation_y=0),
                "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
                "greeting_bubble": SimpleNamespace(enabled=False),
                "greeting_until": 0.0,
                "path": [(10, 10)],
                "repath_at": 100.0,
                "patrol_target": (10, 10),
                "phase": 0,
                "speed": 1.0,
                "chase_speed": 1.0,
                "chase_radius": 0,
                "model_controlled": False,
            },
        ]
        initial_positions = [(guard["x"], guard["z"]) for guard in guards]
        self.game.guard_entities = guards
        self.game.player = SimpleNamespace(x=1.5, z=1.5)
        self.game.ai_results = queue.Queue()
        self.game.ai_generation = 0

        self.game.update_guard(0.05, 0.0)

        self.assertGreater(guards[0]["x"], initial_positions[0][0])
        self.assertLess(guards[1]["x"], initial_positions[1][0])

    def test_chasing_neighbor_moves_when_sharing_players_map_cell(self):
        guard = {
            "x": 20.9,
            "z": 20.5,
            "root": SimpleNamespace(position=None, rotation_y=0),
            "head": SimpleNamespace(rotation_y=0),
            "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
            "greeting_bubble": SimpleNamespace(enabled=False),
            "greeting_until": 0.0,
            "path": [],
            "repath_at": 100.0,
            "patrol_target": (20, 20),
            "phase": 0,
            "speed": 1.0,
            "chase_speed": 1.0,
            "chase_radius": 4.5,
            "model_controlled": False,
        }
        self.game.guard_entities = [guard]
        self.game.player = SimpleNamespace(x=20.1, z=20.5)
        self.game.ai_results = queue.Queue()
        self.game.ai_generation = 0

        self.game.update_guard(0.05, 0.0)

        self.assertLess(guard["x"], 20.9)

    def test_random_neighbor_positions_are_walkable_and_spread_out(self):
        self.game.player = SimpleNamespace(x=17.5, z=12.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]

        positions = self.game.random_neighbor_positions(4)

        self.assertEqual(len(set(positions)), 4)
        for x, z in positions:
            self.assertFalse(self.game.is_wall(x, z))
            self.assertGreaterEqual(((x - 17.5) ** 2 + (z - 12.5) ** 2) ** 0.5, 4)

    def test_patrol_target_selection_can_reach_the_forest(self):
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]
        self.game.guard_entities = [
            {
                "x": 5.5,
                "z": 5.5,
                "patrol_target": (5, 5),
            }
        ]

        with patch("game.gameplay.random.choice", side_effect=lambda cells: cells[-1]):
            target = self.game.choose_guard_patrol_target(0)

        self.assertGreaterEqual(target[1], 27)

    def test_only_one_neighbor_chases_the_player_at_a_time(self):
        guards = []
        for index, z in enumerate((23.5, 24.5, 25.5)):
            guards.append(
                {
                    "x": 20.5,
                    "z": z,
                    "root": SimpleNamespace(position=None, rotation_y=0),
                    "head": SimpleNamespace(rotation_y=0),
                    "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
                    "greeting_bubble": SimpleNamespace(enabled=False),
                    "greeting_until": 0.0,
                    "path": [],
                    "repath_at": 0.0,
                    "patrol_target": ((2 + index * 10), 2),
                    "phase": 0,
                    "speed": 1.0,
                    "chase_speed": 1.0,
                    "chase_radius": 4.5,
                    "model_controlled": False,
                }
            )
        self.game.guard_entities = guards
        self.game.player = SimpleNamespace(x=20.5, z=20.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]
        self.game.ai_results = queue.Queue()
        self.game.ai_generation = 0

        self.game.update_guard(0.05, 0.0)

        player_goal_count = sum(
            path[-1] == (20, 20)
            for path in (guard["path"] for guard in guards)
            if path
        )
        self.assertEqual(player_goal_count, 1)

    def test_passing_neighbors_show_hi_over_both_characters(self):
        guards = [
            {
                "x": 4.0,
                "z": 8.0,
                "greeting_bubble": SimpleNamespace(enabled=False),
                "greeting_until": 0.0,
            },
            {
                "x": 5.0,
                "z": 8.0,
                "greeting_bubble": SimpleNamespace(enabled=False),
                "greeting_until": 0.0,
            },
        ]
        self.game.guard_entities = guards

        self.game.update_neighbor_greetings(10.0)

        self.assertTrue(all(guard["greeting_bubble"].enabled for guard in guards))
        self.assertEqual(
            [guard["greeting_until"] for guard in guards],
            [11.5, 11.5],
        )
        self.game.update_neighbor_greetings(11.0)
        self.assertTrue(all(guard["greeting_bubble"].enabled for guard in guards))
        self.game.update_neighbor_greetings(11.5)
        self.assertTrue(all(not guard["greeting_bubble"].enabled for guard in guards))

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
