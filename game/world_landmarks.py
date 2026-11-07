from copy import deepcopy

from ursina import Entity, Text, color

from .config import (
    POLICE_CAR_POSITION,
)
from .geometry import (
    create_section_mesh,
    enable_alpha_blending,
)


class WorldLandmarkBuilder:
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
        for side_x in (-1, 1):
            for side_z in (-1, 1):
                Entity(
                    model="cube",
                    position=(x + side_x * 2.42, 7.0, z + side_z * 1.94),
                    scale=(0.28, 13.5, 0.28),
                    color=stone,
                    texture=self.stone_texture,
                )
        for level in range(1, 6):
            band_y = level * 2.5
            Entity(
                model="cube",
                position=(x, band_y, z - 2.16),
                scale=(5.4, 0.14, 0.16),
                color=stone,
                texture=self.stone_texture,
            )
        Entity(
            model="sphere",
            position=(x, 17.68, z - 1.56),
            scale=(1.34, 1.34, 0.16),
            color=color.rgb(69, 72, 66),
            unlit=True,
        )
        Entity(
            model="sphere",
            position=(x, 17.68, z - 1.66),
            scale=(1.13, 1.13, 0.1),
            color=color.rgb(219, 205, 166),
            unlit=True,
        )
        Entity(
            model="cube",
            position=(x, 17.91, z - 1.73),
            scale=(0.045, 0.48, 0.035),
            color=color.rgb(47, 51, 47),
        )
        Entity(
            model="cube",
            position=(x + 0.15, 17.69, z - 1.73),
            scale=(0.32, 0.045, 0.035),
            rotation_z=-32,
            color=color.rgb(47, 51, 47),
        )
        Text(
            text="XII",
            position=(x, 18.32, z - 1.75),
            origin=(0, 0),
            scale=1.2,
            color=color.rgb(56, 58, 51),
        )
        for side_x in (-1, 1):
            for side_z in (-1, 1):
                Entity(
                    model=self.cone_model,
                    position=(x + side_x * 0.95, 18.82, z + side_z * 0.95),
                    scale=(0.34, 0.82, 0.34),
                    color=stone,
                    texture=self.stone_texture,
                )
        Entity(
            model=self.cone_model,
            position=(x, 19.18, z),
            scale=(0.62, 1.25, 0.62),
            color=color.rgb(74, 81, 76),
            texture=self.metal_texture,
        )
        Entity(
            model="sphere",
            position=(x, 19.88, z),
            scale=0.2,
            color=color.rgb(255, 190, 92),
            unlit=True,
        )

    def build_police_car(self):
        x, z = POLICE_CAR_POSITION
        root = Entity(position=(x, 0, z), rotation_y=180)
        paint = color.rgb(22, 66, 126)
        white_paint = color.rgb(222, 226, 225)
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
            model="cube",
            position=(0, 1.475, 0.02),
            scale=(1.14, 0.055, 1.48),
            color=white_paint,
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
            color=white_paint,
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
                position=(side * 0.895, 0.69, 0.05),
                scale=(0.035, 0.16, 1.8),
                color=white_paint,
            )
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
                    text="POLICJA",
                    origin=(0, 0),
                    scale=1.1,
                    color=color.rgb(248, 248, 238),
                    position=(side * 0.90, 0.78, 0.04),
                    rotation=(0, 90, 0),
                ),
            )
            Text(
                parent=root,
                text="RADIOWÓZ",
                origin=(0, 0),
                scale=0.58,
                color=color.rgb(244, 246, 248),
                position=(side * 0.91, 0.58, 0.04),
                rotation=(0, 90, 0),
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
