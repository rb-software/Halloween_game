import math

from ursina import Entity, Mesh, Text, color

from .config import TOWN_HEIGHT
from .geometry import (
    create_mist_texture,
    create_ocean_mesh,
    create_ship_hull_mesh,
    enable_alpha_blending,
)


class WorldNatureBuilder:
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
            texture=self.concrete_texture,
            double_sided=True,
        )
        trail.texture_scale = (1, 7)
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
        self.build_ocean_ships()

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

    def build_ocean_ships(self):
        ship_colors = (
            color.rgb(104, 55, 42),
            color.rgb(73, 83, 87),
            color.rgb(94, 72, 47),
        )
        sail_colors = (
            color.rgb(220, 207, 165),
            color.rgb(183, 199, 193),
            color.rgb(204, 187, 145),
        )
        self.ocean_ships = []
        for index, (x, z, size) in enumerate(
            ((5.5, -12.0, 1.0), (25.5, -27.0, 0.82), (13.5, -49.0, 1.18))
        ):
            heading = (-12, 14, -7)[index]
            ship = Entity(
                position=(x, 0.12, z),
                rotation_y=heading,
                scale=size,
            )
            Entity(
                parent=ship,
                model=create_ship_hull_mesh(),
                position=(0, 0, 0),
                color=ship_colors[index],
                double_sided=True,
            )
            Entity(
                parent=ship,
                model="cube",
                position=(0, 0.43, 0),
                scale=(3.55, 0.1, 0.94),
                color=color.rgb(157, 127, 83),
            )
            Entity(
                parent=ship,
                model=self.cylinder_model,
                position=(0, 1.85, 0),
                scale=(0.09, 3.7, 0.09),
                color=color.rgb(100, 79, 56),
                texture=self.wood_texture,
            )
            Entity(
                parent=ship,
                model=self.cylinder_model,
                position=(0, 2.15, 0),
                rotation_z=90,
                scale=(0.055, 2.55, 0.055),
                color=color.rgb(100, 79, 56),
                texture=self.wood_texture,
            )
            for vertices, sail_position in (
                (
                    ((0, 0, 0), (0, 2.05, 0), (-1.35, 0.12, 0)),
                    (0, 0.42, -0.07),
                ),
                (
                    ((0, 0, 0), (0, 1.65, 0), (1.05, 0.12, 0)),
                    (0, 0.55, -0.08),
                ),
            ):
                Entity(
                    parent=ship,
                    model=Mesh(
                        vertices=vertices,
                        triangles=((0, 1, 2),),
                        uvs=((0, 0), (0.5, 1), (1, 0)),
                        static=True,
                    ),
                    position=sail_position,
                    color=sail_colors[index],
                    double_sided=True,
                )
            Entity(
                parent=ship,
                model="cube",
                position=(1.45, 0.75, 0),
                scale=(0.68, 0.55, 0.72),
                color=color.rgb(131, 118, 91),
            )
            Entity(
                parent=ship,
                model="cube",
                position=(1.45, 1.04, 0),
                scale=(0.75, 0.08, 0.78),
                color=color.rgb(87, 67, 48),
            )
            self.ocean_ships.append(
                {
                    "entity": ship,
                    "x": x,
                    "y": 0.12,
                    "z": z,
                    "heading": heading,
                    "phase": index * 2.2,
                    "speed": 0.42 + index * 0.08,
                    "direction": 1 if index % 2 == 0 else -1,
                    "roll": (-1, 1, -1)[index],
                }
            )

    def update_ocean_ships(self, now):
        for ship in self.ocean_ships:
            phase = now * ship["speed"] + ship["phase"]
            ship["entity"].x = ship["x"] + math.sin(phase * 0.32) * 3.2
            ship["entity"].y = ship["y"] + math.sin(phase) * 0.18
            ship["entity"].z = ship["z"] + math.cos(phase * 0.32) * 2.2
            ship["entity"].rotation_z = math.sin(phase * 0.8) * 2.0
            ship["entity"].rotation_y = ship["heading"] + (
                math.sin(phase) * ship["roll"] * 2.0
            )
