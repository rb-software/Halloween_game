import random

from ursina import Entity, Text, color

from .config import (
    FOREST_TREE_CELLS,
    TOWN_HEIGHT,
)
from .geometry import (
    create_mist_texture,
    create_ocean_mesh,
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
