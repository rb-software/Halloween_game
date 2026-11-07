import math
import random

from panda3d.core import TransparencyAttrib
from PIL import Image as PILImage
from PIL import ImageDraw as PILImageDraw
from PIL import ImageEnhance as PILImageEnhance
from PIL import ImageFilter as PILImageFilter
from PIL import ImageOps as PILImageOps
from ursina import Mesh, Texture


def create_ocean_mesh(width, depth, segments=48):
    vertices = []
    normals = []
    uvs = []
    triangles = []
    for row in range(segments + 1):
        v = row / segments
        for column in range(segments + 1):
            u = column / segments
            vertices.append(((u - 0.5) * width, 0, (v - 0.5) * depth))
            normals.append((0, 1, 0))
            uvs.append((u, v))

    for row in range(segments):
        for column in range(segments):
            lower_left = row * (segments + 1) + column
            lower_right = lower_left + 1
            upper_left = lower_left + segments + 1
            upper_right = upper_left + 1
            triangles.extend(
                (
                    (lower_left, upper_left, upper_right),
                    (lower_left, upper_right, lower_right),
                )
            )
    return Mesh(
        vertices=vertices,
        triangles=triangles,
        uvs=uvs,
        normals=normals,
        static=True,
    )


def create_profile_mesh(profile, segments=20):
    vertices = []
    uvs = []
    triangles = []
    for ring_index, (y, radius_x, radius_z, center_z) in enumerate(profile):
        v = ring_index / max(1, len(profile) - 1)
        for segment in range(segments):
            angle = 2 * math.pi * segment / segments
            vertices.append(
                (
                    radius_x * math.cos(angle),
                    y,
                    center_z + radius_z * math.sin(angle),
                )
            )
            uvs.append((segment / segments, v))

    for ring_index in range(len(profile) - 1):
        lower = ring_index * segments
        upper = lower + segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            triangles.extend(
                (
                    (lower + segment, upper + segment, upper + next_segment),
                    (lower + segment, upper + next_segment, lower + next_segment),
                )
            )

    bottom_center = len(vertices)
    vertices.append((0, profile[0][0], profile[0][3]))
    uvs.append((0.5, 0))
    top_center = len(vertices)
    vertices.append((0, profile[-1][0], profile[-1][3]))
    uvs.append((0.5, 1))
    top_ring = (len(profile) - 1) * segments
    for segment in range(segments):
        next_segment = (segment + 1) % segments
        triangles.append((bottom_center, segment, next_segment))
        triangles.append((top_ring + segment, top_center, top_ring + next_segment))

    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, static=True)


def create_section_mesh(sections):
    vertices = []
    uvs = []
    triangles = []
    for section_index, (z, half_width, bottom, top) in enumerate(sections):
        vertices.extend(
            (
                (-half_width, bottom, z),
                (half_width, bottom, z),
                (half_width, top, z),
                (-half_width, top, z),
            )
        )
        uvs.extend(
            (
                (0, section_index / (len(sections) - 1)),
                (1, section_index / (len(sections) - 1)),
                (1, section_index / (len(sections) - 1)),
                (0, section_index / (len(sections) - 1)),
            )
        )

    for section_index in range(len(sections) - 1):
        start = section_index * 4
        next_start = start + 4
        for corner in range(4):
            next_corner = (corner + 1) % 4
            triangles.extend(
                (
                    (start + corner, next_start + corner, next_start + next_corner),
                    (start + corner, next_start + next_corner, start + next_corner),
                )
            )
    triangles.extend(((0, 1, 2), (0, 2, 3)))
    end = (len(sections) - 1) * 4
    triangles.extend(((end, end + 2, end + 1), (end, end + 3, end + 2)))
    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, static=True)


def create_gable_mesh(width, depth, height):
    half_width = width / 2
    half_depth = depth / 2
    vertices = (
        (-half_width, 0, -half_depth),
        (half_width, 0, -half_depth),
        (0, height, -half_depth),
        (-half_width, 0, half_depth),
        (half_width, 0, half_depth),
        (0, height, half_depth),
    )
    triangles = (
        (0, 1, 2),
        (3, 5, 4),
        (0, 3, 4),
        (0, 4, 1),
        (1, 4, 5),
        (1, 5, 2),
        (2, 5, 3),
        (2, 3, 0),
    )
    uvs = (
        (0, 0),
        (1, 0),
        (0.5, 1),
        (0, 0),
        (1, 0),
        (0.5, 1),
    )
    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, static=True)


