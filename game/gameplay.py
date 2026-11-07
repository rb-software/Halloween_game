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

from ursina import Entity, Vec3, color, destroy, held_keys, mouse, time, window

from .config import (
    AI_DECISION_INTERVAL,
    HOUSE_NAMES,
    HOUSE_POSITIONS,
    MISSION_SECONDS,
    PLAYER_SPEED,
    PLAYER_START,
    PLAYER_START_ROTATION,
    SNACK_COLORS,
    SNACK_STARTS,
)
from .models import HouseState, SnackState


class GameplayMixin:
    def reset(self):
        self.ai_generation += 1
        self.player.position = PLAYER_START
        self.player.rotation_y = PLAYER_START_ROTATION
        self.look_pitch = 0
        self.camera_pivot.rotation_x = 0
        self.score = 0
        self.candy_count = 0
        self.bag_capacity = 5
        self.treats_collected = 0
        self.visited_houses = 0
        self.mission_started = clock.monotonic()
        self.mission_time_bonus = 0
        self.sprint_energy = 100.0
        self.torch_charge = 100.0
        self.torch_on = True
        self.torch.enabled = True
        self.game_over = False
        self.map_visible = False
        self.map_text.enabled = False
        self.message = ""
        self.message_until = 0.0
        self.greeting_cooldowns = {}
        self.patrol_cells = [
            (x, z)
            for z, row in enumerate(self.grid)
            for x, _ in enumerate(row)
            if not self.is_wall(x + 0.5, z + 0.5)
        ]
        starts = self.random_neighbor_positions(len(self.guard_entities))
        for index, guard in enumerate(self.guard_entities):
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
            )
            guard["greeting_bubble"].enabled = False
            guard["root"].position = (x, 0, z)
            guard["root"].rotation_y = 0
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
        for index, (x, z, kind) in enumerate(SNACK_STARTS):
            candy = Entity(
                model="sphere" if kind == "lollipop" else "cube",
                position=(x, 0.42, z),
                scale=(0.34, 0.46, 0.34) if kind == "lollipop" else (0.42, 0.34, 0.3),
                color=SNACK_COLORS[index % len(SNACK_COLORS)],
                texture=self.wrapper_texture,
            )
            wrapper_fold = Entity(
                model="cube",
                position=(x + 0.2, 0.42, z),
                scale=(0.12, 0.2, 0.22),
                rotation=(18, 23, 12),
                color=SNACK_COLORS[(index + 2) % len(SNACK_COLORS)],
                texture=self.wrapper_texture,
            )
            self.snack_entities.append([candy, wrapper_fold])
            self.snacks.append(
                {
                    "x": x,
                    "z": z,
                    "phase": index * 0.71,
                    "kind": kind,
                    "collected": False,
                    "path": [],
                    "repath_at": 0.0,
                    "entities": (candy, wrapper_fold),
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
        for guard in self.guard_entities:
            if now >= guard["greeting_until"]:
                guard["greeting_bubble"].enabled = False

        for first_index, first in enumerate(self.guard_entities):
            for second_index in range(first_index + 1, len(self.guard_entities)):
                second = self.guard_entities[second_index]
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
                    guard["greeting_bubble"].enabled = True
                self.greeting_cooldowns[pair] = now + 5.0

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
        speed = PLAYER_SPEED * (1.65 if sprinting else 1.0)
        if sprinting:
            self.sprint_energy = max(0.0, self.sprint_energy - 28 * dt)
        else:
            self.sprint_energy = min(100.0, self.sprint_energy + 12 * dt)
        if self.candy_count >= self.bag_capacity:
            speed *= 0.82

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

    def interact(self, share=False):
        if not share:
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
        if self.visited_houses == len(self.house_state) and self.treats_collected >= 5:
            self.end_game(True)
        self.refresh_hud()

    def update_snacks(self, dt, now):
        for snack in self.snacks:
            if snack["collected"]:
                continue
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
                snack["x"] += dx / distance_to_goal * step
                snack["z"] += dz / distance_to_goal * step
                for index, entity in enumerate(snack["entities"]):
                    entity.x = snack["x"]
                    entity.z = snack["z"]
                    if index == 1:
                        entity.x += 0.2
                        entity.y = snack["entities"][0].y
            if distance_to_goal < 0.06:
                snack["path"].pop(0)

    def update_guard(self, dt, now):
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
                if not guard["model_controlled"]
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

        for guard_index, guard in enumerate(self.guard_entities):
            distance_to_player = math.hypot(
                self.player.x - guard["x"],
                self.player.z - guard["z"],
            )
            chasing = (
                guard_index == active_chaser
                and distance_to_player < guard["chase_radius"]
            )
            if guard["model_controlled"]:
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
            elif now >= guard["repath_at"] or not guard["path"]:
                if chasing:
                    goal = (int(self.player.x), int(self.player.z))
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
            speed = guard["chase_speed"] if chasing else guard["speed"]
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
            ) == (int(self.player.x), int(self.player.z)):
                dx = self.player.x - guard["x"]
                dz = self.player.z - guard["z"]
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
            for limb, rotation in zip(
                guard["limbs"],
                (gait, -gait, -gait, gait),
            ):
                limb.rotation_x = rotation
            guard["root"].position = (
                guard["x"],
                max(0, math.sin(now * 14 + guard["phase"]) * 0.025),
                guard["z"],
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
            f"TREATS {self.treats_collected}/5   "
            f"TIME {int(remaining // 60):02}:{int(remaining % 60):02}   "
            f"SPRINT {int(self.sprint_energy)}%   FLASHLIGHT {int(self.torch_charge)}%"
        )
        if self.map_visible:
            rows = []
            for z, row in enumerate(self.grid):
                chars = []
                for x, cell in enumerate(row):
                    if (int(self.player.x), int(self.player.z)) == (x, z):
                        chars.append("@")
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
                        guard["model_controlled"]
                        and (int(guard["x"]), int(guard["z"])) == (x, z)
                        for guard in self.guard_entities
                    ):
                        chars.append("A")
                    elif any(
                        not guard["model_controlled"]
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
                "MAP  @ You  A AI neighbor  G Neighbors  h House  d Visited  "
                "! Item  * Treat\n" + "\n".join(rows)
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
