import math
import os
import queue
import random
import sys
import tempfile
import time as clock
import wave
from array import array
from contextlib import suppress

from direct.filter.FilterManager import FilterManager
from panda3d.core import Fog
from panda3d.core import Texture as PandaTexture
from PIL import Image as PILImage
from PIL import ImageFilter as PILImageFilter
from ursina import (
    AmbientLight,
    Audio,
    Cone,
    Cylinder,
    DirectionalLight,
    Entity,
    Mesh,
    PointLight,
    Text,
    Texture,
    Ursina,
    Vec2,
    Vec3,
    camera,
    color,
    invoke,
    mouse,
    scene,
    time,
    window,
)

from .config import (
    AMBIENTCG_DIR,
    MISSION_SECONDS,
    PLAYER_START,
    PLAYER_START_ROTATION,
    TEXTURE_DIR,
    create_map,
)
from .entities import EntityBuilder
from .gameplay import GameplayMixin
from .shaders import (
    create_ambient_occlusion_shader,
    create_material_shader,
    create_ocean_shader,
    create_skin_shader,
)
from .world import WorldBuilder


class NeonFPS(WorldBuilder, EntityBuilder, GameplayMixin):
    def __init__(self):
        self.app = Ursina(
            fullscreen=False,
            borderless=False,
        )
        self.ao_enabled = False
        self.ao_available = None
        self.ao_filter_manager = None
        self.ao_quad = None
        self.cylinder_model = Cylinder(resolution=32)
        self.cone_model = Cone(resolution=24)
        self.ai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.ai_model = (
            os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        )
        self.ai_results = queue.Queue()
        self.ai_generation = 0
        window.size = (1280, 720)
        window.title = "The Estate: The Last Run — 1986"
        window.color = color.rgb(48, 58, 64)
        window.fps_counter.enabled = True
        window.exit_button.visible = False
        camera.fov = 79
        camera.clip_plane_far = 260
        mouse.locked = False
        mouse.visible = False
        window.set_mouse_mode(window.M_confined)
        self.app.win.requestProperties(window)
        self.mouse_sensitivity = 40
        self.touchpad_sensitivity = 180
        self.look_pitch = 0

        self.grid = create_map()
        self.map_width = len(self.grid[0])
        self.map_height = len(self.grid)
        self.world_entities = []
        self.snack_entities = []
        self.house_entities = []
        self.guard_entities = []
        self.pbr_entities = []
        (
            self.wall_texture,
            self.ground_texture,
            self.stone_texture,
            self.concrete_texture,
            self.sidewalk_texture,
            self.roof_texture,
            self.brick_texture,
            self.paving_texture,
            self.wood_texture,
            self.fabric_texture,
            self.metal_texture,
            self.skin_texture,
            self.wrapper_texture,
            self.sky_texture,
        ) = self.create_textures()
        self.material_maps = self.create_material_maps()
        self.material_shader = create_material_shader()
        self.skin_shader = create_skin_shader()
        self.ocean_shader = create_ocean_shader()
        self.fog_color = color.rgb(190, 216, 224)
        self.fog_density = 0.0075
        self.atmosphere_fog = Fog("coastal_atmosphere")
        self.atmosphere_fog.setColor(
            self.fog_color.r,
            self.fog_color.g,
            self.fog_color.b,
        )
        self.atmosphere_fog.setExpDensity(self.fog_density)
        scene.setFog(self.atmosphere_fog)
        self.displaced_wall_model = self.create_displaced_box(
            AMBIENTCG_DIR / "Plaster001_1K-JPG_Displacement.jpg",
            AMBIENTCG_DIR / "Plaster001_1K-JPG_NormalGL.jpg",
            resolution=40,
            amplitude=0.006,
        )
        self.brick_wall_model = self.create_displaced_box(
            AMBIENTCG_DIR / "Bricks055_1K-JPG_Displacement.jpg",
            AMBIENTCG_DIR / "Bricks055_1K-JPG_NormalGL.jpg",
            resolution=40,
            amplitude=0.012,
        )
        self.displaced_concrete_model = self.create_displaced_box(
            AMBIENTCG_DIR / "Concrete019_1K-JPG_Displacement.jpg",
            AMBIENTCG_DIR / "Concrete019_1K-JPG_NormalGL.jpg",
            resolution=12,
            amplitude=0.004,
        )
        self.displaced_asphalt_model = self.create_displaced_plane(
            AMBIENTCG_DIR / "Asphalt001_1K-JPG_Displacement.jpg",
            AMBIENTCG_DIR / "Asphalt001_1K-JPG_NormalGL.jpg",
        )
        self.paving_model = self.create_displaced_plane(
            AMBIENTCG_DIR / "PavingStones036_1K-JPG_Displacement.jpg",
            AMBIENTCG_DIR / "PavingStones036_1K-JPG_NormalGL.jpg",
            resolution=72,
            amplitude=0.012,
            tiling=3,
        )
        self.player = Entity(
            position=PLAYER_START,
            rotation_y=PLAYER_START_ROTATION,
        )
        camera.parent = self.player
        self.camera_pivot = Entity(parent=self.player, position=(0, 1.65, 0))
        camera.parent = self.camera_pivot
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)

        self.photo_mode = False
        self.ambient = AmbientLight(color=color.rgba(197, 202, 206, 255))
        self.sunlight = DirectionalLight(
            color=color.rgb(255, 241, 218),
            rotation=(48, -34, 0),
            shadows=self.photo_mode,
            shadow_map_resolution=Vec2(2048, 2048),
        )
        self.torch = PointLight(
            parent=camera,
            position=(0.15, -0.2, 0.45),
            color=color.rgb(207, 176, 128),
        )
        self.audio_enabled = True
        self.ambient_audio, self.ambient_path = self.create_ambient_audio()

        self.make_sky()
        self.build_world()
        self.build_forest()
        self.build_coastline()
        self.build_plaza()
        self.build_landmark()
        self.build_police_car()
        self.build_houses()
        self.build_city_fires()
        self.build_interactables()
        self.build_guard()
        self.shadow_bounds = Entity(
            model="cube",
            position=(self.map_width / 2, 10, self.map_height / 2),
            scale=(self.map_width + 2, 26, self.map_height + 2),
            visible=False,
        )
        invoke(
            self.sunlight.update_bounds,
            self.shadow_bounds,
            delay=0.35,
        )
        self.build_hud()
        if self.photo_mode:
            self.set_ambient_occlusion(True)
        self.reset()

    def create_ambient_audio(self):
        sample_rate = 22050
        duration = 10
        rng = random.Random(1986)
        samples = array("h")
        wind = 0.0
        traffic = 0.0
        total_samples = sample_rate * duration
        bird_calls = (1.2, 4.7, 8.1)
        for index in range(total_samples):
            t = index / sample_rate
            wind += (rng.uniform(-1, 1) - wind) * 0.018
            traffic_noise = rng.uniform(-1, 1)
            traffic += (traffic_noise - traffic) * 0.075
            traffic_cycle = t % 7.0
            vehicle = math.exp(-(((traffic_cycle - 3.7) / 1.2) ** 2))
            hum = math.sin(2 * math.pi * 48 * t) * 0.12
            rumble = math.sin(2 * math.pi * 72 * t) * 0.07
            sample = wind * 850 + traffic * vehicle * 750 + (hum + rumble) * 900
            for call_start in bird_calls:
                call_time = t - call_start
                if 0 <= call_time < 0.32:
                    envelope = math.sin(math.pi * call_time / 0.32) ** 2
                    frequency = 1650 + 550 * call_time / 0.32
                    sample += (
                        math.sin(2 * math.pi * frequency * call_time) * 170 * envelope
                    )
            samples.append(max(-32768, min(32767, int(sample))))
        fade_samples = sample_rate // 10
        for index in range(fade_samples):
            fade = index / fade_samples
            samples[index] = int(samples[index] * fade)
            samples[-index - 1] = int(samples[-index - 1] * fade)

        with tempfile.NamedTemporaryFile(
            prefix="prl_ambience_",
            suffix=".wav",
            delete=False,
        ) as sound_file:
            path = sound_file.name
        with wave.open(path, "wb") as sound_file:
            sound_file.setnchannels(1)
            sound_file.setsampwidth(2)
            sound_file.setframerate(sample_rate)
            sound_file.writeframes(samples.tobytes())
        ambient = Audio(self.app.loader.loadSfx(path), loop=True, volume=0.28)
        return ambient, path

    def make_sky(self):
        self.sky = Entity(
            model="sphere",
            scale=350,
            color=color.white,
            double_sided=True,
            unlit=True,
            texture=self.sky_texture,
        )

    @staticmethod
    def create_material_maps():
        materials = {
            "plaster": "Plaster001_1K-JPG",
            "concrete": "Concrete019_1K-JPG",
            "asphalt": "Asphalt001_1K-JPG",
            "brick": "Bricks055_1K-JPG",
            "roofing": "RoofingTiles001_1K-JPG",
            "paving": "PavingStones036_1K-JPG",
        }
        maps = {}
        for material, asset in materials.items():
            maps[material] = {}
            for map_type, key in (
                ("NormalGL", "normal"),
                ("Roughness", "roughness"),
                ("Displacement", "displacement"),
            ):
                path = AMBIENTCG_DIR / f"{asset}_{map_type}.jpg"
                if not path.is_file():
                    raise FileNotFoundError(
                        f"Missing material map: {path}. "
                        "Restore the files in assets/textures/ambientcg."
                    )
                if key != "displacement":
                    maps[material][key] = Texture(str(path))
            occlusion_path = AMBIENTCG_DIR / f"{asset}_AmbientOcclusion.jpg"
            if occlusion_path.is_file():
                maps[material]["occlusion"] = Texture(str(occlusion_path))
        return maps

    @staticmethod
    def create_displaced_box(
        height_map_path,
        normal_map_path,
        resolution=32,
        amplitude=0.008,
    ):
        with PILImage.open(height_map_path) as source:
            height_map = source.convert("L").filter(PILImageFilter.GaussianBlur(1.5))
        with PILImage.open(normal_map_path) as source:
            normal_map = source.convert("RGB").filter(PILImageFilter.GaussianBlur(8))
        width, height = height_map.size
        normal_width, normal_height = normal_map.size
        faces = (
            ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
            ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
            ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
            ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
            ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
            ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
        )
        pixels = height_map.load()
        normal_pixels = normal_map.load()
        vertices = []
        normals = []
        uvs = []
        triangles = []
        tiling = 3
        uv_step = 1 / resolution

        def sample_height(u, v):
            u = (u * tiling) % 1.0
            v = (v * tiling) % 1.0
            px = min(width - 1, int(u * width))
            py = min(height - 1, int(v * height))
            return (pixels[px, py] / 255.0 - 0.5) * amplitude

        def sample_normal(u, v):
            u = (u * tiling) % 1.0
            v = (v * tiling) % 1.0
            px = min(normal_width - 1, int(u * normal_width))
            py = min(normal_height - 1, int(v * normal_height))
            return tuple(channel / 127.5 - 1.0 for channel in normal_pixels[px, py])

        for normal, axis_u, axis_v in faces:
            start = len(vertices)
            for row in range(resolution + 1):
                v = row / resolution
                for column in range(resolution + 1):
                    u = column / resolution
                    displacement = sample_height(u, v)
                    du = (
                        sample_height(u + uv_step, v) - sample_height(u - uv_step, v)
                    ) / (2 * uv_step)
                    dv = (
                        sample_height(u, v + uv_step) - sample_height(u, v - uv_step)
                    ) / (2 * uv_step)
                    map_normal = sample_normal(u, v)
                    point = tuple(
                        normal[index] * (0.5 + displacement)
                        + axis_u[index] * (u - 0.5)
                        + axis_v[index] * (v - 0.5)
                        for index in range(3)
                    )
                    perturbed_normal = tuple(
                        axis_u[index] * map_normal[0] * 0.4
                        + axis_v[index] * map_normal[1] * 0.4
                        + normal[index] * map_normal[2]
                        - axis_u[index] * du
                        - axis_v[index] * dv
                        for index in range(3)
                    )
                    normal_length = math.sqrt(
                        sum(component * component for component in perturbed_normal)
                    )
                    vertices.append(point)
                    normals.append(
                        tuple(
                            component / normal_length for component in perturbed_normal
                        )
                    )
                    uvs.append((u, v))

            for row in range(resolution):
                for column in range(resolution):
                    a = start + row * (resolution + 1) + column
                    b = a + 1
                    d = a + resolution + 1
                    c = d + 1
                    triangles.extend(((a, b, c), (a, c, d)))

        return Mesh(
            vertices=vertices,
            triangles=triangles,
            uvs=uvs,
            normals=normals,
            static=True,
        )

    @staticmethod
    def create_displaced_plane(
        height_map_path,
        normal_map_path,
        resolution=48,
        amplitude=0.004,
        tiling=6,
    ):
        with PILImage.open(height_map_path) as source:
            height_map = source.convert("L")
        with PILImage.open(normal_map_path) as source:
            normal_map = source.convert("RGB")
        width, height = height_map.size
        normal_width, normal_height = normal_map.size
        height_pixels = height_map.load()
        normal_pixels = normal_map.load()
        vertices = []
        normals = []
        uvs = []
        triangles = []

        def sample(u, v):
            tiled_u = (u * tiling) % 1.0
            tiled_v = (v * tiling) % 1.0
            x = min(width - 1, int(tiled_u * width))
            y = min(height - 1, int(tiled_v * height))
            nx = min(normal_width - 1, int(tiled_u * normal_width))
            ny = min(normal_height - 1, int(tiled_v * normal_height))
            height_value = (height_pixels[x, y] / 255.0 - 0.5) * amplitude
            map_normal = tuple(
                channel / 127.5 - 1.0 for channel in normal_pixels[nx, ny]
            )
            return height_value, map_normal

        for row in range(resolution + 1):
            v = row / resolution
            for column in range(resolution + 1):
                u = column / resolution
                displacement, map_normal = sample(u, v)
                vertices.append((u - 0.5, displacement, 0.5 - v))
                normals.append(
                    (
                        map_normal[0],
                        map_normal[2],
                        -map_normal[1],
                    )
                )
                uvs.append((u, v))

        for row in range(resolution):
            for column in range(resolution):
                a = row * (resolution + 1) + column
                b = a + 1
                d = a + resolution + 1
                c = d + 1
                triangles.extend(((a, b, c), (a, c, d)))

        return Mesh(
            vertices=vertices,
            triangles=triangles,
            uvs=uvs,
            normals=normals,
            static=True,
        )

    def apply_surface_material(self, entity, material):
        entity.shader = self.material_shader
        maps = self.material_maps[material]
        entity.set_shader_input("fog_color", self.fog_color)
        entity.set_shader_input("fog_density", self.fog_density)
        entity.set_shader_input("shadow_strength", float(self.photo_mode))
        entity.set_shader_input("environment_map", self.sky_texture)
        entity.set_shader_input(
            "reflection_strength",
            {
                "asphalt": 0.22,
                "paving": 0.16,
                "concrete": 0.09,
                "roofing": 0.10,
                "plaster": 0.045,
                "brick": 0.04,
            }[material],
        )
        entity.set_shader_input(
            "roughness_map",
            maps["roughness"],
        )
        entity.set_shader_input(
            "occlusion_map",
            maps.get("occlusion", maps["roughness"]),
        )
        entity.set_shader_input(
            "occlusion_strength",
            0.72 if "occlusion" in maps else 0.0,
        )
        self.pbr_entities.append(entity)

    def apply_skin_material(self, entity):
        entity.shader = self.skin_shader
        entity.set_shader_input(
            "subsurface_color",
            Vec3(1.0, 0.48, 0.34),
        )
        entity.set_shader_input("subsurface_strength", 0.42)

    def set_ambient_occlusion(self, enabled):
        if self.ao_available is None:
            self.ao_filter_manager = FilterManager(self.app.win, self.app.cam)
            self.ao_color_texture = PandaTexture("ao-scene-color")
            self.ao_depth_texture = PandaTexture("ao-scene-depth")
            self.ao_quad = self.ao_filter_manager.renderSceneInto(
                colortex=self.ao_color_texture,
                depthtex=self.ao_depth_texture,
            )
            self.ao_available = self.ao_quad is not None
            if self.ao_available:
                self.ao_quad.setShader(create_ambient_occlusion_shader())
                self.ao_quad.setShaderInput("scene_color", self.ao_color_texture)
                self.ao_quad.setShaderInput("scene_depth", self.ao_depth_texture)
                self.ao_quad.setShaderInput(
                    "inverse_resolution",
                    Vec2(
                        1.0 / max(self.ao_color_texture.getXSize(), 1),
                        1.0 / max(self.ao_color_texture.getYSize(), 1),
                    ),
                )

        if not self.ao_available:
            self.ao_enabled = False
            print(
                "Screen-space ambient occlusion is unavailable; "
                "material AO maps will still be used.",
                file=sys.stderr,
            )
            self.set_message(
                "Screen-space AO unavailable — material AO maps remain active.",
                5,
            )
            return False

        self.ao_enabled = bool(enabled)
        self.ao_quad.setShaderInput("ao_enabled", float(self.ao_enabled))
        return True

    def set_photo_mode(self, enabled):
        self.photo_mode = enabled
        self.sunlight.shadows = enabled
        self.set_ambient_occlusion(enabled)
        if enabled:
            self.sunlight.update_bounds(self.shadow_bounds)
        self.ambient.color = (
            color.rgba(180, 187, 193, 255)
            if enabled
            else color.rgba(197, 202, 206, 255)
        )
        for entity in self.pbr_entities:
            entity.set_shader_input("shadow_strength", float(enabled))
        self.set_message(
            "Photo mode on — shadows and ambient occlusion enabled."
            if enabled
            else "Performance mode on — shadows and AO disabled.",
            2,
        )

    def build_hud(self):
        self.title_text = Text(
            text="THE ESTATE 1986  /  THE LAST RUN",
            position=(-0.86, 0.46),
            scale=0.9,
            color=color.rgb(222, 190, 133),
        )
        self.stats_text = Text(
            position=(-0.86, 0.39),
            scale=0.78,
            color=color.rgb(225, 217, 191),
        )
        self.controls_text = Text(
            text=(
                "WASD move | Mouse look | SHIFT sprint | E interact | "
                "Q share a treat | F flashlight\n"
                "TAB map | U audio | P graphics | R release cursor | "
                "ENTER restart | ESC quit"
            ),
            position=(-0.86, -0.47),
            scale=0.62,
            color=color.rgb(199, 193, 172),
        )
        self.message_text = Text(
            position=(0, 0.31),
            origin=(0, 0),
            scale=1.1,
            color=color.rgb(235, 205, 146),
        )
        self.capture_text = Text(
            text="CLICK WINDOW TO CAPTURE MOUSE | R: RELEASE MOUSE",
            position=(0, -0.39),
            origin=(0, 0),
            scale=0.85,
            color=color.rgb(235, 205, 146),
        )
        self.crosshair = Text(
            text="+",
            origin=(0, 0),
            scale=0.055,
            color=color.rgb(225, 212, 176),
        )
        self.map_text = Text(
            position=(0.6, 0.39),
            scale=0.52,
            color=color.rgb(218, 205, 165),
            enabled=False,
        )
        self.end_text = Text(
            origin=(0, 0),
            scale=2,
            color=color.rgb(225, 188, 118),
            enabled=False,
        )

    @staticmethod
    def create_textures():
        files = (
            AMBIENTCG_DIR / "Plaster001_1K-JPG_Color.jpg",
            AMBIENTCG_DIR / "Asphalt001_1K-JPG_Color.jpg",
            TEXTURE_DIR / "cobblestone.png",
            AMBIENTCG_DIR / "Concrete019_1K-JPG_Color.jpg",
            AMBIENTCG_DIR / "Concrete019_1K-JPG_Color.jpg",
            AMBIENTCG_DIR / "RoofingTiles001_1K-JPG_Color.jpg",
            AMBIENTCG_DIR / "Bricks055_1K-JPG_Color.jpg",
            AMBIENTCG_DIR / "PavingStones036_1K-JPG_Color.jpg",
            TEXTURE_DIR / "weathered_wood.png",
            TEXTURE_DIR / "worn_fabric.png",
            TEXTURE_DIR / "oxidized_metal.png",
            TEXTURE_DIR / "weathered_skin.png",
            TEXTURE_DIR / "stained_paper.png",
            TEXTURE_DIR / "overcast_sky.png",
        )
        missing = [path for path in files if not path.is_file()]
        if missing:
            names = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(
                f"Missing game textures: {names}. "
                "Restore the ambientCG textures in assets/textures/ambientcg "
                "and run the generator for the remaining materials."
            )
        return tuple(Texture(str(path)) for path in files)

    def update(self):
        now = clock.monotonic()
        dt = min(time.dt, 0.05)
        self.ocean.set_shader_input("water_time", now)
        if not self.game_over:
            self.move_player()
            self.update_snacks(dt, now)
            self.update_guard(dt, now)
            if self.torch_on:
                self.torch_charge = max(0.0, self.torch_charge - 2.2 * dt)
                if self.torch_charge <= 0:
                    self.torch_on = False
                    self.torch.enabled = False
            elif any(
                house["visited"]
                and math.hypot(house["x"] - self.player.x, house["z"] - self.player.z)
                < 1.4
                for house in self.house_state
            ):
                self.torch_charge = min(100.0, self.torch_charge + 7 * dt)

            remaining = (
                MISSION_SECONDS - (now - self.mission_started) + self.mission_time_bonus
            )
            if remaining <= 0:
                self.end_game(False)

        for index, light in enumerate(self.police_lights):
            light.enabled = int(now * 3) % 2 == index
        for flame in self.fire_flames:
            flicker = math.sin(now * 12 + flame["phase"])
            pulse = math.sin(now * 8.5 + flame["phase"] * 1.3)
            flame["entity"].scale = (
                flame["scale"][0] * (1.0 + flicker * 0.1),
                flame["scale"][1] * (1.0 + pulse * 0.16),
                flame["scale"][2] * (1.0 - flicker * 0.08),
            )
            flame["entity"].rotation_y += (18 + flicker * 12) * dt
        fire_flicker = math.sin(now * 9.0) + math.sin(now * 15.7 + 0.8) * 0.42
        self.fire_light.color = color.rgb(
            int(244 + fire_flicker * 8),
            int(105 + fire_flicker * 17),
            int(36 + fire_flicker * 8),
        )
        for light in self.city_fire_lights:
            flicker = math.sin(now * 10.0 + light["phase"])
            light["entity"].color = color.rgb(
                255,
                int(84 + 22 * flicker),
                int(24 + 12 * flicker),
            )
        for core in self.city_fire_cores:
            flicker = math.sin(now * 15.0 + core["phase"])
            pulse = 1.0 + 0.1 * flicker
            core["entity"].scale = (
                core["scale"][0] * pulse,
                core["scale"][1] * (1.0 + 0.08 * math.sin(now * 11.0 + core["phase"])),
                1,
            )
            core["entity"].rotation_z = 2.5 * flicker
            core["entity"].color = color.rgba(
                255,
                int(226 + 28 * max(0.0, flicker)),
                int(176 + 52 * max(0.0, flicker)),
                218,
            )
        for particle in self.city_fire_particles:
            particle["age"] += dt
            if particle["age"] >= particle["lifetime"]:
                self.reset_city_fire_particle(particle)
            progress = particle["age"] / particle["lifetime"]
            entity = particle["entity"]
            entity.position = (
                particle["origin_x"] + particle["drift_x"] * particle["age"],
                particle["origin_y"] + particle["speed"] * particle["age"],
                particle["origin_z"] + particle["drift_z"] * particle["age"],
            )
            if particle["kind"] == "flame":
                flicker = 0.88 + 0.12 * math.sin(
                    now * 19.0 + particle["origin_x"] * 7.0
                )
                growth = 0.72 + 0.45 * progress
                entity.scale = (
                    particle["size"] * 0.72 * growth,
                    particle["size"] * 1.55 * growth,
                    1,
                )
                entity.color = color.rgba(
                    255,
                    int(235 - 75 * progress),
                    int(190 - 145 * progress),
                    int(240 * (1.0 - progress) ** 0.72 * flicker),
                )
            else:
                entity.scale = (
                    particle["size"] * (0.65 + progress * 0.75),
                    particle["size"] * (0.8 + progress * 1.1),
                    1,
                )
                alpha = int(116 * (1.0 - progress) ** 1.35)
                entity.color = color.rgba(
                    int(124 + progress * 30),
                    int(120 + progress * 29),
                    int(113 + progress * 29),
                    alpha,
                )
        for particle in self.fire_particles:
            particle["age"] += dt
            if particle["age"] >= particle["lifetime"]:
                self.reset_fire_particle(
                    particle,
                    21.5,
                    35.5,
                )
            progress = particle["age"] / particle["lifetime"]
            pulse = 0.82 + 0.18 * math.sin(now * 18.0 + particle["phase"])
            particle_entity = particle["entity"]
            particle_entity.position = (
                particle["origin_x"] + particle["drift_x"] * particle["age"],
                0.38 + particle["age"] * particle["speed"],
                particle["origin_z"] + particle["drift_z"] * particle["age"],
            )
            particle_entity.scale = particle["size"] * (1.0 + progress * 0.35)
            particle_entity.color = color.rgba(
                255,
                int(122 + 74 * (1.0 - progress)),
                int(35 + 45 * (1.0 - progress)),
                int(220 * (1.0 - progress) ** 1.4 * pulse),
            )
        for bank in self.fog_banks:
            bank["entity"].x = bank["x"] + math.sin(now * 0.18 + bank["phase"]) * 0.48
            bank["entity"].y = 1.2 + math.sin(now * 0.28 + bank["phase"]) * 0.12
            bank["entity"].rotation_y = math.sin(now * 0.12 + bank["phase"]) * 7
        for snack in self.snacks:
            if not snack["collected"]:
                snack["entities"][0].y = (
                    0.42 + math.sin(now * 3 + snack["phase"]) * 0.08
                )
                snack["entities"][0].rotation_y += 35 * dt

        if self.message and now > self.message_until:
            self.message_text.text = ""
        self.capture_text.enabled = not mouse.locked and not self.game_over
        self.refresh_hud()

    def run(self):
        try:
            self.app.run()
        finally:
            self.close()

    def close(self):
        if self.ao_filter_manager is not None:
            self.ao_filter_manager.cleanup()
        if self.ambient_audio.clip:
            self.ambient_audio.stop(destroy=False)
        with suppress(FileNotFoundError):
            os.remove(self.ambient_path)


game = None


def update():
    if game is not None:
        game.update()


def input(key):
    if game is not None:
        game.input(key)


def run_game():
    global game
    game = NeonFPS()
    game.run()
