import math
import random
from copy import deepcopy

from ursina import Entity, Mesh, Text, color

from .config import (
    PACKAGE_RETURN_POSITION,
    PACKAGE_RETURN_RADIUS,
    PLAZA_CENTER,
    POLICE_CAR_POSITION,
    TOWN_HEIGHT,
)
from .geometry import (
    enable_alpha_blending,
)


def create_package_return_ring_mesh(radius, thickness, segments=48):
    vertices = []
    triangles = []
    inner_radius = radius - thickness
    for index in range(segments):
        angle = math.tau * index / segments
        cosine, sine = math.cos(angle), math.sin(angle)
        vertices.extend(
            (
                (inner_radius * cosine, 0, inner_radius * sine),
                (radius * cosine, 0, radius * sine),
            )
        )

    for index in range(segments):
        current = index * 2
        following = ((index + 1) % segments) * 2
        triangles.extend(
            (
                (current, following, following + 1),
                (current, following + 1, current + 1),
            )
        )
    return Mesh(vertices=vertices, triangles=triangles, static=True)


class WorldCityBuilder:
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
        return_x, return_z = PACKAGE_RETURN_POSITION
        self.package_return_position = PACKAGE_RETURN_POSITION
        Entity(
            name="package_return_zone",
            model=create_package_return_ring_mesh(PACKAGE_RETURN_RADIUS, 0.16),
            position=(return_x, 0.035, return_z),
            color=color.rgb(255, 190, 55),
            unlit=True,
            double_sided=True,
        )
        return_station = Entity(
            name="package_return_station",
            position=(return_x, 0, return_z),
        )
        Entity(
            parent=return_station,
            model="cube",
            position=(0, 0.48, 0),
            scale=(0.9, 0.9, 0.72),
            color=color.rgb(69, 86, 73),
            texture=self.wood_texture,
        )
        Entity(
            parent=return_station,
            model="cube",
            position=(0, 0.96, 0),
            scale=(1.02, 0.12, 0.82),
            color=color.rgb(214, 172, 74),
            texture=self.metal_texture,
        )
        Entity(
            parent=return_station,
            model="cube",
            position=(0, 0.82, -0.37),
            scale=(0.55, 0.08, 0.035),
            color=color.rgb(26, 34, 30),
        )
        Text(
            parent=return_station,
            text="PACKAGE\nRETURN",
            position=(0, 1.48, 0),
            origin=(0, 0),
            scale=3.5,
            color=color.rgb(255, 215, 120),
            billboard=True,
        )
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
