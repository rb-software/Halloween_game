import math
import random

from ursina import Entity, PointLight, color

from .config import (
    HOUSE_POSITIONS,
    HOUSE_ROTATIONS,
)
from .geometry import (
    create_fire_texture,
    create_smoke_texture,
    create_spark_texture,
    enable_alpha_blending,
)


class WorldFireBuilder:
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
