import json
import math
import queue
import random
import threading
import time as clock
from collections import deque
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ursina import Entity, Text, Vec3, color, destroy, held_keys, mouse, time, window

from .config import (
    AI_DECISION_INTERVAL,
    HOUSE_NAMES,
    HOUSE_POSITIONS,
    INTERACTABLES,
    MISSION_SECONDS,
    NEIGHBOR_PACKAGE_CAPACITY,
    OFFICER_ELIMINATION_RADIUS,
    OFFICER_SALUTE_RADIUS,
    OFFICER_VISION_RADIUS,
    PACKAGE_RETURN_POSITION,
    PACKAGE_RETURN_RADIUS,
    PLAYER_SPEED,
    PLAYER_START,
    PLAYER_START_ROTATION,
    SNACK_COLORS,
    SNACK_COUNT,
    SNACK_KINDS,
    SNACK_MIN_SPACING,
    SUPER_PACKAGE_DURATION,
    SUPER_PACKAGE_SPEED_MULTIPLIER,
)
from .geometry import create_spark_texture, enable_alpha_blending
from .models import HouseState, SnackState


class GameplayMixin:
    def random_snack_positions(self, count=SNACK_COUNT):
        if count <= 0:
            return []

        excluded_positions = [
            (PLAYER_START[0], PLAYER_START[2]),
            PACKAGE_RETURN_POSITION,
            *HOUSE_POSITIONS,
            *((prop["x"], prop["z"]) for prop in INTERACTABLES),
            *((guard["x"], guard["z"]) for guard in self.guard_entities),
        ]
        cells = self.patrol_cells[:]
        random.shuffle(cells)

        for spacing in (
            SNACK_MIN_SPACING,
            SNACK_MIN_SPACING - 0.25,
            SNACK_MIN_SPACING - 0.5,
        ):
            positions = []
            for cell_x, cell_z in cells:
                position = (cell_x + 0.5, cell_z + 0.5)
                if any(
                    math.hypot(position[0] - x, position[1] - z) < 1.45
                    for x, z in excluded_positions
                ):
                    continue
                if any(
                    math.hypot(position[0] - x, position[1] - z) < spacing
                    for x, z in positions
                ):
                    continue
                positions.append(position)
                if len(positions) == count:
                    return positions

        raise RuntimeError(f"Could not place {count} separated packages on the map.")

    def snack_position_is_clear(self, snack, x, z):
        return all(
            other is snack
            or other["collected"]
            or math.hypot(other["x"] - x, other["z"] - z) >= SNACK_MIN_SPACING
            for other in self.snacks
        )

    def reset(self):
        self.ai_generation += 1
        if getattr(self, "speed_boost_pickup", None) is not None:
            for entity in self.speed_boost_pickup["entities"]:
                destroy(entity)
            self.speed_boost_pickup = None
        self.player.position = PLAYER_START
        self.player.rotation_y = PLAYER_START_ROTATION
        self.look_pitch = 0
        self.camera_pivot.rotation_x = 0
        self.score = 0
        self.candy_count = 0
        self.bag_capacity = 5
        self.treats_collected = 0
        self.treats_returned = 0
        self.neighbor_treats_returned = 0
        self.visited_houses = 0
        self.mission_started = clock.monotonic()
        self.mission_time_bonus = 0
        self.sprint_energy = 100.0
        self.player_speed_boost_until = 0.0
        self.speed_boost_pickup = None
        self.torch_charge = 100.0
        self.torch_on = True
        self.torch.enabled = True
        self.game_over = False
        self.map_visible = False
        self.map_text.enabled = False
        self.message = ""
        self.message_until = 0.0
        self.greeting_cooldowns = {}
        for ufo_part in self.ufo.values():
            ufo_part.enabled = False
        gaze_rng = random.Random(self.mission_started)
        self.neighbor_abduction = None
        self._last_ufo_update = self.mission_started
        self.next_neighbor_abduction_at = self.mission_started + gaze_rng.uniform(
            24.0,
            42.0,
        )
        self.neighbor_chase = None
        self.next_neighbor_chase_at = self.mission_started + gaze_rng.uniform(
            6.0,
            12.0,
        )
        self.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.grid)
            for x, _ in enumerate(row)
            if not self.is_wall(x + 0.5, z + 0.5)
        ]
        self.officer_next_salute_at = self.mission_started
        starts = self.random_neighbor_positions(len(self.guard_entities))
        for index, guard in enumerate(self.guard_entities):
            self.set_guard_ufo_tint(guard, False)
            x, z = starts[index]
            guard.update(
                x=x,
                z=z,
                path=[],
                repath_at=0.0,
                patrol_target=(int(x), int(z)),
                ai_target=None,
                ai_mode="patrol",
                ai_retry_at=0.0,
                greeting_until=0.0,
                sky_gazing_until=0.0,
                next_sky_gaze_at=self.mission_started + gaze_rng.uniform(8, 20),
                sky_gaze_duration=gaze_rng.uniform(2.0, 3.5),
                package_count=0,
                snack_target=None,
                next_package_check_at=self.mission_started + gaze_rng.uniform(12, 28),
                speed_boost_until=0.0,
                speed_boost_target=False,
                saluting_until=0.0,
                throwing_until=0.0,
                ufo_original_colors=None,
                transformed_by_ufo=False,
                eliminated=False,
            )
            guard["root"].enabled = True
            package_glow = guard.get("package_glow")
            if package_glow is not None:
                package_glow.enabled = False
            self.set_neighbor_bubble(guard, "Hi")
            guard["greeting_bubble"].enabled = False
            guard["root"].position = (x, 0, z)
            guard["root"].rotation_y = 0
            guard["head"].rotation_x = 0
        for index, guard in enumerate(self.guard_entities):
            guard["patrol_target"] = self.choose_guard_patrol_target(index)
        self.house_state: list[HouseState] = [
            {"x": x, "z": z, "visited": False, "name": name}
            for (x, z), name in zip(HOUSE_POSITIONS, HOUSE_NAMES)
        ]
        for prop in self.interactable_entities:
            prop["used"] = False
        for entities in self.snack_entities:
            for entity in entities:
                destroy(entity)
        self.snack_entities = []
        self.snacks: list[SnackState] = []
        snack_positions = self.random_snack_positions()
        glow_texture = create_spark_texture()
        for index, (x, z) in enumerate(snack_positions):
            kind = SNACK_KINDS[index % len(SNACK_KINDS)]
            snack_color = SNACK_COLORS[index % len(SNACK_COLORS)]
            candy = Entity(
                model="sphere" if kind == "lollipop" else "cube",
                position=(x, 0.42, z),
                scale=(0.34, 0.46, 0.34) if kind == "lollipop" else (0.42, 0.34, 0.3),
                color=snack_color,
                texture=self.wrapper_texture,
                unlit=True,
            )
            wrapper_fold = Entity(
                model="cube",
                position=(x + 0.2, 0.42, z),
                scale=(0.12, 0.2, 0.22),
                rotation=(18, 23, 12),
                color=SNACK_COLORS[(index + 2) % len(SNACK_COLORS)],
                texture=self.wrapper_texture,
                unlit=True,
            )
            glow = Entity(
                model="quad",
                position=(x, 0.5, z),
                scale=0.8,
                color=color.rgba(255, 255, 255, 190),
                texture=glow_texture,
                billboard=True,
                double_sided=True,
                unlit=True,
            )
            glow.set_light_off()
            enable_alpha_blending(glow)
            self.snack_entities.append([candy, wrapper_fold, glow])
            self.snacks.append(
                {
                    "x": x,
                    "z": z,
                    "phase": index * 0.71,
                    "kind": kind,
                    "collected": False,
                    "path": [],
                    "repath_at": 0.0,
                    "claimed_by": None,
                    "entities": (candy, wrapper_fold, glow),
                }
            )
        for house in self.house_entities:
            house["door"].color = color.rgb(72, 73, 58)
        self.message_text.text = ""
        self.end_text.enabled = False
        self.refresh_hud()
        if not self.ai_api_key:
            self.set_message(
                "No OPENAI_API_KEY — the neighbor uses local patrol AI.",
                5,
            )

    def is_wall(self, x, z):
        cell_x, cell_z = int(x), int(z)
        return (
            cell_x < 0
            or cell_z < 0
            or cell_x >= self.map_width
            or cell_z >= self.map_height
            or self.grid[cell_z][cell_x] in ("#", "T", "H")
        )

    def random_neighbor_positions(self, count):
        cells = self.patrol_cells[:]
        random.shuffle(cells)
        starts = []
        if count <= 0:
            return starts
        for minimum_distance in (10.0, 6.0, 0.0):
            for cell_x, cell_z in cells:
                position = (cell_x + 0.5, cell_z + 0.5)
                player_distance = math.hypot(
                    position[0] - self.player.x,
                    position[1] - self.player.z,
                )
                if player_distance < 4.0 or player_distance < minimum_distance:
                    continue
                if any(
                    math.hypot(position[0] - x, position[1] - z)
                    < minimum_distance
                    for x, z in starts
                ):
                    continue
                if position not in starts:
                    starts.append(position)
                    if len(starts) == count:
                        return starts
        if len(starts) < count:
            raise RuntimeError("Not enough walkable map cells to place all neighbors.")
        return starts

    def choose_guard_patrol_target(self, guard_index):
        guard = self.guard_entities[guard_index]
        other_positions = []
        other_targets = []
        for index, other in enumerate(self.guard_entities):
            if index == guard_index:
                continue
            if other.get("eliminated", False):
                continue
            other_positions.append((other["x"], other["z"]))
            if "patrol_target" in other:
                other_targets.append(
                    (other["patrol_target"][0] + 0.5, other["patrol_target"][1] + 0.5)
                )

        for minimum_distance in (12.0, 8.0, 4.0, 0.0):
            candidates = [
                cell
                for cell in self.patrol_cells
                if math.hypot(
                    cell[0] + 0.5 - guard["x"],
                    cell[1] + 0.5 - guard["z"],
                )
                >= minimum_distance
                and cell not in {
                    other["patrol_target"]
                    for index, other in enumerate(self.guard_entities)
                    if index != guard_index and "patrol_target" in other
                }
            ]
            if candidates:
                def separation(cell):
                    position = (cell[0] + 0.5, cell[1] + 0.5)
                    distances = [
                        math.hypot(position[0] - x, position[1] - z)
                        for x, z in other_positions + other_targets
                    ]
                    return min(distances, default=math.inf)

                best_separation = max(separation(cell) for cell in candidates)
                best_candidates = [
                    cell for cell in candidates
                    if separation(cell) >= best_separation - 1.0
                ]
                return random.choice(best_candidates)
        raise RuntimeError("Could not find a patrol destination for a neighbor.")

    def shortest_path(self, start, goal):
        if self.is_wall(goal[0] + 0.5, goal[1] + 0.5):
            return []
        queue = deque([start])
        previous = {start: None}
        while queue:
            cell = queue.popleft()
            if cell == goal:
                break
            for neighbor in (
                (cell[0] + 1, cell[1]),
                (cell[0] - 1, cell[1]),
                (cell[0], cell[1] + 1),
                (cell[0], cell[1] - 1),
            ):
                if neighbor not in previous and not self.is_wall(
                    neighbor[0] + 0.5, neighbor[1] + 0.5
                ):
                    previous[neighbor] = cell
                    queue.append(neighbor)
        if goal not in previous:
            return []
        path = []
        cell = goal
        while cell != start:
            path.append(cell)
            cell = previous[cell]
        path.reverse()
        return path

    @staticmethod
    def fetch_ai_neighbor_target(api_key, model, snapshot, candidates):
        body = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": 80,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You control one opponent in a 3D game. Choose the best "
                        "reachable goal from the candidates to intercept the player. "
                        "Choose mode='chase' when intercepting the player is "
                        "worthwhile, "
                        "or mode='patrol' when patrolling is better. Return only JSON "
                        "in the format "
                        '{"target_index": 0, "mode": "chase"}. '
                        "The index must refer to an item in the candidate list."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"situation": snapshot, "candidates": candidates},
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        request = Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            decision = json.loads(content)
            target_index = decision.get("target_index")
            if (
                isinstance(target_index, bool)
                or not isinstance(target_index, int)
                or not 0 <= target_index < len(candidates)
            ):
                return None, None, "AI returned an invalid target."
            mode = decision.get("mode")
            if mode not in ("chase", "patrol"):
                return None, None, "AI returned an invalid behavior mode."
            return tuple(candidates[target_index]["cell"]), mode, None
        except HTTPError as error:
            if error.code == 401:
                return None, None, "The API rejected the key (HTTP 401)."
            if error.code == 429:
                return (
                    None,
                    None,
                    "API rate limit reached (HTTP 429); using local patrol.",
                )
            return None, None, f"API returned HTTP error {error.code}."
        except URLError:
            return None, None, "Cannot connect to the API; using local patrol."
        except TimeoutError:
            return None, None, "API request timed out; using local patrol."
        except (OSError, HTTPException):
            return None, None, "API connection error; using local patrol."
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            TypeError,
        ):
            return None, None, "Could not read the AI response."

    def request_ai_neighbor_target(self, guard, now):
        if not self.ai_api_key or guard["ai_inflight"] or now < guard["ai_retry_at"]:
            return

        start = (int(guard["x"]), int(guard["z"]))
        player_cell = (int(self.player.x), int(self.player.z))
        possible_goals = [
            (player_cell, "player position"),
            ((player_cell[0] + 1, player_cell[1]), "intercept from the east"),
            ((player_cell[0] - 1, player_cell[1]), "intercept from the west"),
            ((player_cell[0], player_cell[1] + 1), "intercept from the south"),
            ((player_cell[0], player_cell[1] - 1), "intercept from the north"),
        ]
        possible_goals.append(
            (guard["patrol_target"], "assigned patrol point")
        )

        candidates = []
        seen = set()
        for cell, label in possible_goals:
            if cell in seen or self.is_wall(cell[0] + 0.5, cell[1] + 0.5):
                continue
            if cell != start and not self.shortest_path(start, cell):
                continue
            seen.add(cell)
            candidates.append({"cell": cell, "description": label})
        if not candidates:
            guard["ai_retry_at"] = now + 2
            self.set_message(
                "Neighbor AI: no reachable targets; switching to patrol.",
                3,
            )
            return

        snapshot = {
            "neighbor": {"x": round(guard["x"], 1), "z": round(guard["z"], 1)},
            "player": {"x": round(self.player.x, 1), "z": round(self.player.z, 1)},
            "other_neighbors": [
                {"x": round(other["x"], 1), "z": round(other["z"], 1)}
                for other in self.guard_entities
                if other is not guard
            ],
            "collected_treats": self.treats_collected,
        }
        generation = self.ai_generation
        guard["ai_inflight"] = True
        guard["ai_inflight_generation"] = generation
        guard["ai_retry_at"] = now + AI_DECISION_INTERVAL
        thread = threading.Thread(
            target=self._run_ai_neighbor_request,
            args=(generation, snapshot, candidates),
            daemon=True,
        )
        thread.start()

    def _run_ai_neighbor_request(self, generation, snapshot, candidates):
        target, mode, error = self.fetch_ai_neighbor_target(
            self.ai_api_key,
            self.ai_model,
            snapshot,
            candidates,
        )
        self.ai_results.put((generation, target, mode, error))

    def flee_path(self, snack):
        player_cell = (int(self.player.x), int(self.player.z))
        snack_cell = (int(snack["x"]), int(snack["z"]))
        distances = {player_cell: 0}
        queue = deque([player_cell])
        while queue:
            cell = queue.popleft()
            for neighbor in (
                (cell[0] + 1, cell[1]),
                (cell[0] - 1, cell[1]),
                (cell[0], cell[1] + 1),
                (cell[0], cell[1] - 1),
            ):
                if neighbor not in distances and not self.is_wall(
                    neighbor[0] + 0.5, neighbor[1] + 0.5
                ):
                    distances[neighbor] = distances[cell] + 1
                    queue.append(neighbor)
        current_distance = distances.get(snack_cell, 0)
        safer = [
            cell
            for cell, distance in distances.items()
            if distance >= current_distance + 2
        ] or list(distances)
        farthest = max(distances[cell] for cell in safer)
        options = [cell for cell in safer if distances[cell] == farthest]
        goal = options[int(snack["phase"] * 100) % len(options)]
        snack["path"] = self.shortest_path(snack_cell, goal)

    def update_neighbor_greetings(self, now):
        chase = getattr(self, "neighbor_chase", None)
        chasing_neighbors = (
            {chase["chaser"], chase["target"]} if chase is not None else set()
        )
        for index, guard in enumerate(self.guard_entities):
            if guard.get("eliminated", False):
                continue
            if index in chasing_neighbors:
                continue
            if (
                now >= guard["greeting_until"]
                and now >= guard.get("sky_gazing_until", 0.0)
            ):
                guard["greeting_bubble"].enabled = False

        for first_index, first in enumerate(self.guard_entities):
            if first.get("eliminated", False):
                continue
            if first_index in chasing_neighbors:
                continue
            for second_index in range(first_index + 1, len(self.guard_entities)):
                if second_index in chasing_neighbors:
                    continue
                second = self.guard_entities[second_index]
                if second.get("eliminated", False):
                    continue
                if (
                    now < first.get("sky_gazing_until", 0.0)
                    or now < second.get("sky_gazing_until", 0.0)
                ):
                    continue
                pair = (first_index, second_index)
                distance = math.hypot(
                    first["x"] - second["x"],
                    first["z"] - second["z"],
                )
                if distance > 1.5 or now < self.greeting_cooldowns.get(pair, 0.0):
                    continue
                greeting_until = now + 1.5
                for guard in (first, second):
                    guard["greeting_until"] = greeting_until
                    self.set_neighbor_bubble(guard, "Hi")
                self.greeting_cooldowns[pair] = now + 5.0

    def update_neighbor_chase(self, now):
        chase = getattr(self, "neighbor_chase", None)
        if chase is not None:
            chaser = self.guard_entities[chase["chaser"]]
            target = self.guard_entities[chase["target"]]
            distance = math.hypot(
                chaser["x"] - target["x"],
                chaser["z"] - target["z"],
            )
            if now < chase["until"] and distance > 1.0:
                return chase
            caught = distance <= 1.0
            for participant in (chaser, target):
                snack_target = participant.get("snack_target")
                if snack_target is not None and snack_target < len(self.snacks):
                    snack = self.snacks[snack_target]
                    if snack.get("claimed_by") in (
                        chase["chaser"],
                        chase["target"],
                    ):
                        snack["claimed_by"] = None
                participant["snack_target"] = None
                if (
                    participant.get("speed_boost_target")
                    and self.speed_boost_pickup is not None
                ):
                    self.speed_boost_pickup["claimed_by"] = None
                    participant["speed_boost_target"] = False
            if caught and target.get("package_count", 0):
                chaser["package_count"] = (
                    chaser.get("package_count", 0) + target["package_count"]
                )
                target["package_count"] = 0
                self.update_neighbor_package_glow(chaser)
                self.update_neighbor_package_glow(target)
                self.set_neighbor_bubble(chaser, "Got your loot!")
                self.set_neighbor_bubble(target, "My packages!")
            for index in (chase["chaser"], chase["target"]):
                participant = self.guard_entities[index]
                participant["path"] = []
                participant["repath_at"] = 0.0
                participant["greeting_until"] = now + 1.5 if caught else 0.0
                if not caught:
                    participant["greeting_bubble"].enabled = False
            chaser["path"] = []
            chaser["repath_at"] = 0.0
            self.neighbor_chase = None
            self.next_neighbor_chase_at = now + random.uniform(6.0, 12.0)

        if now < getattr(self, "next_neighbor_chase_at", math.inf):
            return None

        neighbors = [
            index
            for index, guard in enumerate(self.guard_entities)
            if not guard.get(
                "is_officer",
                guard.get("model_controlled", False),
            )
            and not guard.get("eliminated", False)
            and now >= guard.get("sky_gazing_until", 0.0)
        ]
        pairs = []
        for chaser_index in neighbors:
            chaser = self.guard_entities[chaser_index]
            for target_index in neighbors:
                if target_index == chaser_index:
                    continue
                target = self.guard_entities[target_index]
                distance = math.hypot(
                    chaser["x"] - target["x"],
                    chaser["z"] - target["z"],
                )
                if not 3.0 <= distance <= 10.0:
                    continue
                start = (int(chaser["x"]), int(chaser["z"]))
                goal = (int(target["x"]), int(target["z"]))
                if start != goal and not self.shortest_path(start, goal):
                    continue
                pairs.append((chaser_index, target_index))

        if not pairs:
            self.next_neighbor_chase_at = now + random.uniform(3.0, 6.0)
            return None

        chaser_index, target_index = random.choice(pairs)
        until = now + random.uniform(9.0, 13.0)
        self.neighbor_chase = {
            "chaser": chaser_index,
            "target": target_index,
            "until": until,
        }
        chaser = self.guard_entities[chaser_index]
        target = self.guard_entities[target_index]
        chaser["path"] = []
        chaser["repath_at"] = 0.0
        chaser["greeting_until"] = until
        target["greeting_until"] = until
        self.set_neighbor_bubble(chaser, "I'll get you!")
        if math.hypot(chaser["x"] - target["x"], chaser["z"] - target["z"]) > 1.0:
            self.set_neighbor_bubble(target, "Aah!")
        return self.neighbor_chase

    def choose_neighbor_flee_path(self, runner, chaser):
        start = (int(runner["x"]), int(runner["z"]))
        away_x = runner["x"] - chaser["x"]
        away_z = runner["z"] - chaser["z"]
        away_length = math.hypot(away_x, away_z)
        if away_length == 0:
            away_x, away_z, away_length = 1.0, 0.0, 1.0
        away_x /= away_length
        away_z /= away_length

        candidates = []
        for cell in self.patrol_cells:
            goal_x, goal_z = cell[0] + 0.5, cell[1] + 0.5
            dx = goal_x - runner["x"]
            dz = goal_z - runner["z"]
            runner_distance = math.hypot(dx, dz)
            if not 3.0 <= runner_distance <= 9.0:
                continue
            chaser_distance = math.hypot(
                goal_x - chaser["x"],
                goal_z - chaser["z"],
            )
            if chaser_distance < 4.0:
                continue
            score = dx * away_x + dz * away_z + chaser_distance * 0.2
            candidates.append((score, cell))

        for _, goal in sorted(candidates, reverse=True)[:12]:
            path = self.shortest_path(start, goal)
            if path:
                return goal, path
        return None, []

    def update_neighbor_abduction(self, now):
        abduction = getattr(self, "neighbor_abduction", None)
        if abduction is None:
            if now < getattr(self, "next_neighbor_abduction_at", math.inf):
                return None

            unavailable = set()
            neighbor_chase = getattr(self, "neighbor_chase", None)
            if neighbor_chase is not None:
                unavailable.update(
                    (neighbor_chase["chaser"], neighbor_chase["target"])
                )
            candidates = [
                (index, guard)
                for index, guard in enumerate(self.guard_entities)
                if index not in unavailable
                and not guard.get("eliminated", False)
                and not guard.get(
                    "is_officer",
                    guard.get("model_controlled", False),
                )
                and not guard.get("model_controlled", False)
                and now >= guard.get("sky_gazing_until", 0.0)
            ]
            if not candidates:
                self.next_neighbor_abduction_at = now + 8.0
                return None

            nearby = [
                (index, guard)
                for index, guard in candidates
                if math.hypot(
                    guard["x"] - self.player.x,
                    guard["z"] - self.player.z,
                )
                <= 30.0
            ]
            index, guard = random.choice(nearby or candidates)
            abduction = {
                "neighbor": index,
                "x": guard["x"],
                "z": guard["z"],
                "started_at": now,
                "duration": random.uniform(7.0, 9.0),
                "runners": [],
            }
            self.neighbor_abduction = abduction
            guard["path"] = []
            guard["repath_at"] = 0.0
            guard["greeting_until"] = now + abduction["duration"]
            self.set_guard_ufo_tint(guard, True)
            self.set_neighbor_bubble(guard, "UFO!")
            nearby_runners = [
                (runner_index, runner)
                for runner_index, runner in enumerate(self.guard_entities)
                if runner_index != index
                and not runner.get("eliminated", False)
                and not runner.get(
                    "is_officer",
                    runner.get("model_controlled", False),
                )
                and not runner.get("model_controlled", False)
                and math.hypot(
                    runner["x"] - guard["x"],
                    runner["z"] - guard["z"],
                )
                <= 12.0
            ]
            nearby_runners.sort(
                key=lambda item: math.hypot(
                    item[1]["x"] - guard["x"],
                    item[1]["z"] - guard["z"],
                )
            )
            nearby_runners = nearby_runners[:5]
            for runner_position, (runner_index, runner) in enumerate(nearby_runners):
                runner["greeting_until"] = now + abduction["duration"]
                runner["ufo_run_phase"] = runner_position * math.tau / max(
                    1,
                    len(nearby_runners),
                )
                runner["ufo_run_target_at"] = 0.0
                self.set_neighbor_bubble(runner, "Run!")
                abduction["runners"].append(runner_index)
            self.ufo["ship"].enabled = True
            self.ufo["beam"].enabled = True
            self.ufo["ring"].enabled = True

        guard = self.guard_entities[abduction["neighbor"]]
        progress = min(1.0, (now - abduction["started_at"]) / abduction["duration"])
        if progress >= 1.0:
            guard["x"] = abduction["x"]
            guard["z"] = abduction["z"]
            guard["root"].position = (guard["x"], 0, guard["z"])
            guard["transformed_by_ufo"] = True
            guard["greeting_until"] = now + 2.0
            self.set_neighbor_bubble(guard, "Back!")
            guard["path"] = []
            guard["repath_at"] = 0.0
            self.ufo["ship"].enabled = False
            self.ufo["beam"].enabled = False
            self.ufo["ring"].enabled = False
            for runner_index in abduction["runners"]:
                runner = self.guard_entities[runner_index]
                runner.pop("ufo_run_phase", None)
                runner.pop("ufo_run_target", None)
                runner.pop("ufo_run_target_at", None)
                runner["path"] = []
                runner["repath_at"] = 0.0
            self.neighbor_abduction = None
            self.next_neighbor_abduction_at = now + random.uniform(42.0, 68.0)
            return None

        for runner_index in abduction["runners"]:
            runner = self.guard_entities[runner_index]
            if now < runner.get("ufo_run_target_at", 0.0) and runner.get(
                "ufo_run_target"
            ):
                continue
            angle = now * 0.8 + runner["ufo_run_phase"]
            ring_radius = 3.5 + 0.45 * math.sin(now * 1.9 + runner["ufo_run_phase"])
            candidates = [
                cell
                for cell in self.patrol_cells
                if 2.5
                <= math.hypot(
                    cell[0] + 0.5 - abduction["x"],
                    cell[1] + 0.5 - abduction["z"],
                )
                <= 6.5
            ]
            if candidates:
                preferred_x = abduction["x"] + math.cos(angle) * ring_radius
                preferred_z = abduction["z"] + math.sin(angle) * ring_radius
                target_cell = min(
                    candidates,
                    key=lambda cell: math.hypot(
                        cell[0] + 0.5 - preferred_x,
                        cell[1] + 0.5 - preferred_z,
                    ),
                )
                runner["ufo_run_target"] = target_cell
                runner["path"] = self.shortest_path(
                    (int(runner["x"]), int(runner["z"])),
                    target_cell,
                )
                runner["repath_at"] = now + 0.45
                runner["ufo_run_target_at"] = now + 1.25

        lift_progress = min(1.0, progress / 0.28)
        lower_progress = max(0.0, (progress - 0.68) / 0.24)
        lift = 4.5 * min(lift_progress, 1.0 - lower_progress)
        guard["root"].position = (abduction["x"], lift, abduction["z"])
        bob = math.sin(now * 2.1) * 0.16
        self.ufo["ship"].position = (
            abduction["x"],
            9.0 + bob,
            abduction["z"],
        )
        self.ufo["ship"].rotation_y += 16.0 * min(
            0.05,
            max(0.0, now - getattr(self, "_last_ufo_update", now)),
        )
        self._last_ufo_update = now
        self.ufo["ring"].scale = 1.55 + 0.2 * math.sin(now * 4.0)
        self.ufo["beam"].color = color.rgba(
            114,
            241,
            238,
            int(45 + 22 * (0.5 + 0.5 * math.sin(now * 3.2))),
        )
        return abduction

    def update_officer_green_target(self, officer_index, now):
        officer = self.guard_entities[officer_index]
        if officer.get("eliminated"):
            return None

        candidates = []
        for neighbor_index, neighbor in enumerate(self.guard_entities):
            if (
                neighbor_index == officer_index
                or neighbor.get("is_officer", neighbor.get("model_controlled", False))
                or not neighbor.get("transformed_by_ufo", False)
                or neighbor.get("eliminated", False)
            ):
                continue
            abduction = getattr(self, "neighbor_abduction", None)
            if abduction is not None and abduction["neighbor"] == neighbor_index:
                continue
            distance = math.hypot(
                neighbor["x"] - officer["x"],
                neighbor["z"] - officer["z"],
            )
            if distance > OFFICER_VISION_RADIUS:
                continue
            start = (int(officer["x"]), int(officer["z"]))
            goal = (int(neighbor["x"]), int(neighbor["z"]))
            path = [] if start == goal else self.shortest_path(start, goal)
            if start != goal and not path:
                continue
            candidates.append((distance, neighbor_index, path))

        if not candidates:
            return None

        distance, neighbor_index, path = min(candidates, key=lambda item: item[0])
        if distance <= OFFICER_ELIMINATION_RADIUS:
            neighbor = self.guard_entities[neighbor_index]
            neighbor["eliminated"] = True
            neighbor["root"].enabled = False
            neighbor["greeting_bubble"].enabled = False
            snack_target = neighbor.get("snack_target")
            if snack_target is not None and snack_target < len(self.snacks):
                snack = self.snacks[snack_target]
                if snack.get("claimed_by") == neighbor_index:
                    snack["claimed_by"] = None
            neighbor["snack_target"] = None
            if (
                neighbor.get("speed_boost_target")
                and self.speed_boost_pickup is not None
                and self.speed_boost_pickup.get("claimed_by") == neighbor_index
            ):
                self.speed_boost_pickup["claimed_by"] = None
            neighbor["speed_boost_target"] = False
            package_glow = neighbor.get("package_glow")
            if package_glow is not None:
                package_glow.enabled = False
            neighbor_chase = getattr(self, "neighbor_chase", None)
            if neighbor_chase is not None and neighbor_index in (
                neighbor_chase["chaser"],
                neighbor_chase["target"],
            ):
                self.neighbor_chase = None
            return None

        if now >= officer["repath_at"] or not officer["path"]:
            officer["path"] = path
            officer["repath_at"] = now + 0.3
        return neighbor_index

    @staticmethod
    def set_guard_ufo_tint(guard, enabled):
        if enabled:
            if guard.get("ufo_original_colors") is not None:
                return
            original_colors = []
            skipped = {
                id(guard["greeting_bubble"]),
                id(guard.get("package_glow")),
            }
            pending = list(getattr(guard["root"], "children", ()))
            while pending:
                entity = pending.pop()
                pending.extend(getattr(entity, "children", ()))
                if id(entity) in skipped or not hasattr(entity, "color"):
                    continue
                original_colors.append((entity, entity.color))
                entity.color = color.rgb(72, 220, 92)
            guard["ufo_original_colors"] = original_colors
            return

        for entity, original_color in guard.get("ufo_original_colors") or []:
            entity.color = original_color
        guard["ufo_original_colors"] = None

    def spawn_super_package(self, x, z, now=None, origin=None):
        if self.speed_boost_pickup is not None:
            return False
        if now is None:
            now = clock.monotonic()
        start_x, start_z = origin or (x, z)
        glow_texture = create_spark_texture()
        package = Entity(
            model="sphere",
            position=(start_x, 1.55, start_z),
            scale=0.58,
            color=color.rgb(255, 215, 65),
            texture=self.wrapper_texture,
            unlit=True,
        )
        wrapper = Entity(
            model="cube",
            position=(start_x + 0.2, 1.58, start_z),
            scale=(0.16, 0.28, 0.22),
            rotation=(18, 30, 12),
            color=color.rgb(61, 190, 255),
            texture=self.wrapper_texture,
            unlit=True,
        )
        glow = Entity(
            model="quad",
            position=(start_x, 1.6, start_z),
            scale=1.35,
            color=color.rgba(255, 205, 56, 230),
            texture=glow_texture,
            billboard=True,
            double_sided=True,
            unlit=True,
        )
        glow.set_light_off()
        enable_alpha_blending(glow)
        label = Text(
            text="SUPER",
            position=(start_x, 2.15, start_z),
            origin=(0, 0),
            scale=5,
            color=color.rgb(255, 234, 137),
            billboard=True,
        )
        self.speed_boost_pickup = {
            "x": x,
            "z": z,
            "start_x": start_x,
            "start_z": start_z,
            "throw_until": now + 0.9,
            "claimed_by": None,
            "available_after": now + 1.5,
            "phase": now,
            "entities": (package, wrapper, glow, label),
        }
        return True

    def collect_super_package(self, collector_index, now):
        pickup = self.speed_boost_pickup
        if pickup is None:
            return False
        for guard in self.guard_entities:
            if guard.get("speed_boost_target"):
                guard["speed_boost_target"] = False
        for entity in pickup["entities"]:
            destroy(entity)
        self.speed_boost_pickup = None
        boost_until = now + SUPER_PACKAGE_DURATION
        if collector_index is None:
            self.player_speed_boost_until = boost_until
            self.set_message("Super package! 4x speed for 12 seconds!")
        else:
            collector = self.guard_entities[collector_index]
            collector["speed_boost_until"] = boost_until
            collector["greeting_until"] = now + 1.5
            self.set_neighbor_bubble(collector, "Zoom!")
        return True

    def update_officer_salutes(self, now):
        if now < getattr(self, "officer_next_salute_at", math.inf) or len(
            self.guard_entities
        ) < 2:
            return
        officers = [
            guard
            for guard in self.guard_entities
            if not guard.get("eliminated", False)
            and guard.get(
                "is_officer",
                guard.get("model_controlled", False),
            )
        ]
        neighbors = [
            guard
            for guard in self.guard_entities
            if not guard.get("eliminated", False)
            and not guard.get(
                "is_officer",
                guard.get("model_controlled", False),
            )
        ]
        officer_neighbor_pairs = [
            (
                math.hypot(
                    neighbor["x"] - officer["x"],
                    neighbor["z"] - officer["z"],
                ),
                officer,
                neighbor,
            )
            for officer in officers
            for neighbor in neighbors
            if math.hypot(
                neighbor["x"] - officer["x"],
                neighbor["z"] - officer["z"],
            )
            <= OFFICER_SALUTE_RADIUS
        ]
        if not officer_neighbor_pairs:
            return
        _, officer, _ = min(officer_neighbor_pairs, key=lambda pair: pair[0])
        nearby_neighbors = [
            neighbor
            for neighbor in neighbors
            if math.hypot(
                neighbor["x"] - officer["x"],
                neighbor["z"] - officer["z"],
            )
            <= OFFICER_SALUTE_RADIUS
        ]
        if not nearby_neighbors:
            return

        self.officer_next_salute_at = now + 20.0
        for neighbor in nearby_neighbors:
            neighbor["saluting_until"] = now + 1.5
            neighbor["greeting_until"] = now + 1.5
            self.set_neighbor_bubble(neighbor, "Yes, sir!")
        officer["greeting_until"] = now + 1.5
        officer["throwing_until"] = now + 0.6
        self.set_neighbor_bubble(officer, "For you!")
        if self.speed_boost_pickup is None:
            receiver = min(
                nearby_neighbors,
                key=lambda guard: math.hypot(
                    guard["x"] - officer["x"],
                    guard["z"] - officer["z"],
                ),
            )
            x = (officer["x"] + receiver["x"]) * 0.5
            z = (officer["z"] + receiver["z"]) * 0.5
            if self.is_wall(x, z):
                x, z = receiver["x"], receiver["z"]
            self.spawn_super_package(
                x,
                z,
                now,
                origin=(officer["x"], officer["z"]),
            )

    def update_super_package(self, now):
        pickup = getattr(self, "speed_boost_pickup", None)
        if pickup is None:
            return
        package, wrapper, glow, label = pickup["entities"]
        progress = min(
            1.0,
            max(0.0, 1.0 - (pickup["throw_until"] - now) / 0.9),
        )
        x = pickup["start_x"] + (pickup["x"] - pickup["start_x"]) * progress
        z = pickup["start_z"] + (pickup["z"] - pickup["start_z"]) * progress
        arc = math.sin(math.pi * progress) * 1.45 if progress < 1.0 else 0
        bob = math.sin(now * 3.2 + pickup["phase"]) * 0.1
        height = 0.62 + arc + bob
        package.position = (x, height, z)
        wrapper.position = (x + 0.2, height + 0.03, z)
        glow.position = (x, height + 0.06, z)
        glow.scale = 1.25 + 0.12 * math.sin(now * 4.0)
        label.position = (x, height + 0.63, z)

    def update_guard_package_task(self, guard_index, now):
        guard = self.guard_entities[guard_index]
        guard.setdefault("package_count", 0)
        guard.setdefault("snack_target", None)
        guard.setdefault("next_package_check_at", now)
        self.update_neighbor_package_glow(guard)

        def release_target():
            target_index = guard["snack_target"]
            if target_index is not None and target_index < len(self.snacks):
                snack = self.snacks[target_index]
                if snack.get("claimed_by") == guard_index:
                    snack["claimed_by"] = None
            guard["snack_target"] = None

        if guard["package_count"] >= NEIGHBOR_PACKAGE_CAPACITY:
            release_target()
            return_x, return_z = PACKAGE_RETURN_POSITION
            if (
                math.hypot(guard["x"] - return_x, guard["z"] - return_z)
                < PACKAGE_RETURN_RADIUS
            ):
                self.neighbor_treats_returned += guard["package_count"]
                guard["package_count"] = 0
                self.update_neighbor_package_glow(guard)
                guard["path"] = []
                guard["repath_at"] = 0.0
                guard["greeting_until"] = now + 1.5
                self.set_neighbor_bubble(guard, "Whew!")
                return None
            return int(return_x), int(return_z)

        pickup = getattr(self, "speed_boost_pickup", None)
        if guard.get("speed_boost_target"):
            if pickup is None or pickup.get("claimed_by") != guard_index:
                guard["speed_boost_target"] = False
            elif math.hypot(
                guard["x"] - pickup["x"],
                guard["z"] - pickup["z"],
            ) < 0.9:
                self.collect_super_package(guard_index, now)
                guard["path"] = []
                guard["repath_at"] = 0.0
                return None
            else:
                return int(pickup["x"]), int(pickup["z"])

        target_index = guard["snack_target"]
        if target_index is not None:
            if target_index >= len(self.snacks):
                release_target()
            else:
                snack = self.snacks[target_index]
                if (
                    snack["collected"]
                    or snack.get("claimed_by") != guard_index
                ):
                    release_target()
                elif math.hypot(
                    guard["x"] - snack["x"],
                    guard["z"] - snack["z"],
                ) < 0.75:
                    snack["collected"] = True
                    snack["claimed_by"] = None
                    for entity in snack["entities"]:
                        destroy(entity)
                    guard["package_count"] += 1
                    self.update_neighbor_package_glow(guard)
                    guard["snack_target"] = None
                    guard["path"] = []
                    guard["repath_at"] = 0.0
                    guard["next_package_check_at"] = now + random.uniform(5, 10)
                    guard["greeting_until"] = now + 1.4
                    self.set_neighbor_bubble(guard, "Got one!")
                    return None
                else:
                    return int(snack["x"]), int(snack["z"])

        pickup = getattr(self, "speed_boost_pickup", None)
        if (
            not guard.get(
                "is_officer",
                guard.get("model_controlled", False),
            )
            and pickup is not None
            and pickup.get("claimed_by") is None
            and now >= pickup.get("available_after", 0.0)
            and math.hypot(
                guard["x"] - pickup["x"],
                guard["z"] - pickup["z"],
            )
            <= 12.0
        ):
            pickup["claimed_by"] = guard_index
            guard["speed_boost_target"] = True
            return int(pickup["x"]), int(pickup["z"])

        if now < guard["next_package_check_at"]:
            return None
        guard["next_package_check_at"] = now + random.uniform(12.0, 22.0)
        if random.random() >= 0.18:
            return None

        available = [
            (index, snack)
            for index, snack in enumerate(self.snacks)
            if not snack["collected"] and snack.get("claimed_by") is None
            and math.hypot(
                guard["x"] - snack["x"],
                guard["z"] - snack["z"],
            ) <= 12.0
        ]
        if not available:
            return None
        target_index, snack = min(
            available,
            key=lambda item: math.hypot(
                guard["x"] - item[1]["x"],
                guard["z"] - item[1]["z"],
            ),
        )
        snack["claimed_by"] = guard_index
        guard["snack_target"] = target_index
        return int(snack["x"]), int(snack["z"])

    @staticmethod
    def update_neighbor_package_glow(guard):
        package_glow = guard.get("package_glow")
        if package_glow is not None:
            package_glow.enabled = (
                guard["package_count"] >= NEIGHBOR_PACKAGE_CAPACITY
            )

    @staticmethod
    def set_neighbor_bubble(guard, text):
        bubble = guard["greeting_bubble"]
        if bubble.text != text:
            bubble.text = text
            bubble.create_background(
                padding=(0.26, 0.18),
                radius=0.07,
                color=color.rgba(246, 242, 219, 245),
            )
        bubble.enabled = True

    def update_neighbor_sky_gazes(self, now, excluded_neighbors=()):
        gazing_neighbors = set()
        for index, guard in enumerate(self.guard_entities):
            if index in excluded_neighbors or guard.get("eliminated", False):
                continue
            gaze_until = guard.get("sky_gazing_until", 0.0)
            if gaze_until and now >= gaze_until:
                guard["sky_gazing_until"] = 0.0
                guard["head"].rotation_x = 0
                guard["next_sky_gaze_at"] = now + random.uniform(16.0, 30.0)
                if now >= guard["greeting_until"]:
                    guard["greeting_bubble"].enabled = False
                gaze_until = 0.0

            if not gaze_until and now >= guard.get("next_sky_gaze_at", math.inf):
                gaze_until = now + guard.get("sky_gaze_duration", 2.8)
                guard["sky_gazing_until"] = gaze_until
                guard["greeting_until"] = gaze_until
                self.set_neighbor_bubble(guard, "Wow!")
                guard["head"].rotation_x = -38

            if now < gaze_until:
                gazing_neighbors.add(index)
        return gazing_neighbors

    def move_player(self):
        dt = min(time.dt, 0.05)
        if self.game_over:
            return
        sensitivity = (
            self.mouse_sensitivity if mouse.locked else self.touchpad_sensitivity
        )
        self.player.rotation_y += mouse.velocity[0] * sensitivity
        self.look_pitch = max(
            -85,
            min(85, self.look_pitch - mouse.velocity[1] * sensitivity),
        )
        self.camera_pivot.rotation_x = self.look_pitch
        self.player.rotation_y += (
            (held_keys["right arrow"] - held_keys["left arrow"]) * 115 * dt
        )
        forward_input = (
            held_keys["w"]
            + held_keys["up arrow"]
            - held_keys["s"]
            - held_keys["down arrow"]
        )
        strafe_input = held_keys["d"] - held_keys["a"]
        if not forward_input and not strafe_input:
            self.sprint_energy = min(100.0, self.sprint_energy + 15 * dt)
            return

        sprinting = held_keys["shift"] and self.sprint_energy > 0
        if sprinting:
            self.sprint_energy = max(0.0, self.sprint_energy - 28 * dt)
        else:
            self.sprint_energy = min(100.0, self.sprint_energy + 12 * dt)
        speed = self.player_movement_speed(sprinting, clock.monotonic())

        yaw = math.radians(self.player.rotation_y)
        forward = Vec3(math.sin(yaw), 0, math.cos(yaw))
        right = Vec3(math.cos(yaw), 0, -math.sin(yaw))
        movement = (forward * forward_input + right * strafe_input).normalized()
        dx, dz = movement.x * speed * dt, movement.z * speed * dt
        radius = 0.22
        next_x = self.player.x + dx
        next_z = self.player.z + dz
        if not any(
            self.is_wall(next_x + offset_x, self.player.z + offset_z)
            for offset_x in (-radius, radius)
            for offset_z in (-radius, radius)
        ):
            self.player.x = next_x
        if not any(
            self.is_wall(self.player.x + offset_x, next_z + offset_z)
            for offset_x in (-radius, radius)
            for offset_z in (-radius, radius)
        ):
            self.player.z = next_z

    def player_movement_speed(self, sprinting, now):
        speed = PLAYER_SPEED * (1.65 if sprinting else 1.0)
        if self.candy_count >= self.bag_capacity:
            speed *= 0.82
        if now < self.player_speed_boost_until:
            speed *= SUPER_PACKAGE_SPEED_MULTIPLIER
        return speed

    def recenter_captured_mouse(self):
        if not self.mouse_captured or not self.app.win.has_pointer(0):
            return
        mouse.position = (0, 0)
        mouse.prev_x = 0
        mouse.prev_y = 0

    def set_message(self, message, duration=2.2):
        self.message = message
        self.message_until = clock.monotonic() + duration
        self.message_text.text = message

    def collect_snack(self):
        pickup = self.speed_boost_pickup
        if pickup is not None and math.hypot(
            pickup["x"] - self.player.x,
            pickup["z"] - self.player.z,
        ) < 1.25:
            self.collect_super_package(None, clock.monotonic())
            self.refresh_hud()
            return

        available = [
            snack
            for snack in self.snacks
            if not snack["collected"]
            and math.hypot(snack["x"] - self.player.x, snack["z"] - self.player.z)
            < 1.25
        ]
        if not available:
            self.set_message("Move closer to the treat.", 1.2)
            return
        if self.candy_count >= self.bag_capacity:
            self.set_message("Your bag is full! Visit a house to upgrade it.", 1.8)
            return
        snack = min(
            available,
            key=lambda item: math.hypot(
                item["x"] - self.player.x,
                item["z"] - self.player.z,
            ),
        )
        snack["collected"] = True
        for entity in snack["entities"]:
            destroy(entity)
        self.candy_count += 1
        self.treats_collected += 1
        self.score += 1
        self.set_message("Treat collected.")
        self.refresh_hud()

    def return_packages(self):
        if self.candy_count <= 0:
            self.set_message("Your bag is empty.")
            return

        returned = self.candy_count
        self.treats_returned += returned
        self.candy_count = 0
        self.set_message(f"Returned {returned} package{'s' if returned != 1 else ''}.")
        if (
            self.visited_houses == len(self.house_state)
            and self.treats_returned >= 5
        ):
            self.end_game(True)
        self.refresh_hud()

    def interact(self, share=False):
        if not share:
            pickup = self.speed_boost_pickup
            if pickup is not None and math.hypot(
                pickup["x"] - self.player.x,
                pickup["z"] - self.player.z,
            ) < 1.25:
                self.collect_super_package(None, clock.monotonic())
                self.refresh_hud()
                return
            if (
                math.hypot(
                    PACKAGE_RETURN_POSITION[0] - self.player.x,
                    PACKAGE_RETURN_POSITION[1] - self.player.z,
                )
                < PACKAGE_RETURN_RADIUS
            ):
                self.return_packages()
                return
            nearby_props = [
                prop
                for prop in self.interactable_entities
                if not prop["used"]
                and math.hypot(
                    prop["position"][0] - self.player.x,
                    prop["position"][1] - self.player.z,
                )
                < 1.55
            ]
            if nearby_props:
                prop = min(
                    nearby_props,
                    key=lambda item: math.hypot(
                        item["position"][0] - self.player.x,
                        item["position"][1] - self.player.z,
                    ),
                )
                details = prop["entity"]
                if "time_bonus" in details:
                    self.mission_time_bonus += details["time_bonus"]
                if details.get("sprint"):
                    self.sprint_energy = 100.0
                if "torch" in details:
                    self.torch_charge = min(100.0, self.torch_charge + details["torch"])
                    self.torch_on = True
                    self.torch.enabled = True
                prop["used"] = True
                self.set_message(details["message"])
                self.refresh_hud()
                return

        nearby = [
            (index, house)
            for index, house in enumerate(self.house_state)
            if not house["visited"]
            and math.hypot(house["x"] - self.player.x, house["z"] - self.player.z) < 1.5
        ]
        if not nearby:
            if share:
                self.set_message("Move closer to a house to share a treat.", 1.4)
            else:
                self.collect_snack()
            return
        index, house = min(
            nearby,
            key=lambda pair: math.hypot(
                pair[1]["x"] - self.player.x,
                pair[1]["z"] - self.player.z,
            ),
        )
        if share:
            if self.candy_count < 1:
                self.set_message("You don't have a treat to share!", 1.5)
                return
            self.candy_count -= 1
            self.mission_time_bonus += 12
            self.torch_charge = min(100.0, self.torch_charge + 35)
            message = "The neighbor gave you a battery and added 12 seconds."
        else:
            self.candy_count = min(self.bag_capacity, self.candy_count + 1)
            if index == 0:
                self.bag_capacity += 2
                message = "A bag from the kiosk! Capacity +2."
            elif index == 1:
                self.sprint_energy = 100.0
                message = "The kiosk owner lent you a flashlight!"
            else:
                self.torch_charge = 100.0
                message = "R-20 battery fully charged!"
        house["visited"] = True
        self.visited_houses += 1
        self.house_entities[index]["door"].color = color.rgb(92, 112, 78)
        self.set_message(message)
        if self.visited_houses == len(self.house_state) and self.treats_returned >= 5:
            self.end_game(True)
        self.refresh_hud()

    def update_snacks(self, dt, now):
        for snack in self.snacks:
            if snack["collected"]:
                continue
            candy, wrapper_fold, glow = snack["entities"]
            candy.y = 0.42 + math.sin(now * 3 + snack["phase"]) * 0.08
            wrapper_fold.y = candy.y
            glow.position = (snack["x"], candy.y + 0.12, snack["z"])
            glow.scale = 0.72 + 0.12 * math.sin(now * 4 + snack["phase"])
            distance = math.hypot(
                snack["x"] - self.player.x,
                snack["z"] - self.player.z,
            )
            if distance > 4.5:
                snack["path"] = []
                continue
            if now >= snack["repath_at"] or not snack["path"]:
                self.flee_path(snack)
                snack["repath_at"] = now + 0.65
            if not snack["path"]:
                continue
            goal_x, goal_z = snack["path"][0]
            dx = goal_x + 0.5 - snack["x"]
            dz = goal_z + 0.5 - snack["z"]
            distance_to_goal = math.hypot(dx, dz)
            step = min(1.5 * dt, distance_to_goal)
            if step > 0:
                next_x = snack["x"] + dx / distance_to_goal * step
                next_z = snack["z"] + dz / distance_to_goal * step
                if self.snack_position_is_clear(snack, next_x, next_z):
                    snack["x"], snack["z"] = next_x, next_z
                    candy.position = (next_x, candy.y, next_z)
                    wrapper_fold.position = (next_x + 0.2, candy.y, next_z)
                    glow.position = (next_x, candy.y + 0.12, next_z)
                else:
                    snack["path"] = []
                    snack["repath_at"] = now + 0.65
            if distance_to_goal < 0.06 and snack["path"]:
                snack["path"].pop(0)

    def update_guard(self, dt, now):
        self.update_super_package(now)
        ai_guard = self.guard_entities[0]
        while True:
            try:
                generation, target, mode, error = self.ai_results.get_nowait()
            except queue.Empty:
                break
            if ai_guard["ai_inflight_generation"] == generation:
                ai_guard["ai_inflight"] = False
            if generation != self.ai_generation:
                continue
            if error:
                ai_guard["ai_retry_at"] = now + 12
                self.set_message(f"Neighbor AI: {error}", 4)
                continue
            if target is None:
                continue
            if mode not in ("chase", "patrol"):
                ai_guard["ai_retry_at"] = now + 12
                self.set_message("Neighbor AI returned an invalid mode.", 4)
                continue
            start = (int(ai_guard["x"]), int(ai_guard["z"]))
            if self.is_wall(target[0] + 0.5, target[1] + 0.5):
                ai_guard["ai_retry_at"] = now + 12
                self.set_message("Neighbor AI selected an unreachable location.", 4)
                continue
            ai_guard["ai_target"] = target
            ai_guard["ai_mode"] = mode
            ai_guard["path"] = (
                [] if target == start else self.shortest_path(start, target)
            )
            ai_guard["repath_at"] = now + 0.5
            ai_guard["ai_retry_at"] = now + AI_DECISION_INTERVAL

        ai_chaser = next(
            (
                index
                for index, guard in enumerate(self.guard_entities)
                if guard["model_controlled"]
                and guard["ai_target"] is not None
                and guard["ai_mode"] == "chase"
            ),
            None,
        )
        local_chaser = min(
            (
                (
                    index,
                    math.hypot(
                        self.player.x - guard["x"],
                        self.player.z - guard["z"],
                    ),
                )
                for index, guard in enumerate(self.guard_entities)
                if not guard.get(
                    "is_officer",
                    guard["model_controlled"],
                )
                and not guard.get("eliminated", False)
                and math.hypot(
                    self.player.x - guard["x"],
                    self.player.z - guard["z"],
                )
                < guard["chase_radius"]
            ),
            key=lambda item: item[1],
            default=(None, math.inf),
        )[0]
        active_chaser = ai_chaser if ai_chaser is not None else local_chaser
        neighbor_chase = self.update_neighbor_chase(now)
        chase_participants = (
            {neighbor_chase["chaser"], neighbor_chase["target"]}
            if neighbor_chase is not None
            else set()
        )
        gazing_neighbors = self.update_neighbor_sky_gazes(
            now,
            excluded_neighbors=chase_participants,
        )
        abduction = self.update_neighbor_abduction(now)
        self.update_officer_salutes(now)

        for guard_index, guard in enumerate(self.guard_entities):
            if guard.get("eliminated", False):
                continue
            if abduction is not None and guard_index == abduction["neighbor"]:
                continue
            if guard_index in gazing_neighbors:
                guard["root"].position = (guard["x"], 0, guard["z"])
                guard["head"].rotation_y = 0
                for limb in guard["limbs"]:
                    limb.rotation_x = 0
                continue

            distance_to_player = math.hypot(
                self.player.x - guard["x"],
                self.player.z - guard["z"],
            )
            transformed_target_index = (
                self.update_officer_green_target(guard_index, now)
                if guard.get("is_officer", guard["model_controlled"])
                else None
            )
            pursuing_transformed_neighbor = transformed_target_index is not None
            chasing_player = (
                guard_index == active_chaser
                and distance_to_player < guard["chase_radius"]
            )
            chasing_neighbor = (
                neighbor_chase is not None
                and guard_index == neighbor_chase["chaser"]
                and not chasing_player
            )
            fleeing_neighbor = (
                neighbor_chase is not None
                and guard_index == neighbor_chase["target"]
                and not chasing_player
            )
            if fleeing_neighbor:
                guard["greeting_until"] = max(
                    guard.get("greeting_until", 0.0),
                    neighbor_chase["until"],
                )
                self.set_neighbor_bubble(guard, "Aah!")
            chase_target = (
                self.guard_entities[neighbor_chase["target"]]
                if chasing_neighbor
                else self.guard_entities[transformed_target_index]
                if pursuing_transformed_neighbor
                else None
            )
            chasing = (
                chasing_player
                or chasing_neighbor
                or pursuing_transformed_neighbor
            )
            running_from_ufo = (
                abduction is not None
                and guard_index in abduction["runners"]
                and not guard["model_controlled"]
            )
            package_goal = None
            if not (
                chasing
                or fleeing_neighbor
                or running_from_ufo
                or guard.get("is_officer", guard["model_controlled"])
            ):
                package_goal = self.update_guard_package_task(guard_index, now)
            if package_goal is not None:
                if now >= guard["repath_at"] or not guard["path"]:
                    guard["path"] = self.shortest_path(
                        (int(guard["x"]), int(guard["z"])),
                        package_goal,
                    )
                    guard["repath_at"] = now + 0.4
            elif pursuing_transformed_neighbor:
                pass
            elif guard["model_controlled"]:
                self.request_ai_neighbor_target(guard, now)
                if guard["ai_target"] is not None:
                    chasing = guard["ai_mode"] == "chase"
                    if now >= guard["repath_at"] or not guard["path"]:
                        start = (int(guard["x"]), int(guard["z"]))
                        if start == guard["ai_target"]:
                            guard["path"] = []
                            if guard["ai_mode"] == "patrol":
                                guard["ai_target"] = None
                        else:
                            guard["path"] = self.shortest_path(
                                start,
                                guard["ai_target"],
                            )
                        guard["repath_at"] = now + 0.5
                elif now >= guard["repath_at"] or not guard["path"]:
                    goal = guard["patrol_target"]
                    if (int(guard["x"]), int(guard["z"])) == goal:
                        goal = self.choose_guard_patrol_target(guard_index)
                        guard["patrol_target"] = goal
                    guard["path"] = self.shortest_path(
                        (int(guard["x"]), int(guard["z"])),
                        goal,
                    )
                    guard["repath_at"] = now + 0.5
            elif running_from_ufo:
                if now >= guard["repath_at"] or not guard["path"]:
                    goal = guard.get("ufo_run_target")
                    if goal is None:
                        goal = guard["patrol_target"]
                    guard["path"] = self.shortest_path(
                        (int(guard["x"]), int(guard["z"])),
                        goal,
                    )
                    guard["repath_at"] = now + 0.45
            elif fleeing_neighbor:
                if now >= guard["repath_at"] or not guard["path"]:
                    flee_target = self.guard_entities[neighbor_chase["chaser"]]
                    _, guard["path"] = self.choose_neighbor_flee_path(
                        guard,
                        flee_target,
                    )
                    guard["repath_at"] = now + 0.35
            elif now >= guard["repath_at"] or not guard["path"]:
                if chasing_player:
                    goal = (int(self.player.x), int(self.player.z))
                elif chasing_neighbor:
                    goal = (int(chase_target["x"]), int(chase_target["z"]))
                else:
                    goal = guard["patrol_target"]
                    if (int(guard["x"]), int(guard["z"])) == goal:
                        goal = self.choose_guard_patrol_target(guard_index)
                        guard["patrol_target"] = goal
                guard["path"] = self.shortest_path(
                    (int(guard["x"]), int(guard["z"])),
                    goal,
                )
                guard["repath_at"] = now + 0.5
            speed = (
                guard["chase_speed"]
                if chasing or fleeing_neighbor or running_from_ufo
                else guard["speed"]
            )
            if now < guard.get("speed_boost_until", 0.0):
                speed *= SUPER_PACKAGE_SPEED_MULTIPLIER
            if guard["path"]:
                target_x, target_z = guard["path"][0]
                dx = target_x + 0.5 - guard["x"]
                dz = target_z + 0.5 - guard["z"]
                distance = math.hypot(dx, dz)
                step = min(speed * dt, distance)
                if distance > 0:
                    guard["x"] += dx / distance * step
                    guard["z"] += dz / distance * step
                    guard["root"].rotation_y = math.degrees(math.atan2(dx, dz))
                if distance < 0.06:
                    guard["path"].pop(0)
            elif chasing and (
                int(guard["x"]),
                int(guard["z"]),
            ) == (
                int(chase_target["x"])
                if chasing_neighbor or pursuing_transformed_neighbor
                else int(self.player.x),
                int(chase_target["z"])
                if chasing_neighbor or pursuing_transformed_neighbor
                else int(self.player.z),
            ):
                target_x = (
                    chase_target["x"]
                    if chasing_neighbor or pursuing_transformed_neighbor
                    else self.player.x
                )
                target_z = (
                    chase_target["z"]
                    if chasing_neighbor or pursuing_transformed_neighbor
                    else self.player.z
                )
                dx = target_x - guard["x"]
                dz = target_z - guard["z"]
                distance = math.hypot(dx, dz)
                step = min(speed * dt, distance)
                if distance > 0:
                    move_x = dx / distance * step
                    move_z = dz / distance * step
                    next_x = guard["x"] + move_x
                    next_z = guard["z"] + move_z
                    radius = 0.22
                    if not any(
                        self.is_wall(next_x + offset_x, next_z + offset_z)
                        for offset_x in (-radius, radius)
                        for offset_z in (-radius, radius)
                    ):
                        guard["x"] = next_x
                        guard["z"] = next_z
                        guard["root"].rotation_y = math.degrees(
                            math.atan2(move_x, move_z)
                        )

            gait = math.sin(now * 7 + guard["phase"]) * 24
            saluting = now < guard.get("saluting_until", 0.0)
            throwing = now < guard.get("throwing_until", 0.0)
            for limb, rotation in zip(
                guard["limbs"],
                (
                    105 if throwing else -115 if saluting else gait,
                    -25 if saluting and not throwing else -gait,
                    -gait,
                    gait,
                ),
            ):
                limb.rotation_x = rotation
            guard["root"].position = (
                guard["x"],
                max(0, math.sin(now * 14 + guard["phase"]) * 0.025),
                guard["z"],
            )
            package_glow = guard.get("package_glow")
            if package_glow is not None and package_glow.enabled:
                pulse = 0.5 + 0.5 * math.sin(now * 4.0 + guard["phase"])
                package_glow.scale = (
                    1.2 + pulse * 0.16,
                    2.0 + pulse * 0.2,
                    1,
                )
                package_glow.color = color.rgba(
                    255,
                    int(168 + pulse * 35),
                    35,
                    int(145 + pulse * 55),
                )
            guard["head"].rotation_y = math.sin(now * 1.3 + guard["phase"]) * 5

            if distance_to_player < 0.58:
                self.player.position = PLAYER_START
                self.candy_count = max(0, self.candy_count - 1)
                self.mission_time_bonus -= 10
                self.set_message("Caught! You dropped a treat and lost 10 seconds.")
                break

        self.update_neighbor_greetings(now)

    def refresh_hud(self):
        self.next_hud_refresh = clock.monotonic() + 0.1
        remaining = max(
            0,
            MISSION_SECONDS
            - (clock.monotonic() - self.mission_started)
            + self.mission_time_bonus,
        )
        self.stats_text.text = (
            f"BAG {self.candy_count}/{self.bag_capacity}   "
            f"HOUSES {self.visited_houses}/{len(HOUSE_POSITIONS)}   "
            f"RETURNED {self.treats_returned}/5   "
            f"TIME {int(remaining // 60):02}:{int(remaining % 60):02}   "
            f"SPRINT {int(self.sprint_energy)}%   FLASHLIGHT {int(self.torch_charge)}%"
            + (
                f"   SUPER SPEED {max(0, int(self.player_speed_boost_until - clock.monotonic()))}s"
                if self.player_speed_boost_until > clock.monotonic()
                else ""
            )
        )
        if self.map_visible:
            rows = []
            for z, row in enumerate(self.grid):
                chars = []
                for x, cell in enumerate(row):
                    if (int(self.player.x), int(self.player.z)) == (x, z):
                        chars.append("@")
                    elif (x, z) == tuple(map(int, PACKAGE_RETURN_POSITION)):
                        chars.append("R")
                    elif self.return_zone_contains_cell(x, z):
                        chars.append("r")
                    elif any(
                        not snack["collected"]
                        and (int(snack["x"]), int(snack["z"])) == (x, z)
                        for snack in self.snacks
                    ):
                        chars.append("*")
                    elif any(
                        not house["visited"]
                        and (int(house["x"]), int(house["z"])) == (x, z)
                        for house in self.house_state
                    ):
                        chars.append("h")
                    elif any(
                        house["visited"]
                        and (int(house["x"]), int(house["z"])) == (x, z)
                        for house in self.house_state
                    ):
                        chars.append("d")
                    elif any(
                        not prop["used"]
                        and (int(prop["position"][0]), int(prop["position"][1]))
                        == (x, z)
                        for prop in self.interactable_entities
                    ):
                        chars.append("!")
                    elif any(
                        not guard.get("eliminated", False)
                        and guard.get(
                            "is_officer",
                            guard["model_controlled"],
                        )
                        and (int(guard["x"]), int(guard["z"])) == (x, z)
                        for guard in self.guard_entities
                    ):
                        chars.append("P")
                    elif any(
                        not guard.get("eliminated", False)
                        and not guard.get(
                            "is_officer",
                            guard["model_controlled"],
                        )
                        and (int(guard["x"]), int(guard["z"])) == (x, z)
                        for guard in self.guard_entities
                    ):
                        chars.append("G")
                    elif cell in ("#", "H"):
                        chars.append("#")
                    elif cell == "T":
                        chars.append("T")
                    else:
                        chars.append(".")
                rows.append("".join(chars))
            self.map_text.text = (
                "MAP  @ You  P Officers  G Neighbors  h House  d Visited  "
                "! Item  * Treat  R/r Package Return\n" + "\n".join(rows)
            )

    @staticmethod
    def return_zone_contains_cell(cell_x, cell_z):
        center_x, center_z = PACKAGE_RETURN_POSITION
        nearest_x = min(max(center_x, cell_x), cell_x + 1)
        nearest_z = min(max(center_z, cell_z), cell_z + 1)
        return (
            math.hypot(center_x - nearest_x, center_z - nearest_z)
            <= PACKAGE_RETURN_RADIUS
        )

    def end_game(self, won):
        self.game_over = True
        self.end_text.text = (
            "SHIFT OVER\nYou survived the night\n\n"
            "ENTER — play again\nR — release cursor"
            if won
            else "TIME'S UP\n\nENTER — try again\nR — release cursor"
        )
        self.end_text.enabled = True
        self.capture_text.enabled = False

    def capture_mouse(self):
        mouse.locked = False
        mouse.visible = False
        window.set_mouse_mode(window.M_confined)
        self.app.win.requestProperties(window)
        self.mouse_captured = True
        self.capture_text.enabled = False

    def release_mouse(self):
        mouse.locked = False
        mouse.visible = True
        self.mouse_captured = False
        self.capture_text.enabled = not self.game_over

    def input(self, key):
        if key == "escape":
            self.app.userExit()
        elif key == "p":
            self.set_photo_mode(not self.photo_mode)
        elif key == "left mouse down" and not mouse.locked and not self.game_over:
            self.capture_mouse()
        elif key == "r":
            self.release_mouse()
        elif key == "enter" and self.game_over:
            self.reset()
            self.capture_mouse()
        elif key == "e" and not self.game_over:
            self.interact()
        elif key == "q" and not self.game_over:
            self.interact(share=True)
        elif key == "f":
            if self.torch_charge > 0:
                self.torch_on = not self.torch_on
                self.torch.enabled = self.torch_on
                self.set_message(
                    "Flashlight on" if self.torch_on else "Flashlight off",
                    1.2,
                )
        elif key == "tab":
            self.map_visible = not self.map_visible
            self.map_text.enabled = self.map_visible
        elif key == "u":
            self.audio_enabled = not self.audio_enabled
            self.ambient_audio.volume = 0.28 if self.audio_enabled else 0
            self.set_message(
                "Ambient audio on" if self.audio_enabled else "Ambient audio off",
                1.5,
            )
