import math
import random
from copy import deepcopy

from ursina import Entity, PointLight, Text, color

from .config import (
    FOREST_TREE_CELLS,
    HOUSE_POSITIONS,
    HOUSE_ROTATIONS,
    PLAZA_CENTER,
    POLICE_CAR_POSITION,
    TOWN_HEIGHT,
)
from .geometry import (
    create_fire_texture,
    create_mist_texture,
    create_ocean_mesh,
    create_section_mesh,
    create_smoke_texture,
    create_spark_texture,
    enable_alpha_blending,
)


class WorldBuilder:
    def build_world(self):
        ground = Entity(
            model=deepcopy(self.displaced_asphalt_model),
            scale=(self.map_width, 1, self.map_height),
            position=(self.map_width / 2, -0.06, self.map_height / 2),
            color=color.rgb(205, 205, 196),
            texture=self.ground_texture,
            double_sided=True,
        )
        ground.texture_scale = (self.map_width / 5, self.map_height / 5)

        road_cells = {
            (x, z)
            for z in range(self.map_height)
            for x in range(self.map_width)
            if abs(z - 13) <= 2 or abs(x - 17) <= 3 or abs(x - 26) <= 2
        }
        sidewalk_cells = set()
        for z in range(TOWN_HEIGHT):
            for x in range(self.map_width):
                if self.grid[z][x] == "#":
                    continue
                if (x, z) in road_cells:
                    continue
                if any(
                    self.is_wall(x + dx, z + dz)
                    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
                ) or (abs(z - 13) == 2 or abs(x - 17) == 3 or abs(x - 26) == 2):
                    sidewalk_cells.add((x, z))

        for x, z in sorted(sidewalk_cells):
            slab = Entity(
                model=deepcopy(self.displaced_concrete_model),
                position=(x + 0.5, -0.012, z + 0.5),
                scale=(0.99, 0.035, 0.99),
                color=color.rgb(226, 224, 211),
                texture=self.sidewalk_texture,
            )
            slab.texture_scale = (1, 1)
            self.apply_surface_material(slab, "concrete")

        self.build_road_network()

        for z, row in enumerate(self.grid):
            if z == 0:
                continue
            x = 0
            while x < self.map_width:
                if row[x] != "#":
                    x += 1
                    continue
                start_x = x
                while x + 1 < self.map_width and row[x + 1] == "#":
                    x += 1
                end_x = x
                length = end_x - start_x + 1
                wall_color = color.rgb(
                    random.randint(207, 232),
                    random.randint(203, 228),
                    random.randint(190, 215),
                )
                wall_material = (
                    "brick" if (start_x // 3 + z // 4) % 5 == 0 else "plaster"
                )
                wall = Entity(
                    model=deepcopy(
                        self.brick_wall_model
                        if wall_material == "brick"
                        else self.displaced_wall_model
                    ),
                    position=((start_x + end_x + 1) / 2, 3.15, z + 0.5),
                    scale=(length, 6.0, 1),
                    color=wall_color,
                    texture=(
                        self.brick_texture
                        if wall_material == "brick"
                        else self.wall_texture
                    ),
                )
                wall.texture_scale = (length * 0.9, 2.6)
                self.apply_surface_material(wall, wall_material)
                dado = Entity(
                    model="cube",
                    position=((start_x + end_x + 1) / 2, 0.46, z + 0.5),
                    scale=(length, 0.92, 1),
                    color=color.rgb(183, 177, 159),
                    texture=self.concrete_texture,
                )
                dado.texture_scale = (length, 1)
                for band_y, band_color in (
                    (0.93, color.rgb(74, 82, 69)),
                    (0.99, color.rgb(143, 137, 116)),
                    (2.65, color.rgb(164, 159, 145)),
                    (4.65, color.rgb(164, 159, 145)),
                    (5.85, color.rgb(164, 159, 145)),
                ):
                    band = Entity(
                        model="cube",
                        position=((start_x + end_x + 1) / 2, band_y, z + 0.5),
                        scale=(length + 0.025, 0.055, 1.015),
                        color=band_color,
                        texture=self.concrete_texture,
                    )
                    self.apply_surface_material(band, "concrete")
                cap = Entity(
                    model="cube",
                    position=((start_x + end_x + 1) / 2, 6.28, z + 0.5),
                    scale=(length + 0.12, 0.1, 1.12),
                    color=color.rgb(214, 207, 187),
                    texture=self.concrete_texture,
                )
                self.apply_surface_material(cap, "concrete")
                roof_ledge = Entity(
                    model="cube",
                    position=((start_x + end_x + 1) / 2, 6.42, z + 0.5),
                    scale=(length + 0.28, 0.22, 1.28),
                    color=color.rgb(158, 151, 133),
                    texture=self.concrete_texture,
                )
                self.apply_surface_material(roof_ledge, "concrete")
                for pipe_x in (start_x + 0.12, end_x + 0.88):
                    Entity(
                        model=self.cylinder_model,
                        position=(pipe_x, 3.15, z - 0.035),
                        scale=(0.045, 6.0, 0.045),
                        color=color.rgb(89, 91, 84),
                        texture=self.metal_texture,
                    )
                for wall_x in range(start_x, end_x + 1):
                    self.add_wall_windows(wall_x, z)
                x += 1
        self.build_street_furniture()

    def build_forest(self):
        Entity(
            model="plane",
            position=(
                self.map_width / 2,
                -0.012,
                (TOWN_HEIGHT + self.map_height) / 2,
            ),
            scale=(self.map_width, 1, self.map_height - TOWN_HEIGHT),
            color=color.rgb(91, 116, 76),
            texture=self.ground_texture,
            double_sided=True,
        )
        trail = Entity(
            model="plane",
            position=(17.5, 0.012, (TOWN_HEIGHT + 45) / 2),
            scale=(4.4, 1, 45 - TOWN_HEIGHT),
            color=color.rgb(133, 119, 88),
            texture=self.sidewalk_texture,
            double_sided=True,
        )
        trail.texture_scale = (1, 7)
        rng = random.Random(1986)
        foliage_colors = (
            color.rgb(43, 75, 54),
            color.rgb(51, 86, 60),
            color.rgb(58, 91, 62),
            color.rgb(65, 96, 66),
        )
        for x, z in FOREST_TREE_CELLS:
            center_x, center_z = x + 0.5, z + 0.5
            height = rng.uniform(6.8, 9.0)
            Entity(
                model=self.cylinder_model,
                position=(center_x, height * 0.2, center_z),
                scale=(0.42, height * 0.4, 0.42),
                color=color.rgb(91, 69, 49),
                texture=self.wood_texture,
            )
            for tier, (height_fraction, width_fraction) in enumerate(
                ((0.38, 0.48), (0.58, 0.39), (0.77, 0.29))
            ):
                Entity(
                    model=self.cone_model,
                    position=(center_x, height * height_fraction, center_z),
                    scale=(
                        height * width_fraction,
                        height * 0.5,
                        height * width_fraction,
                    ),
                    color=foliage_colors[(tier + x + z) % len(foliage_colors)],
                )
        self.build_campfire()
        mist_texture = create_mist_texture()
        self.fog_banks = []
        for index, (x, z) in enumerate(((17.5, 30.5), (17.5, 36.5), (17.5, 42.5))):
            bank = Entity(
                model="plane",
                position=(x, 1.2, z),
                rotation_x=90,
                scale=(12, 1, 2.8),
                texture=mist_texture,
                color=color.rgba(193, 211, 216, 88),
                double_sided=True,
            )
            bank.set_light_off()
            enable_alpha_blending(bank)
            self.fog_banks.append(
                {"entity": bank, "x": x, "z": z, "phase": index * 2.1}
            )

    def build_campfire(self):
        x, z = 21.5, 35.5
        for offset, rotation_x, rotation_z in (
            (-0.16, 0, 90),
            (0.16, 0, 90),
            (0, 90, 0),
        ):
            Entity(
                model=self.cylinder_model,
                position=(x + offset, 0.16, z),
                rotation_x=rotation_x,
                rotation_z=rotation_z,
                scale=(0.16, 1.35, 0.16),
                color=color.rgb(91, 58, 38),
                texture=self.wood_texture,
            )

        for index in range(8):
            angle = math.tau * index / 8
            stone = Entity(
                model=self.cylinder_model,
                position=(x + math.cos(angle) * 0.88, 0.13, z + math.sin(angle) * 0.88),
                scale=(0.28, 0.22, 0.28),
                color=color.rgb(105 + index % 3 * 5, 99 + index % 2 * 4, 82),
                texture=self.concrete_texture,
            )
            self.apply_surface_material(stone, "concrete")

        fire_texture = create_fire_texture()
        fire_layers = (
            ((-0.14, 0.52, -0.06), (0.66, 1.08, 1), color.rgba(255, 151, 51, 235)),
            ((0.12, 0.54, 0.02), (0.54, 0.94, 1), color.rgba(255, 191, 77, 225)),
            ((0.02, 0.56, 0.08), (0.38, 0.76, 1), color.rgba(255, 228, 136, 210)),
        )
        self.fire_flames = []
        for index, (position, scale, flame_color) in enumerate(fire_layers):
            flame = Entity(
                model="quad",
                texture=fire_texture,
                position=(x + position[0], position[1], z + position[2]),
                scale=scale,
                rotation=(0, index * 37, index * 9 - 8),
                color=flame_color,
                billboard=True,
                double_sided=True,
                unlit=True,
            )
            flame.set_light_off()
            enable_alpha_blending(flame)
            self.fire_flames.append(
                {"entity": flame, "scale": scale, "phase": index * 1.7}
            )
        self.fire_particle_rng = random.Random(1987)
        spark_texture = create_spark_texture()
        self.fire_particles = []
        for _ in range(24):
            particle = Entity(
                model="quad",
                texture=spark_texture,
                position=(x, 0.7, z),
                scale=0.08,
                color=color.rgba(255, 140, 48, 0),
                billboard=True,
                unlit=True,
            )
            enable_alpha_blending(particle)
            spark = {
                "entity": particle,
                "age": 0.0,
                "lifetime": 1.0,
                "speed": 1.0,
                "drift_x": 0.0,
                "drift_z": 0.0,
                "size": 0.08,
                "phase": self.fire_particle_rng.uniform(0, math.tau),
            }
            self.reset_fire_particle(spark, x, z, randomize_age=True)
            self.fire_particles.append(spark)
        self.fire_light = PointLight(
            position=(x, 1.0, z),
            color=color.rgb(255, 126, 52),
        )
        self.fire_light.enabled = True

    def reset_fire_particle(self, particle, x, z, randomize_age=False):
        rng = self.fire_particle_rng
        particle["lifetime"] = rng.uniform(0.7, 1.45)
        particle["age"] = (
            rng.uniform(0.0, particle["lifetime"]) if randomize_age else 0.0
        )
        particle["speed"] = rng.uniform(0.8, 1.55)
        particle["drift_x"] = rng.uniform(-0.38, 0.38)
        particle["drift_z"] = rng.uniform(-0.38, 0.38)
        particle["size"] = rng.uniform(0.045, 0.105)
        particle["origin_x"] = x + rng.uniform(-0.28, 0.28)
        particle["origin_z"] = z + rng.uniform(-0.28, 0.28)

    def build_city_fires(self):
        fire_texture = create_fire_texture()
        smoke_texture = create_smoke_texture()
        self.city_fire_rng = random.Random(1990)
        self.city_fire_particles = []
        self.city_fire_cores = []
        self.city_fire_lights = []
        fire_sites = []
        for index in (0, 2, 4, 5, 6, 7):
            house_x, house_z = HOUSE_POSITIONS[index]
            front_sign = 1 if HOUSE_ROTATIONS[index] == 180 else -1
            site = (house_x, house_z + front_sign * 1.95)
            fire_sites.append(site)
            light = PointLight(
                position=(site[0], 2.8, site[1]),
                color=color.rgb(255, 95, 29),
            )
            light.enabled = True
            self.city_fire_lights.append({"entity": light, "phase": index * 1.31})
            for layer, (offset_x, height, width, flame_height) in enumerate(
                (
                    (-0.42, 2.0, 0.9, 1.9),
                    (0.08, 2.7, 1.05, 2.25),
                    (0.48, 2.25, 0.8, 1.75),
                )
            ):
                core = Entity(
                    model="quad",
                    texture=fire_texture,
                    position=(site[0] + offset_x, height, site[1]),
                    scale=(width, flame_height, 1),
                    color=color.rgba(255, 240, 205, 220),
                    billboard=True,
                    double_sided=True,
                    unlit=True,
                )
                enable_alpha_blending(core)
                self.city_fire_cores.append(
                    {
                        "entity": core,
                        "scale": (width, flame_height, 1),
                        "phase": index * 1.7 + layer * 2.2,
                    }
                )
            for _ in range(5):
                flame = Entity(
                    model="quad",
                    texture=fire_texture,
                    position=(site[0], 0.8, site[1]),
                    scale=(0.8, 1.45, 1),
                    color=color.rgba(255, 255, 255, 0),
                    billboard=True,
                    double_sided=True,
                    unlit=True,
                )
                flame.set_light_off()
                enable_alpha_blending(flame)
                particle = {"entity": flame, "kind": "flame", "site": site}
                self.reset_city_fire_particle(particle)
                self.city_fire_particles.append(particle)
            for _ in range(4):
                smoke = Entity(
                    model="quad",
                    texture=smoke_texture,
                    position=(site[0], 4.2, site[1]),
                    scale=(1.7, 2.4, 1),
                    color=color.rgba(132, 128, 120, 0),
                    billboard=True,
                    double_sided=True,
                    unlit=True,
                )
                smoke.set_light_off()
                enable_alpha_blending(smoke)
                particle = {"entity": smoke, "kind": "smoke", "site": site}
                self.reset_city_fire_particle(particle, randomize_age=True)
                self.city_fire_particles.append(particle)

    def reset_city_fire_particle(self, particle, randomize_age=False):
        rng = self.city_fire_rng
        x, z = particle["site"]
        if particle["kind"] == "flame":
            particle["lifetime"] = rng.uniform(0.62, 1.08)
            particle["age"] = (
                rng.uniform(0.0, particle["lifetime"]) if randomize_age else 0.0
            )
            particle["speed"] = rng.uniform(1.25, 2.0)
            particle["size"] = rng.uniform(0.85, 1.25)
            particle["drift_x"] = rng.uniform(-0.32, 0.32)
            particle["drift_z"] = rng.uniform(-0.12, 0.12)
            particle["origin_y"] = rng.uniform(1.0, 2.2)
        else:
            particle["lifetime"] = rng.uniform(2.8, 4.8)
            particle["age"] = (
                rng.uniform(0.0, particle["lifetime"]) if randomize_age else 0.0
            )
            particle["speed"] = rng.uniform(0.7, 1.1)
            particle["size"] = rng.uniform(1.3, 2.0)
            particle["drift_x"] = rng.uniform(-0.4, 0.4)
            particle["drift_z"] = rng.uniform(-0.18, 0.18)
            particle["origin_y"] = rng.uniform(3.4, 4.8)
        particle["origin_x"] = x + rng.uniform(-0.52, 0.52)
        particle["origin_z"] = z + rng.uniform(-0.16, 0.16)

    def build_coastline(self):
        beach = Entity(
            model="plane",
            position=(self.map_width / 2, -0.025, 0.72),
            scale=(self.map_width, 1, 1.44),
            color=color.rgb(174, 158, 124),
            texture=self.concrete_texture,
            double_sided=True,
        )
        beach.texture_scale = (self.map_width / 8, 1)
        self.ocean = Entity(
            model=create_ocean_mesh(self.map_width + 150, 150),
            position=(self.map_width / 2, -0.075, -75),
            shader=self.ocean_shader,
            double_sided=True,
        )
        self.ocean.set_shader_input("environment_map", self.sky_texture)
        self.ocean.set_shader_input("fog_color", self.fog_color)
        self.ocean.set_shader_input("fog_density", self.fog_density)
        self.ocean.set_shader_input("water_time", 0.0)

        for x, z, label in ((2.5, 6.5, "THE ESTATE"), (13.5, 2.5, "PSS")):
            sign = Entity(
                model="cube",
                position=(x, 2.5, z),
                scale=(1.6, 0.75, 0.1),
                color=color.rgb(91, 86, 72),
                texture=self.metal_texture,
            )
            Text(
                parent=sign,
                text=label,
                origin=(0, 0),
                scale=5,
                color=color.rgb(220, 198, 147),
                position=(0, 0, -0.56),
            )

    def build_road_network(self):
        roads = (
            (
                (self.map_width / 2, 0.006, 13.5),
                (self.map_width - 2, 1, 4.7),
                (self.map_width / 5, 1),
            ),
            (
                (17.5, 0.008, TOWN_HEIGHT / 2),
                (6.2, 1, TOWN_HEIGHT - 2),
                (1, TOWN_HEIGHT / 5),
            ),
            (
                (26.5, 0.008, TOWN_HEIGHT / 2),
                (4.7, 1, TOWN_HEIGHT - 2),
                (1, TOWN_HEIGHT / 5),
            ),
        )
        for position, scale, texture_scale in roads:
            road = Entity(
                model=deepcopy(self.displaced_asphalt_model),
                position=position,
                scale=scale,
                color=color.rgb(222, 222, 211),
                texture=self.ground_texture,
                double_sided=True,
            )
            road.texture_scale = texture_scale
            self.apply_surface_material(road, "asphalt")

        for x in range(2, self.map_width - 2, 4):
            Entity(
                model="cube",
                position=(x + 0.5, 0.018, 13.5),
                scale=(1.5, 0.012, 0.035),
                color=color.rgb(157, 151, 126),
            )
        for x in (17.5, 26.5):
            for z in range(2, TOWN_HEIGHT - 2, 4):
                Entity(
                    model="cube",
                    position=(x, 0.02, z + 0.5),
                    scale=(0.035, 0.012, 1.5),
                    color=color.rgb(157, 151, 126),
                )

        for crossing_x in (17.5, 26.5):
            for offset in range(-4, 5):
                Entity(
                    model="cube",
                    position=(crossing_x + offset * 0.24, 0.023, 13.5),
                    scale=(0.11, 0.012, 2.1),
                    color=color.rgb(166, 162, 146),
                )
            Entity(
                model="cube",
                position=(crossing_x - 1.55, 0.015, 13.5),
                scale=(0.16, 0.07, 3.1),
                color=color.rgb(93, 91, 83),
                texture=self.concrete_texture,
            )
            Entity(
                model="cube",
                position=(crossing_x + 1.55, 0.015, 13.5),
                scale=(0.16, 0.07, 3.1),
                color=color.rgb(93, 91, 83),
                texture=self.concrete_texture,
            )

    def build_plaza(self):
        x, z = PLAZA_CENTER
        plaza = Entity(
            model=deepcopy(self.paving_model),
            position=(x, 0.008, z),
            scale=(8, 1, 8),
            color=color.rgb(228, 222, 205),
            texture=self.paving_texture,
            double_sided=True,
        )
        plaza.texture_scale = (4, 4)
        self.apply_surface_material(plaza, "paving")
        car_x, car_z = POLICE_CAR_POSITION
        for side in (-1, 1):
            Entity(
                model="cube",
                position=(car_x + side * 1.38, 0.023, car_z),
                scale=(0.045, 0.012, 6.2),
                color=color.rgb(187, 178, 151),
            )

    def add_wall_windows(self, x, z):
        for window_y in (1.55, 3.55, 5.55):
            self.add_facade_window(x, z, window_y)

    def add_facade_window(self, x, z, window_y):
        openings = (
            (self.is_wall(x, z - 1), "front"),
            (self.is_wall(x, z + 1), "back"),
            (self.is_wall(x - 1, z), "left"),
            (self.is_wall(x + 1, z), "right"),
        )
        for blocked, side in openings:
            if blocked:
                continue
            if side in ("front", "back"):
                if x % 2 == 0:
                    continue
                face_z = z if side == "front" else z + 1
                frame_position = (x + 0.5, window_y, face_z)
                pane_position = (
                    x + 0.5,
                    window_y,
                    face_z + (-0.026 if side == "front" else 0.026),
                )
                frame_scale = (0.62, 0.94, 0.07)
                pane_scale = (0.47, 0.74, 0.025)
                sill_position = (x + 0.5, window_y - 0.5, face_z)
                sill_scale = (0.75, 0.09, 0.18)
                mullion_position = (
                    x + 0.5,
                    window_y,
                    face_z + (-0.047 if side == "front" else 0.047),
                )
                mullion_scale = (0.045, 0.78, 0.035)
                crossbar_position = (
                    x + 0.5,
                    window_y,
                    face_z + (-0.047 if side == "front" else 0.047),
                )
                crossbar_scale = (0.56, 0.045, 0.035)
            else:
                face_x = x if side == "left" else x + 1
                frame_position = (face_x, window_y, z + 0.5)
                pane_position = (
                    face_x + (-0.026 if side == "left" else 0.026),
                    window_y,
                    z + 0.5,
                )
                frame_scale = (0.07, 0.94, 0.62)
                pane_scale = (0.025, 0.74, 0.47)
                sill_position = (face_x, window_y - 0.5, z + 0.5)
                sill_scale = (0.18, 0.09, 0.75)
                mullion_position = (
                    face_x + (-0.047 if side == "left" else 0.047),
                    window_y,
                    z + 0.5,
                )
                mullion_scale = (0.035, 0.78, 0.045)
                crossbar_position = (
                    face_x + (-0.047 if side == "left" else 0.047),
                    window_y,
                    z + 0.5,
                )
                crossbar_scale = (0.035, 0.045, 0.56)

            Entity(
                model="cube",
                position=frame_position,
                scale=frame_scale,
                color=color.rgb(84, 81, 73),
                texture=self.wood_texture,
            )
            glass_color = (
                color.rgb(54, 63, 66),
                color.rgb(67, 70, 66),
                color.rgb(43, 53, 57),
                color.rgb(78, 68, 55),
            )[(x * 13 + z * 7 + int(window_y * 10)) % 4]
            pane = Entity(
                model="cube",
                position=pane_position,
                scale=pane_scale,
                color=color.rgba(
                    int(glass_color.r * 255),
                    int(glass_color.g * 255),
                    int(glass_color.b * 255),
                    118,
                ),
            )
            enable_alpha_blending(pane)
            Entity(
                model="cube",
                position=sill_position,
                scale=sill_scale,
                color=color.rgb(106, 104, 95),
                texture=self.concrete_texture,
            )
            Entity(
                model="cube",
                position=mullion_position,
                scale=mullion_scale,
                color=color.rgb(92, 89, 80),
                texture=self.wood_texture,
            )
            Entity(
                model="cube",
                position=crossbar_position,
                scale=crossbar_scale,
                color=color.rgb(92, 89, 80),
                texture=self.wood_texture,
            )
            if (
                side in ("front", "back")
                and window_y > 2.0
                and (x + int(window_y * 10)) % 4 == 0
            ):
                outward = -1 if side == "front" else 1
                slab = Entity(
                    model="cube",
                    position=(x + 0.5, window_y - 0.48, face_z + outward * 0.22),
                    scale=(0.96, 0.07, 0.48),
                    color=color.rgb(122, 118, 104),
                    texture=self.concrete_texture,
                )
                self.apply_surface_material(slab, "concrete")
                rail_z = face_z + outward * 0.43
                Entity(
                    model="cube",
                    position=(x + 0.5, window_y - 0.18, rail_z),
                    scale=(0.92, 0.035, 0.035),
                    color=color.rgb(79, 83, 77),
                    texture=self.metal_texture,
                )
                for post_x in (x + 0.08, x + 0.92):
                    Entity(
                        model="cube",
                        position=(post_x, window_y - 0.34, rail_z),
                        scale=(0.035, 0.28, 0.035),
                        color=color.rgb(79, 83, 77),
                        texture=self.metal_texture,
                    )

    def build_street_furniture(self):
        for x, z in (
            (2.25, 3.5),
            (9.7, 2.5),
            (14.65, 5.5),
            (8.35, 10.5),
            (16.0, 10.0),
            (29.0, 16.0),
            (8.5, 18.5),
            (24.5, 24.5),
            (32.5, 15.5),
            (20.0, 17.5),
            (28.5, 10.5),
            (16.0, 18.5),
        ):
            if self.is_wall(x, z):
                continue
            Entity(
                model=self.cylinder_model,
                position=(x, 2.0, z),
                scale=(0.07, 4.0, 0.07),
                color=color.rgb(75, 78, 68),
                texture=self.metal_texture,
            )
            Entity(
                model=self.cylinder_model,
                position=(x + 0.13, 3.92, z),
                scale=(0.045, 0.45, 0.045),
                rotation_z=90,
                color=color.rgb(77, 81, 70),
                texture=self.metal_texture,
            )
            Entity(
                model=self.cone_model,
                position=(x + 0.32, 3.82, z),
                scale=(0.3, 0.19, 0.24),
                rotation_z=180,
                color=color.rgb(93, 97, 82),
                texture=self.metal_texture,
            )
            Entity(
                model="sphere",
                position=(x + 0.32, 3.71, z),
                scale=(0.12, 0.08, 0.12),
                color=color.rgb(153, 129, 91),
                unlit=True,
            )

        for x, z in (
            (3.0, 7.2),
            (10.0, 3.3),
            (15.0, 9.8),
            (18.5, 11.5),
            (23.5, 11.5),
            (16.0, 20.5),
            (14.5, 24.5),
            (28.5, 24.5),
        ):
            if self.is_wall(x, z):
                continue
            Entity(
                model=self.cylinder_model,
                position=(x, 0.43, z),
                scale=(0.42, 0.82, 0.42),
                color=color.rgb(220, 216, 193),
                texture=self.metal_texture,
                texture_scale=(1, 2),
            )
            Entity(
                model=self.cylinder_model,
                position=(x, 0.86, z),
                scale=(0.44, 0.08, 0.44),
                color=color.rgb(61, 72, 61),
            )
            Entity(
                model=self.cylinder_model,
                position=(x, 0.85, z),
                scale=(0.34, 0.025, 0.34),
                color=color.rgb(133, 130, 116),
                texture=self.metal_texture,
            )

        for x, z in ((2.5, 11.2), (9.5, 17.5), (14.5, 23.5), (14.5, 19.5)):
            if self.is_wall(x, z):
                continue
            Entity(
                model="cube",
                position=(x, 0.34, z),
                scale=(1.36, 0.1, 0.4),
                color=color.rgb(87, 78, 62),
                texture=self.wood_texture,
            )
            for slat_z in (-0.12, 0, 0.12):
                Entity(
                    model="cube",
                    position=(x, 0.405, z + slat_z),
                    scale=(1.34, 0.035, 0.035),
                    color=color.rgb(111, 86, 58),
                    texture=self.wood_texture,
                )
            for leg_x in (-0.48, 0.48):
                Entity(
                    model=self.cylinder_model,
                    position=(x + leg_x, 0.16, z),
                    scale=(0.045, 0.38, 0.045),
                    color=color.rgb(60, 62, 54),
                    texture=self.metal_texture,
                )
            Entity(
                model="cube",
                position=(x, 0.58, z + 0.16),
                scale=(1.3, 0.38, 0.1),
                color=color.rgb(87, 78, 62),
                texture=self.wood_texture,
            )
            for slat_y in (0.48, 0.58, 0.68):
                Entity(
                    model="cube",
                    position=(x, slat_y, z + 0.215),
                    scale=(1.24, 0.045, 0.025),
                    color=color.rgb(105, 81, 57),
                    texture=self.wood_texture,
                )

        for x, z in ((19.3, 6.5), (28.0, 7.5), (8.5, 24.4), (28.1, 24.6)):
            if self.is_wall(x, z):
                continue
            Entity(
                model=self.cylinder_model,
                position=(x, 0.42, z),
                scale=(0.29, 0.82, 0.29),
                color=color.rgb(80, 91, 74),
                texture=self.wood_texture,
            )
            Entity(
                model=self.cylinder_model,
                position=(x, 0.86, z),
                scale=(0.31, 0.08, 0.31),
                color=color.rgb(61, 68, 57),
            )
            Entity(
                model="cube",
                position=(x, 0.58, z - 0.18),
                scale=(0.1, 0.08, 0.025),
                color=color.rgb(194, 179, 137),
            )

        for index, (x, z) in enumerate(
            ((19.3, 11.6), (28.3, 11.6), (8.4, 17.6), (19.4, 24.6))
        ):
            if self.is_wall(x, z):
                continue
            planter_base = Entity(
                model=self.cylinder_model,
                position=(x, 0.09, z),
                scale=(0.38, 0.2, 0.38),
                color=color.rgb(97, 79, 59),
                texture=self.concrete_texture,
            )
            self.apply_surface_material(planter_base, "concrete")
            Entity(
                model=self.cylinder_model,
                position=(x, 0.78, z),
                scale=(0.07, 1.4, 0.07),
                color=color.rgb(88, 75, 54),
                texture=self.wood_texture,
            )
            for leaf_index, (leaf_y, leaf_scale) in enumerate(
                ((0.82, 0.62), (1.22, 0.5), (1.57, 0.34), (1.1, 0.4), (1.42, 0.38))
            ):
                offset_x = 0 if leaf_index < 3 else (-0.24 if leaf_index == 3 else 0.24)
                Entity(
                    model=self.cone_model,
                    position=(
                        x + offset_x,
                        leaf_y,
                        z + (0.18 if leaf_index == 4 else 0),
                    ),
                    scale=(leaf_scale, leaf_scale * 1.05, leaf_scale),
                    color=color.rgb(46 + index * 2, 68 + (leaf_index % 2) * 6, 42),
                )

    def build_landmark(self):
        x, z = 12.5, 21.5
        base = color.rgb(138, 134, 123)
        stone = color.rgb(164, 158, 142)
        landmark_base = Entity(
            model=deepcopy(self.displaced_concrete_model),
            position=(x, 7, z),
            scale=(5.2, 14, 4.2),
            color=base,
            texture=self.concrete_texture,
        )
        self.apply_surface_material(landmark_base, "concrete")
        landmark_cap = Entity(
            model=deepcopy(self.displaced_concrete_model),
            position=(x, 14.7, z),
            scale=(6.1, 1.6, 5),
            color=stone,
            texture=self.concrete_texture,
        )
        self.apply_surface_material(landmark_cap, "concrete")
        landmark_tower = Entity(
            model=deepcopy(self.displaced_concrete_model),
            position=(x, 16.2, z),
            scale=(3.1, 2, 3),
            color=base,
            texture=self.concrete_texture,
        )
        self.apply_surface_material(landmark_tower, "concrete")
        Entity(
            model="cube",
            position=(x, 17.7, z),
            scale=(1.4, 1.3, 1.4),
            color=stone,
            texture=self.stone_texture,
        )
        Entity(
            model="cube",
            position=(x, 18.45, z),
            scale=(2.0, 0.25, 2.0),
            color=stone,
            texture=self.stone_texture,
        )
        for level in range(5):
            y = 1.5 + level * 2.5
            for side in (-1, 1):
                Entity(
                    model="cube",
                    position=(x + side * 1.15, y + 0.25, z - 2.13),
                    scale=(0.38, 0.9, 0.03),
                    color=color.rgb(61, 69, 70),
                )
                Entity(
                    model="cube",
                    position=(x + side * 1.15, y - 0.32, z - 2.2),
                    scale=(0.72, 0.08, 0.22),
                    color=color.rgb(137, 125, 100),
                )
        for x_offset in (-1.9, 0, 1.9):
            Entity(
                model="cube",
                position=(x + x_offset, 8.5, z - 2.14),
                scale=(0.045, 14.0, 0.045),
                color=color.rgb(159, 147, 118),
                texture=self.stone_texture,
            )

    def build_police_car(self):
        x, z = POLICE_CAR_POSITION
        root = Entity(position=(x, 0, z), rotation_y=180)
        paint = color.rgb(207, 200, 175)
        Entity(
            parent=root,
            model=create_section_mesh(
                (
                    (-2.12, 0.72, 0.34, 0.72),
                    (-1.72, 0.82, 0.30, 0.84),
                    (-1.12, 0.88, 0.29, 0.87),
                    (1.32, 0.88, 0.29, 0.84),
                    (1.82, 0.80, 0.31, 0.76),
                    (2.10, 0.70, 0.35, 0.69),
                )
            ),
            color=paint,
            double_sided=True,
        )
        Entity(
            parent=root,
            model=create_section_mesh(
                (
                    (-1.02, 0.64, 0.83, 1.30),
                    (-0.68, 0.67, 0.84, 1.43),
                    (0.55, 0.66, 0.83, 1.41),
                    (0.98, 0.60, 0.79, 1.10),
                )
            ),
            color=paint,
            double_sided=True,
        )

        Entity(
            parent=root,
            model="cube",
            position=(0, 0.45, 0),
            scale=(1.67, 0.18, 3.4),
            color=color.rgb(79, 83, 72),
        )
        for side in (-1, 1):
            Entity(
                parent=root,
                model="cube",
                position=(side * 0.865, 0.48, 0),
                scale=(0.045, 0.09, 3.22),
                color=color.rgb(151, 145, 125),
            )
            for wheel_z in (-1.28, 1.28):
                Entity(
                    parent=root,
                    model=self.cylinder_model,
                    position=(side * 0.89, 0.42, wheel_z),
                    scale=(0.23, 0.72, 0.72),
                    rotation_z=90,
                    color=color.rgb(30, 32, 31),
                )
                Entity(
                    parent=root,
                    model=self.cylinder_model,
                    position=(side * 1.02, 0.42, wheel_z),
                    scale=(0.035, 0.36, 0.36),
                    rotation_z=90,
                    color=color.rgb(144, 141, 127),
                )

            for window_z in (-0.34, 0.40):
                pane = Entity(
                    parent=root,
                    model="cube",
                    position=(side * 0.674, 1.12, window_z),
                    scale=(0.035, 0.30, 0.62),
                    color=color.rgba(77, 111, 119, 150),
                )
                enable_alpha_blending(pane)
            for pillar_z in (-0.69, 0.04, 0.72):
                Entity(
                    parent=root,
                    model="cube",
                    position=(side * 0.69, 1.12, pillar_z),
                    scale=(0.055, 0.39, 0.065),
                    color=paint,
                )
            Entity(
                parent=root,
                model="cube",
                position=(side * 0.74, 1.02, -0.78),
                scale=(0.16, 0.045, 0.09),
                color=color.rgb(65, 69, 65),
            )
            Entity(
                parent=root,
                model="cube",
                position=(side * 0.91, 0.82, -0.13),
                scale=(0.025, 0.035, 0.15),
                color=color.rgb(138, 132, 113),
            )

        Entity(
            parent=root,
            model="cube",
            position=(0, 1.095, -0.97),
            scale=(1.12, 0.36, 0.04),
            rotation_x=23,
            color=color.rgb(45, 59, 63),
        )
        Entity(
            parent=root,
            model="cube",
            position=(0, 1.075, 0.92),
            scale=(1.02, 0.28, 0.04),
            rotation_x=-23,
            color=color.rgb(45, 59, 63),
        )
        Entity(
            parent=root,
            model="cube",
            position=(0, 0.88, -1.40),
            scale=(1.58, 0.08, 0.84),
            color=paint,
        )
        Entity(
            parent=root,
            model="cube",
            position=(0, 0.84, 1.56),
            scale=(1.53, 0.08, 0.47),
            color=paint,
        )
        Entity(
            parent=root,
            model="cube",
            position=(0, 0.62, -2.125),
            scale=(0.72, 0.32, 0.045),
            color=color.rgb(36, 40, 39),
        )
        for grille_y in (0.52, 0.59, 0.66, 0.73):
            Entity(
                parent=root,
                model="cube",
                position=(0, grille_y, -2.151),
                scale=(0.64, 0.018, 0.018),
                color=color.rgb(135, 135, 123),
            )

        for side in (-1, 1):
            Entity(
                parent=root,
                model="sphere",
                position=(side * 0.58, 0.67, -2.15),
                scale=(0.20, 0.18, 0.08),
                color=color.rgb(232, 219, 170),
            )
            Entity(
                parent=root,
                model="sphere",
                position=(side * 0.61, 0.64, 2.11),
                scale=(0.13, 0.18, 0.06),
                color=color.rgb(130, 49, 42),
            )
            Entity(
                parent=root,
                model="cube",
                position=(side * 0.22, 1.47, 0.03),
                scale=(0.32, 0.09, 0.42),
                color=color.rgb(68, 72, 67),
            )
            Entity(
                parent=root,
                model="sphere",
                position=(side * 0.22, 1.50, 0.03),
                scale=(0.22, 0.12, 0.18),
                color=color.rgb(180, 47, 40) if side < 0 else color.rgb(70, 104, 142),
                unlit=True,
            )
            (
                Text(
                    parent=root,
                    text="CIVIL MILITIA",
                    origin=(0, 0),
                    scale=0.9,
                    color=color.rgb(52, 54, 48),
                    position=(side * 0.90, 0.78, 0.04),
                    rotation=(0, 90, 0),
                ),
            )
        for side in (-1, 1):
            Entity(
                parent=root,
                model="cube",
                position=(side * 0.88, 0.98, 0.22),
                scale=(0.06, 0.045, 0.17),
                color=color.rgb(166, 158, 137),
            )
        Entity(
            parent=root,
            model="cube",
            position=(0, 0.47, -2.18),
            scale=(1.84, 0.13, 0.16),
            color=color.rgb(120, 119, 108),
        )
        Entity(
            parent=root,
            model="cube",
            position=(0, 0.47, 2.16),
            scale=(1.78, 0.13, 0.16),
            color=color.rgb(120, 119, 108),
        )
        self.police_lights = [
            entity for entity in root.children if getattr(entity, "unlit", False)
        ]
