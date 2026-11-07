import math
import queue
import random
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from game.config import (
    GUARD_COUNT,
    NEIGHBOR_CHASE_SPEED_MULTIPLIER,
    NEIGHBOR_COUNT,
    OFFICER_COUNT,
    OFFICER_SALUTE_RADIUS,
    PACKAGE_RETURN_POSITION,
    PACKAGE_RETURN_RADIUS,
    PLAYER_START,
    PLAZA_CENTER,
    POLICE_CAR_POSITION,
    SNACK_COUNT,
    SNACK_MIN_SPACING,
    SUPER_PACKAGE_DURATION,
    SUPER_PACKAGE_SPEED_MULTIPLIER,
    create_map,
)
from game.gameplay import GameplayMixin


class GameplayMapTests(unittest.TestCase):
    def setUp(self):
        self.game = GameplayMixin()
        self.game.grid = create_map()
        self.game.map_height = len(self.game.grid)
        self.game.map_width = len(self.game.grid[0])
        self.game.greeting_cooldowns = {}
        self.game.guard_entities = []
        self.game.snacks = []
        self.game.neighbor_treats_returned = 0
        self.game.speed_boost_pickup = None
        self.game.player_speed_boost_until = 0.0
        self.game.candy_count = 0
        self.game.bag_capacity = 5
        self.game.officer_next_salute_at = math.inf

    def test_map_dimensions_and_closed_border(self):
        self.assertEqual((self.game.map_width, self.game.map_height), (35, 47))
        self.assertTrue(all(cell == "#" for cell in self.game.grid[0]))
        self.assertTrue(all(cell == "#" for cell in self.game.grid[-1]))
        self.assertTrue(all(row[0] == row[-1] == "#" for row in self.game.grid))

    def test_plaza_center_is_clear(self):
        separation = math.hypot(
            POLICE_CAR_POSITION[0] - PLAZA_CENTER[0],
            POLICE_CAR_POSITION[1] - PLAZA_CENTER[1],
        )

        self.assertGreaterEqual(separation, 5.0)

    def test_map_has_no_tree_obstacles(self):
        self.assertFalse(any("T" in row for row in self.game.grid))

    def test_player_starts_at_the_map_center(self):
        self.assertEqual(
            PLAYER_START,
            (self.game.map_width / 2, 0, self.game.map_height / 2),
        )
        self.assertFalse(self.game.is_wall(PLAYER_START[0], PLAYER_START[2]))

    def test_game_spawns_two_officers_and_fifteen_neighbors(self):
        self.assertEqual(NEIGHBOR_COUNT, 15)
        self.assertEqual(OFFICER_COUNT, 2)
        self.assertEqual(GUARD_COUNT, 17)
        self.game.player = SimpleNamespace(x=17.5, z=12.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]

        positions = self.game.random_neighbor_positions(GUARD_COUNT)

        self.assertEqual(len(positions), GUARD_COUNT)
        self.assertEqual(len(set(positions)), GUARD_COUNT)

    def test_chasing_neighbors_move_at_double_speed(self):
        self.assertEqual(NEIGHBOR_CHASE_SPEED_MULTIPLIER, 2)

    def test_packages_spawn_randomly_across_walkable_map_without_overlapping(self):
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]
        rng = random.Random(42)
        with patch("game.gameplay.random.shuffle", side_effect=rng.shuffle):
            positions = self.game.random_snack_positions()

        self.assertEqual(len(positions), SNACK_COUNT)
        self.assertTrue(
            all(not self.game.is_wall(x, z) for x, z in positions)
        )
        self.assertGreaterEqual(
            min(
                math.dist(first, second)
                for index, first in enumerate(positions)
                for second in positions[index + 1 :]
            ),
            SNACK_MIN_SPACING - 0.5,
        )
        self.assertTrue(any(z < 27 for _, z in positions))
        self.assertTrue(any(z > 27 for _, z in positions))
        self.assertTrue(
            all(
                math.dist(position, PACKAGE_RETURN_POSITION) >= 1.45
                for position in positions
            )
        )

        other_rng = random.Random(7)
        with patch("game.gameplay.random.shuffle", side_effect=other_rng.shuffle):
            another_round = self.game.random_snack_positions()
        self.assertNotEqual(positions, another_round)

    def test_moving_package_stops_before_touching_another_package(self):
        first = {"x": 4.5, "z": 4.5, "collected": False}
        second = {"x": 6.5, "z": 4.5, "collected": False}
        self.game.snacks = [first, second]

        self.assertTrue(
            self.game.snack_position_is_clear(first, 4.6, 4.5)
        )
        self.assertFalse(
            self.game.snack_position_is_clear(first, 5.0, 4.5)
        )

    def test_neighbor_sometimes_claims_an_unclaimed_package(self):
        guard = {
            "x": 10.5,
            "z": 10.5,
            "package_count": 0,
            "snack_target": None,
            "next_package_check_at": 0.0,
        }
        snack = {
            "x": 12.5,
            "z": 10.5,
            "collected": False,
            "claimed_by": None,
            "entities": (),
        }
        self.game.guard_entities = [guard]
        self.game.snacks = [snack]

        with (
            patch("game.gameplay.random.uniform", return_value=6.0),
            patch("game.gameplay.random.random", return_value=0.1),
        ):
            target = self.game.update_guard_package_task(0, 1.0)

        self.assertEqual(target, (12, 10))
        self.assertEqual(guard["snack_target"], 0)
        self.assertEqual(snack["claimed_by"], 0)

    def test_neighbor_collects_package_and_increases_own_bag(self):
        guard = {
            "x": 10.5,
            "z": 10.5,
            "package_count": 0,
            "snack_target": 0,
            "next_package_check_at": 20.0,
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=Mock(),
            ),
            "greeting_until": 0.0,
            "path": [(10, 10)],
            "repath_at": 5.0,
        }
        snack = {
            "x": 10.5,
            "z": 10.5,
            "collected": False,
            "claimed_by": 0,
            "entities": (),
        }
        self.game.guard_entities = [guard]
        self.game.snacks = [snack]

        with patch("game.gameplay.destroy"):
            target = self.game.update_guard_package_task(0, 1.0)

        self.assertIsNone(target)
        self.assertTrue(snack["collected"])
        self.assertEqual(guard["package_count"], 1)
        self.assertIsNone(guard["snack_target"])
        self.assertEqual(guard["greeting_bubble"].text, "Got one!")

    def test_full_neighbor_bag_returns_to_station_without_crediting_player(self):
        guard = {
            "x": 10.5,
            "z": 10.5,
            "package_count": 3,
            "package_glow": SimpleNamespace(enabled=False),
            "snack_target": None,
            "next_package_check_at": 20.0,
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=Mock(),
            ),
            "greeting_until": 0.0,
            "path": [(9, 8)],
            "repath_at": 5.0,
        }
        self.game.guard_entities = [guard]
        self.game.treats_returned = 0

        goal = self.game.update_guard_package_task(0, 1.0)
        self.assertEqual(goal, (6, 5))
        self.assertTrue(guard["package_glow"].enabled)

        guard["x"], guard["z"] = PACKAGE_RETURN_POSITION
        goal = self.game.update_guard_package_task(0, 2.0)

        self.assertIsNone(goal)
        self.assertEqual(guard["package_count"], 0)
        self.assertEqual(self.game.neighbor_treats_returned, 3)
        self.assertEqual(self.game.treats_returned, 0)
        self.assertFalse(guard["package_glow"].enabled)
        self.assertEqual(guard["greeting_bubble"].text, "Whew!")

    def test_ufo_tint_turns_neighbor_green_and_restores_original_colors(self):
        original = object()
        body = SimpleNamespace(color=original, children=[])
        nested = SimpleNamespace(color=original, children=[])
        body.children.append(nested)
        guard = {
            "root": SimpleNamespace(children=[body]),
            "greeting_bubble": SimpleNamespace(),
            "package_glow": SimpleNamespace(),
            "ufo_original_colors": None,
        }

        GameplayMixin.set_guard_ufo_tint(guard, True)

        self.assertNotEqual(body.color, original)
        self.assertNotEqual(nested.color, original)
        GameplayMixin.set_guard_ufo_tint(guard, False)
        self.assertIs(body.color, original)
        self.assertIs(nested.color, original)
        self.assertIsNone(guard["ufo_original_colors"])

    def test_officer_tracks_and_eliminates_only_ufo_transformed_neighbors(self):
        officer = {
            "x": 5.5,
            "z": 10.5,
            "is_officer": True,
            "path": [],
            "repath_at": 0.0,
            "root": SimpleNamespace(enabled=True),
        }
        ordinary_neighbor = {
            "x": 6.0,
            "z": 10.5,
            "is_officer": False,
            "transformed_by_ufo": False,
            "eliminated": False,
        }
        transformed_neighbor = {
            "x": 10.5,
            "z": 10.5,
            "is_officer": False,
            "transformed_by_ufo": True,
            "eliminated": False,
            "root": SimpleNamespace(enabled=True),
            "greeting_bubble": SimpleNamespace(enabled=True),
            "package_glow": SimpleNamespace(enabled=True),
            "snack_target": None,
            "speed_boost_target": False,
        }
        self.game.guard_entities = [
            officer,
            ordinary_neighbor,
            transformed_neighbor,
        ]
        self.game.neighbor_chase = None
        self.game.neighbor_abduction = None
        self.game.speed_boost_pickup = None
        self.game.shortest_path = Mock(return_value=[(10, 10)])

        target_index = self.game.update_officer_green_target(0, 1.0)

        self.assertEqual(target_index, 2)
        self.assertEqual(officer["path"], [(10, 10)])
        self.assertFalse(ordinary_neighbor["eliminated"])

        officer["x"] = 10.0
        self.game.update_officer_green_target(0, 2.0)

        self.assertTrue(transformed_neighbor["eliminated"])
        self.assertFalse(transformed_neighbor["root"].enabled)
        self.assertFalse(transformed_neighbor["greeting_bubble"].enabled)
        self.assertFalse(transformed_neighbor["package_glow"].enabled)

    def test_caught_neighbor_loses_all_packages_to_chaser(self):
        guards = [
            {
                "x": 10.0,
                "z": 10.0,
                "package_count": 1,
                "package_glow": SimpleNamespace(enabled=False),
                "path": [],
                "repath_at": 0.0,
                "greeting_until": 0.0,
                "greeting_bubble": SimpleNamespace(
                    enabled=True,
                    text="Hi",
                    create_background=Mock(),
                ),
            },
            {
                "x": 10.6,
                "z": 10.0,
                "package_count": 3,
                "package_glow": SimpleNamespace(enabled=True),
                "path": [(10, 10)],
                "repath_at": 3.0,
                "greeting_until": 10.0,
                "greeting_bubble": SimpleNamespace(
                    enabled=True,
                    text="Aah!",
                    create_background=Mock(),
                ),
            },
        ]
        self.game.guard_entities = guards
        self.game.neighbor_chase = {"chaser": 0, "target": 1, "until": 20.0}
        self.game.next_neighbor_chase_at = 100.0
        self.game.snacks = []

        self.game.update_neighbor_chase(10.0)

        self.assertEqual(guards[0]["package_count"], 4)
        self.assertEqual(guards[1]["package_count"], 0)
        self.assertTrue(guards[0]["package_glow"].enabled)
        self.assertFalse(guards[1]["package_glow"].enabled)
        self.assertEqual(guards[0]["greeting_bubble"].text, "Got your loot!")
        self.assertEqual(guards[1]["greeting_bubble"].text, "My packages!")

    def test_police_salute_spawns_one_delayed_super_package(self):
        def make_neighbor(x, z):
            return {
                "x": x,
                "z": z,
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
                "greeting_until": 0.0,
                "saluting_until": 0.0,
            }

        officer = make_neighbor(10.5, 10.5)
        officer["is_officer"] = True
        neighbor = make_neighbor(12.5, 10.5)
        neighbor["is_officer"] = False
        self.game.guard_entities = [officer, neighbor]
        self.game.officer_next_salute_at = 1.0
        self.game.is_wall = Mock(return_value=False)
        self.game.spawn_super_package = Mock(return_value=True)

        self.game.update_officer_salutes(1.0)

        self.assertEqual(neighbor["greeting_bubble"].text, "Yes, sir!")
        self.assertEqual(officer["greeting_bubble"].text, "For you!")
        self.assertEqual(neighbor["saluting_until"], 2.5)
        self.game.spawn_super_package.assert_called_once_with(
            11.5,
            10.5,
            1.0,
            origin=(10.5, 10.5),
        )
        self.assertEqual(self.game.officer_next_salute_at, 21.0)
        self.assertEqual(OFFICER_SALUTE_RADIUS, 4.5)

    def test_second_officer_can_greet_neighbors_and_throw_super_package(self):
        officer = {
            "x": 20.5,
            "z": 20.5,
            "is_officer": True,
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=Mock(),
            ),
        }
        neighbor = {
            "x": 22.5,
            "z": 20.5,
            "is_officer": False,
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=Mock(),
            ),
        }
        self.game.guard_entities = [
            {"x": 2.5, "z": 2.5, "is_officer": True},
            officer,
            neighbor,
        ]
        self.game.officer_next_salute_at = 1.0
        self.game.is_wall = Mock(return_value=False)
        self.game.spawn_super_package = Mock(return_value=True)

        self.game.update_officer_salutes(1.0)

        self.assertEqual(officer["greeting_bubble"].text, "For you!")
        self.assertEqual(neighbor["greeting_bubble"].text, "Yes, sir!")
        self.game.spawn_super_package.assert_called_once_with(
            21.5,
            20.5,
            1.0,
            origin=(20.5, 20.5),
        )

    def test_super_package_gives_neighbor_four_times_speed_temporarily(self):
        guard = {
            "x": 4.5,
            "z": 4.5,
            "speed_boost_target": True,
            "speed_boost_until": 0.0,
            "greeting_until": 0.0,
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=Mock(),
            ),
            "path": [(5, 4)],
            "repath_at": 10.0,
        }
        entities = tuple(Mock() for _ in range(4))
        self.game.guard_entities = [guard]
        self.game.speed_boost_pickup = {
            "x": 4.5,
            "z": 4.5,
            "claimed_by": 0,
            "entities": entities,
        }

        with patch("game.gameplay.destroy"):
            self.game.update_guard_package_task(0, 3.0)

        self.assertEqual(guard["speed_boost_until"], 3.0 + SUPER_PACKAGE_DURATION)
        self.assertFalse(guard["speed_boost_target"])
        self.assertIsNone(self.game.speed_boost_pickup)
        self.assertEqual(SUPER_PACKAGE_SPEED_MULTIPLIER, 4)

    def test_player_collects_super_package_and_runs_four_times_faster(self):
        self.game.player = SimpleNamespace(x=10.5, z=10.5)
        self.game.set_message = Mock()
        self.game.refresh_hud = Mock()
        normal_speed = self.game.player_movement_speed(False, 7.0)
        entities = tuple(Mock() for _ in range(4))
        self.game.speed_boost_pickup = {
            "x": 10.5,
            "z": 10.5,
            "entities": entities,
        }

        with patch("game.gameplay.clock.monotonic", return_value=7.0), patch(
            "game.gameplay.destroy"
        ):
            self.game.interact()

        boosted_speed = self.game.player_movement_speed(False, 8.0)
        self.assertAlmostEqual(boosted_speed, normal_speed * 4)
        self.assertEqual(
            self.game.player_speed_boost_until,
            7.0 + SUPER_PACKAGE_DURATION,
        )
        self.assertIsNone(self.game.speed_boost_pickup)
        self.game.set_message.assert_called_once_with(
            "Super package! 4x speed for 12 seconds!"
        )
        self.game.refresh_hud.assert_called_once_with()

    def test_interacting_at_return_station_returns_bag_contents(self):
        self.game.player = SimpleNamespace(
            x=PACKAGE_RETURN_POSITION[0],
            z=PACKAGE_RETURN_POSITION[1],
        )
        self.game.candy_count = 4
        self.game.treats_returned = 2
        self.game.house_state = [{}]
        self.game.visited_houses = 0
        self.game.set_message = Mock()
        self.game.refresh_hud = Mock()

        self.game.interact()

        self.assertEqual(self.game.candy_count, 0)
        self.assertEqual(self.game.treats_returned, 6)
        self.game.set_message.assert_called_once_with("Returned 4 packages.")
        self.game.refresh_hud.assert_called_once_with()

    def test_return_zone_map_cells_follow_the_interaction_radius(self):
        self.assertTrue(GameplayMixin.return_zone_contains_cell(6, 5))
        self.assertTrue(GameplayMixin.return_zone_contains_cell(4, 5))
        self.assertTrue(GameplayMixin.return_zone_contains_cell(7, 5))
        self.assertFalse(GameplayMixin.return_zone_contains_cell(3, 5))
        self.assertFalse(GameplayMixin.return_zone_contains_cell(8, 5))
        self.assertEqual(PACKAGE_RETURN_RADIUS, 1.8)

    def test_fifteen_neighbors_receive_distinct_reachable_patrol_targets(self):
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

    def test_blocked_snack_near_path_goal_does_not_pop_cleared_path(self):
        candy = SimpleNamespace(y=0.0, position=None)
        wrapper = SimpleNamespace(y=0.0, position=None)
        glow = SimpleNamespace(position=None, scale=0.0)
        snack = {
            "collected": False,
            "entities": (candy, wrapper, glow),
            "phase": 0.0,
            "x": 5.49,
            "z": 5.5,
            "path": [(5, 5)],
            "repath_at": 100.0,
        }
        self.game.snacks = [snack]
        self.game.player = SimpleNamespace(x=5.5, z=5.5)
        self.game.snack_position_is_clear = Mock(return_value=False)

        self.game.update_snacks(1 / 60, 1.0)

        self.assertEqual(snack["path"], [])
        self.assertEqual(snack["repath_at"], 1.65)

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
                "greeting_bubble": SimpleNamespace(enabled=False, text="Hi"),
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
                "greeting_bubble": SimpleNamespace(enabled=False, text="Hi"),
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
            "greeting_bubble": SimpleNamespace(enabled=False, text="Hi"),
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
                    "greeting_bubble": SimpleNamespace(enabled=False, text="Hi"),
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

    def test_neighbors_sometimes_start_a_chase_pair(self):
        guards = [
            {
                "x": 18.5,
                "z": 12.5,
                "model_controlled": False,
                "path": [(19, 12)],
                "repath_at": 50.0,
                "greeting_until": 0.0,
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
            },
            {
                "x": 23.5,
                "z": 12.5,
                "model_controlled": False,
                "path": [(22, 12)],
                "repath_at": 50.0,
                "greeting_until": 0.0,
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
            },
        ]
        self.game.guard_entities = guards
        self.game.neighbor_chase = None
        self.game.next_neighbor_chase_at = 0.0

        choose_pair = patch("game.gameplay.random.choice", return_value=(0, 1))
        chase_duration = patch("game.gameplay.random.uniform", return_value=6.0)
        with choose_pair, chase_duration:
            chase = self.game.update_neighbor_chase(10.0)

        self.assertEqual(chase["chaser"], 0)
        self.assertEqual(chase["target"], 1)
        self.assertEqual(chase["until"], 16.0)
        self.assertEqual(guards[0]["greeting_bubble"].text, "I'll get you!")
        self.assertEqual(guards[1]["greeting_bubble"].text, "Aah!")
        self.assertEqual(guards[0]["path"], [])
        self.assertEqual(guards[0]["repath_at"], 0.0)

    def test_ufo_lifts_a_neighbor_then_returns_them(self):
        original_color = object()
        body = SimpleNamespace(color=original_color, children=[])
        guard = {
            "x": 18.5,
            "z": 12.5,
            "model_controlled": False,
            "path": [(19, 12)],
            "repath_at": 30.0,
            "greeting_until": 0.0,
            "sky_gazing_until": 0.0,
            "root": SimpleNamespace(
                position=(18.5, 0, 12.5),
                children=[body],
            ),
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=Mock(),
            ),
        }
        ship = SimpleNamespace(enabled=False, position=None, rotation_y=0)
        beam = SimpleNamespace(enabled=False, color=None)
        ring = SimpleNamespace(enabled=False, scale=0)
        self.game.guard_entities = [
            {"model_controlled": True},
            guard,
        ]
        self.game.player = SimpleNamespace(x=18.5, z=12.5)
        self.game.neighbor_chase = None
        self.game.neighbor_abduction = None
        self.game.next_neighbor_abduction_at = 10.0
        self.game.ufo = {"ship": ship, "beam": beam, "ring": ring}

        with patch("game.gameplay.random.choice", return_value=(1, guard)), patch(
            "game.gameplay.random.uniform",
            return_value=8.0,
        ):
            abduction = self.game.update_neighbor_abduction(10.0)
        self.assertEqual(abduction["neighbor"], 1)
        self.assertTrue(ship.enabled)
        self.assertTrue(beam.enabled)
        abducted_color = body.color
        self.assertIsNot(abducted_color, original_color)

        self.game.update_neighbor_abduction(11.0)
        self.assertGreater(guard["root"].position[1], 0)

        with patch("game.gameplay.random.uniform", return_value=50.0):
            self.assertIsNone(self.game.update_neighbor_abduction(18.0))

        self.assertEqual(guard["root"].position, (18.5, 0, 12.5))
        self.assertIs(body.color, abducted_color)
        self.assertTrue(guard["transformed_by_ufo"])
        self.assertEqual(guard["greeting_bubble"].text, "Back!")
        self.assertFalse(ship.enabled)
        self.assertFalse(beam.enabled)

    def test_neighbors_run_around_a_neighbor_abducted_by_ufo(self):
        def make_guard(x):
            return {
                "x": x,
                "z": 12.5,
                "model_controlled": False,
                "path": [],
                "repath_at": 30.0,
                "greeting_until": 0.0,
                "sky_gazing_until": 0.0,
                "root": SimpleNamespace(position=(x, 0, 12.5)),
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
            }

        abducted = make_guard(18.5)
        runner = make_guard(20.5)
        self.game.guard_entities = [abducted, runner]
        self.game.player = SimpleNamespace(x=17.5, z=12.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]
        self.game.neighbor_chase = None
        self.game.neighbor_abduction = None
        self.game.next_neighbor_abduction_at = 10.0
        self.game.ufo = {
            "ship": SimpleNamespace(enabled=False, position=None, rotation_y=0),
            "beam": SimpleNamespace(enabled=False, color=None),
            "ring": SimpleNamespace(enabled=False, scale=0),
        }

        with patch("game.gameplay.random.choice", return_value=(0, abducted)), patch(
            "game.gameplay.random.uniform",
            return_value=8.0,
        ):
            abduction = self.game.update_neighbor_abduction(10.0)

        self.assertEqual(abduction["runners"], [1])
        self.assertEqual(runner["greeting_bubble"].text, "Run!")
        self.assertIn("ufo_run_target", runner)
        self.assertGreaterEqual(
            math.hypot(
                runner["ufo_run_target"][0] + 0.5 - abducted["x"],
                runner["ufo_run_target"][1] + 0.5 - abducted["z"],
            ),
            2.5,
        )

        with patch("game.gameplay.random.uniform", return_value=50.0):
            self.game.update_neighbor_abduction(18.0)

        self.assertNotIn("ufo_run_target", runner)
        self.assertEqual(runner["path"], [])

    def test_neighbor_chaser_follows_target_instead_of_patrol(self):
        def make_guard(x, path):
            return {
                "x": x,
                "z": 12.5,
                "root": SimpleNamespace(position=None, rotation_y=0),
                "head": SimpleNamespace(rotation_y=0, rotation_x=0),
                "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
                "greeting_until": 0.0,
                "sky_gazing_until": 0.0,
                "next_sky_gaze_at": math.inf,
                "path": path,
                "repath_at": 100.0,
                "patrol_target": (2, 2),
                "phase": 0.0,
                "speed": 0.68,
                "chase_speed": 1.2,
                "chase_radius": 4.5,
                "model_controlled": False,
            }

        guards = [make_guard(18.5, []), make_guard(23.5, [(22, 12)])]
        self.game.guard_entities = guards
        self.game.neighbor_chase = {"chaser": 0, "target": 1, "until": 20.0}
        self.game.next_neighbor_chase_at = 100.0
        self.game.player = SimpleNamespace(x=1.5, z=1.5)
        self.game.ai_results = queue.Queue()
        self.game.ai_generation = 0

        self.game.update_guard(0.05, 10.0)

        self.assertEqual(guards[0]["path"][-1], (23, 12))
        self.assertGreater(guards[0]["x"], 18.5)

    def test_run_bubble_is_backed_by_fleeing_movement(self):
        def make_guard(x):
            return {
                "x": x,
                "z": 12.5,
                "root": SimpleNamespace(position=None, rotation_y=0),
                "head": SimpleNamespace(rotation_y=0, rotation_x=0),
                "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
                "greeting_bubble": SimpleNamespace(
                    enabled=True,
                    text="Run!",
                    create_background=Mock(),
                ),
                "greeting_until": 20.0,
                "sky_gazing_until": 0.0,
                "next_sky_gaze_at": math.inf,
                "path": [],
                "repath_at": 0.0,
                "patrol_target": (int(x), 12),
                "phase": 0.0,
                "speed": 0.68,
                "chase_speed": 1.2,
                "chase_radius": 0.1,
                "model_controlled": False,
            }

        chaser = make_guard(13.5)
        runner = make_guard(18.5)
        self.game.guard_entities = [chaser, runner]
        self.game.player = SimpleNamespace(x=1.5, z=1.5)
        self.game.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.game.grid)
            for x, _ in enumerate(row)
            if not self.game.is_wall(x + 0.5, z + 0.5)
        ]
        self.game.ai_results = queue.Queue()
        self.game.ai_generation = 0
        self.game.neighbor_chase = {"chaser": 0, "target": 1, "until": 20.0}
        self.game.next_neighbor_chase_at = 100.0
        self.game.neighbor_abduction = None
        self.game.next_neighbor_abduction_at = math.inf

        initial_distance = abs(runner["x"] - chaser["x"])
        for step in range(10):
            self.game.update_guard(0.1, 10.0 + step * 0.1)

        self.assertGreater(runner["x"], 18.5)
        self.assertGreater(runner["x"] - chaser["x"], initial_distance)
        self.assertTrue(runner["path"])
        self.assertEqual(runner["greeting_bubble"].text, "Aah!")

    def test_passing_neighbors_show_hi_over_both_characters(self):
        guards = [
            {
                "x": 4.0,
                "z": 8.0,
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
                "greeting_until": 0.0,
            },
            {
                "x": 5.0,
                "z": 8.0,
                "greeting_bubble": SimpleNamespace(
                    enabled=False,
                    text="Hi",
                    create_background=Mock(),
                ),
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

    def test_neighbors_pause_and_show_wow_while_looking_up(self):
        create_background = Mock()
        guard = {
            "x": 4.0,
            "z": 8.0,
            "head": SimpleNamespace(rotation_x=0),
            "root": SimpleNamespace(position=None),
            "limbs": tuple(SimpleNamespace(rotation_x=0) for _ in range(4)),
            "greeting_bubble": SimpleNamespace(
                enabled=False,
                text="Hi",
                create_background=create_background,
            ),
            "greeting_until": 0.0,
            "sky_gazing_until": 0.0,
            "next_sky_gaze_at": 10.0,
            "sky_gaze_duration": 2.0,
        }
        self.game.guard_entities = [guard]

        gazing = self.game.update_neighbor_sky_gazes(10.0)

        self.assertEqual(gazing, {0})
        self.assertEqual(guard["greeting_bubble"].text, "Wow!")
        create_background.assert_called_once_with(
            padding=(0.26, 0.18),
            radius=0.07,
            color=unittest.mock.ANY,
        )
        self.assertTrue(guard["greeting_bubble"].enabled)
        self.assertEqual(guard["head"].rotation_x, -38)
        self.game.update_neighbor_greetings(11.0)
        self.assertTrue(guard["greeting_bubble"].enabled)
        self.assertEqual(self.game.update_neighbor_sky_gazes(12.1), set())
        self.assertFalse(guard["greeting_bubble"].enabled)
        self.assertEqual(guard["head"].rotation_x, 0)
        self.assertGreater(guard["next_sky_gaze_at"], 12.1)

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