def add_andromeda_to_sky(sky_image, galaxy_image):
    source = sky_image.convert("RGB").resize(
        (sky_image.width * 2, sky_image.height * 2),
        resample=PILImage.Resampling.LANCZOS,
    )
    width, height = source.size
    source_luminance = PILImageOps.autocontrast(
        PILImageOps.grayscale(source),
        cutoff=2,
    )
    sky = PILImage.new("RGB", (width, height))
    sky_pixels = sky.load()
    luminance_pixels = source_luminance.load()
    for y in range(height):
        vertical = y / max(1, height - 1)
        blend = min(1.0, vertical * 1.5)
        top_color = (2, 4, 14)
        horizon_color = (8, 9, 24)
        for x in range(width):
            base = tuple(
                round(top * (1 - blend) + horizon * blend)
                for top, horizon in zip(top_color, horizon_color)
            )
            cloud = max(0.0, (luminance_pixels[x, y] - 125) / 130) * 0.045
            sky_pixels[x, y] = tuple(
                round(channel * (1 - cloud) + tint * cloud)
                for channel, tint in zip(base, (40, 55, 90))
            )

    sky = sky.convert("RGBA")

    rng = random.Random(31031)
    nebula = PILImage.new("RGBA", (width, height))
    nebula_draw = PILImageDraw.Draw(nebula)
    nebula_colors = (
        (34, 52, 126, 28),
        (77, 36, 114, 25),
        (33, 80, 103, 22),
        (125, 53, 91, 18),
    )
    for index in range(24):
        center_x = rng.randrange(width)
        center_y = rng.randrange(height // 8, height)
        radius_x = rng.randrange(width // 12, width // 3)
        radius_y = rng.randrange(max(12, height // 22), height // 7)
        nebula_draw.ellipse(
            (
                center_x - radius_x,
                center_y - radius_y,
                center_x + radius_x,
                center_y + radius_y,
            ),
            fill=nebula_colors[index % len(nebula_colors)],
        )
    nebula = nebula.filter(PILImageFilter.GaussianBlur(max(10, width // 48)))
    sky.alpha_composite(nebula)

    star_layer = PILImage.new("RGBA", (width, height))
    star_draw = PILImageDraw.Draw(star_layer)
    for _ in range(width * height // 210):
        star_x = rng.randrange(width)
        star_y = rng.randrange(height)
        brightness = rng.randint(105, 235)
        star_draw.point(
            (star_x, star_y),
            fill=(brightness, brightness, min(255, brightness + 18), 255),
        )
    for _ in range(max(12, width // 35)):
        star_x = rng.randrange(width)
        star_y = rng.randrange(height)
        brightness = rng.randint(190, 255)
        radius = rng.choice((1, 1, 2))
        star_draw.ellipse(
            (star_x - radius, star_y - radius, star_x + radius, star_y + radius),
            fill=(brightness, brightness, 255, 255),
        )
    sky.alpha_composite(star_layer)

    target_width = int(width * 1.22)
    target_height = int(height * 0.94)
    galaxy = galaxy_image.convert("RGB")
    galaxy = PILImageOps.contain(
        galaxy,
        (target_width, target_height),
        method=PILImage.Resampling.LANCZOS,
    )
    if galaxy.width > width:
        crop_left = (galaxy.width - width) // 2
        galaxy = galaxy.crop((crop_left, 0, crop_left + width, galaxy.height))
    galaxy = PILImageEnhance.Contrast(galaxy).enhance(1.1)
    galaxy = PILImageEnhance.Color(galaxy).enhance(1.15)
    galaxy_luminance = PILImageOps.grayscale(galaxy)
    galaxy = galaxy.convert("RGBA")
    galaxy.putalpha(
        galaxy_luminance.point(lambda value: min(230, max(0, (value - 10) * 1.5)))
    )
    galaxy = galaxy.filter(PILImageFilter.GaussianBlur(0.4))

    galaxy_x = (width - galaxy.width) // 2
    galaxy_y = max(
        0,
        (height - galaxy.height) // 2 - int(height * 0.08),
    )
    glow = PILImage.new("RGBA", (width, height))
    glow_draw = PILImageDraw.Draw(glow)
    glow_draw.ellipse(
        (
            galaxy_x - width // 40,
            galaxy_y - height // 18,
            galaxy_x + galaxy.width + width // 40,
            galaxy_y + galaxy.height + height // 18,
        ),
        fill=(101, 125, 221, 64),
    )
    glow = glow.filter(PILImageFilter.GaussianBlur(max(18, width // 24)))
    sky.alpha_composite(glow)
    sky.alpha_composite(galaxy, dest=(galaxy_x, galaxy_y))
    return sky


def create_gable_roof_mesh(width, depth, height, thickness=0.14):
    half_width = width / 2
    half_depth = depth / 2
    vertices = []
    uvs = []
    triangles = []

    def add_quad(a, b, c, d, reverse=False):
        first = (a, b, c)
        second = (a, c, d)
        if reverse:
            first = (first[0], first[2], first[1])
            second = (second[0], second[2], second[1])
        triangles.extend((first, second))

    for eave_z, ridge_z in ((-half_depth, 0), (half_depth, 0)):
        offset = len(vertices)
        reverse = eave_z < 0
        vertices.extend(
            (
                (-half_width, 0, eave_z),
                (half_width, 0, eave_z),
                (half_width, height, ridge_z),
                (-half_width, height, ridge_z),
                (-half_width, -thickness, eave_z),
                (half_width, -thickness, eave_z),
                (half_width, height - thickness, ridge_z),
                (-half_width, height - thickness, ridge_z),
            )
        )
        uvs.extend(
            (
                (0, 0),
                (1, 0),
                (1, 1),
                (0, 1),
                (0, 0),
                (1, 0),
                (1, 1),
                (0, 1),
            )
        )
        add_quad(offset, offset + 1, offset + 2, offset + 3, reverse)
        add_quad(offset + 4, offset + 5, offset + 6, offset + 7, not reverse)
        add_quad(offset, offset + 4, offset + 5, offset + 1, reverse)
        add_quad(offset, offset + 3, offset + 7, offset + 4, reverse)
        add_quad(offset + 1, offset + 5, offset + 6, offset + 2, reverse)

    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, static=True)


def create_mist_texture():
    rng = random.Random(1986)
    blobs = [
        (
            rng.uniform(12, 116),
            rng.uniform(12, 84),
            rng.uniform(14, 34),
            rng.uniform(8, 22),
            rng.uniform(22, 54),
        )
        for _ in range(8)
    ]
    image = PILImage.new("RGBA", (128, 96))
    pixels = []
    for y in range(96):
        for x in range(128):
            density = sum(
                strength
                * math.exp(
                    -(
                        ((x - center_x) / radius_x) ** 2
                        + ((y - center_y) / radius_y) ** 2
                    )
                )
                for center_x, center_y, radius_x, radius_y, strength in blobs
            )
            alpha = min(76, int(density))
            pixels.append((200, 216, 219, alpha))
    image.putdata(pixels)
    image = image.filter(PILImageFilter.GaussianBlur(3))
    return Texture(image)


def create_spark_texture():
    size = 32
    pixels = []
    center = (size - 1) * 0.5
    for y in range(size):
        for x in range(size):
            distance = math.sqrt((x - center) ** 2 + (y - center) ** 2) / center
            alpha = int(255 * max(0.0, 1.0 - distance) ** 2.4)
            pixels.append((255, 255, 255, alpha))
    image = PILImage.new("RGBA", (size, size))
    image.putdata(pixels)
    return Texture(image)


def create_fire_texture():
    width, height = 96, 144
    rng = random.Random(1988)
    noise = [rng.random() for _ in range(width * height)]
    row_flicker = [rng.uniform(-0.12, 0.12) for _ in range(height)]
    pixels = []
    for y in range(height):
        progress = y / (height - 1)
        taper = (1.0 - progress) ** 0.72
        for x in range(width):
            normalized_x = abs((x / (width - 1)) * 2.0 - 1.0)
            edge_noise = (
                row_flicker[y]
                + 0.06 * math.sin(y * 0.19 + x * 0.13)
                + 0.04 * math.sin(y * 0.071 + 1.7)
            )
            edge = taper * (0.78 + edge_noise)
            distance = normalized_x / max(edge, 0.025)
            flicker = noise[y * width + x]
            alpha = max(0.0, min(1.0, (1.0 - distance) * 8.0))
            alpha *= max(0.0, min(1.0, (1.0 - progress) * 10.0 + 0.08))
            alpha *= 0.78 + flicker * 0.22

            core = max(0.0, 1.0 - normalized_x * 3.8) * max(0.0, 1.0 - progress * 0.72)
            red = int(255 - progress * 68)
            green = int(22 + 224 * (1.0 - progress) ** 1.18 + core * 20)
            blue = int(8 + 137 * (1.0 - progress) ** 2 + core * 25)
            pixels.append((red, green, blue, int(255 * alpha)))

    image = PILImage.new("RGBA", (width, height))
    image.putdata(pixels)
    image = image.filter(PILImageFilter.GaussianBlur(1.2))
    image = image.transpose(PILImage.Transpose.FLIP_TOP_BOTTOM)
    return Texture(image)


def create_smoke_texture():
    size = 128
    rng = random.Random(1989)
    blobs = [
        (
            rng.uniform(24, 104),
            rng.uniform(24, 104),
            rng.uniform(12, 30),
            rng.uniform(12, 28),
            rng.uniform(18, 40),
        )
        for _ in range(12)
    ]
    image = PILImage.new("RGBA", (size, size))
    pixels = []
    for y in range(size):
        for x in range(size):
            density = sum(
                strength
                * math.exp(
                    -(
                        ((x - center_x) / radius_x) ** 2
                        + ((y - center_y) / radius_y) ** 2
                    )
                )
                for center_x, center_y, radius_x, radius_y, strength in blobs
            )
            alpha = min(154, int(density * 1.7))
            pixels.append((82, 82, 78, alpha))
    image.putdata(pixels)
    image = image.filter(PILImageFilter.GaussianBlur(7))
    return Texture(image)


def enable_alpha_blending(entity):
    entity.setTransparency(TransparencyAttrib.MAlpha)
    entity.setDepthWrite(False)
