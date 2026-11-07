import math

from ursina import Entity, color

from .geometry import enable_alpha_blending


class WorldUFOBuilder:
    def build_ufo(self):
        ship = Entity(position=(0, 10, 0), enabled=False)
        Entity(
            parent=ship,
            model=self.cylinder_model,
            position=(0, 0, 0),
            scale=(2.5, 0.24, 2.5),
            color=color.rgb(141, 158, 163),
        )
        Entity(
            parent=ship,
            model="sphere",
            position=(0, 0.28, 0),
            scale=(1.15, 0.85, 1.15),
            color=color.rgb(116, 196, 204),
            unlit=True,
        )
        Entity(
            parent=ship,
            model=self.cylinder_model,
            position=(0, -0.17, 0),
            scale=(2.0, 0.1, 2.0),
            color=color.rgb(81, 225, 220),
            unlit=True,
        )
        for index in range(8):
            angle = index * math.pi / 4
            lamp = Entity(
                parent=ship,
                model="sphere",
                position=(1.03 * math.cos(angle), -0.02, 1.03 * math.sin(angle)),
                scale=0.16,
                color=color.rgb(176, 255, 232),
                unlit=True,
            )
            lamp.set_light_off()

        beam = Entity(
            parent=ship,
            model=self.cone_model,
            position=(0, -4.1, 0),
            scale=(2.9, 8.2, 2.9),
            color=color.rgba(114, 241, 238, 66),
            double_sided=True,
            unlit=True,
            enabled=False,
        )
        enable_alpha_blending(beam)
        ring = Entity(
            parent=ship,
            model=self.cylinder_model,
            position=(0, -7.9, 0),
            scale=(1.8, 0.09, 1.8),
            color=color.rgba(168, 255, 228, 170),
            unlit=True,
            enabled=False,
        )
        enable_alpha_blending(ring)
        self.ufo = {"ship": ship, "beam": beam, "ring": ring}
