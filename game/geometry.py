import math
import random

from panda3d.core import TransparencyAttrib
from PIL import Image as PILImage
from PIL import ImageChops as PILImageChops
from PIL import ImageDraw as PILImageDraw
from PIL import ImageFilter as PILImageFilter
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


def create_sky_hemisphere_mesh(radius=1, longitude_segments=64, latitude_segments=32):
    vertices = []
    uvs = []
    triangles = []
    for row in range(latitude_segments):
        latitude = math.pi * 0.5 * row / latitude_segments
        vertical_radius = radius * math.cos(latitude)
        height = radius * math.sin(latitude)
        v = row / latitude_segments
        for column in range(longitude_segments + 1):
            longitude = math.tau * column / longitude_segments
            vertices.append(
                (
                    vertical_radius * math.sin(longitude),
                    height,
                    vertical_radius * math.cos(longitude),
                )
            )
            uvs.append((column / longitude_segments, v))

    row_width = longitude_segments + 1
    for row in range(latitude_segments - 1):
        for column in range(longitude_segments):
            lower_left = row * row_width + column
            lower_right = lower_left + 1
            upper_left = lower_left + row_width
            upper_right = upper_left + 1
            triangles.extend(
                (
                    (lower_left, upper_left, upper_right),
                    (lower_left, upper_right, lower_right),
                )
            )

    pole_y = radius
    pole_start = len(vertices)
    for column in range(longitude_segments):
        vertices.append((0, pole_y, 0))
        uvs.append(((column + 0.5) / longitude_segments, 1))
        lower_left = (latitude_segments - 1) * row_width + column
        lower_right = lower_left + 1
        triangles.append((lower_left, pole_start + column, lower_right))

    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, static=True)


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


def create_shirt_front_mesh():
    vertices = (
        (0, 1.48, 0.14),
        (-0.07, 1.40, 0.15),
        (-0.18, 1.08, 0.14),
        (0, 0.98, 0.17),
        (0.18, 1.08, 0.14),
        (0.07, 1.40, 0.15),
    )
    triangles = (
        (0, 1, 2),
        (0, 2, 3),
        (0, 3, 4),
        (0, 4, 5),
    )
    uvs = (
        (0.5, 1),
        (0.35, 0.8),
        (0, 0.2),
        (0.5, 0),
        (1, 0.2),
        (0.65, 0.8),
    )
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


def create_ship_hull_mesh():
    sections = (
        (-2.5, 0.03, 0.2, 0.32, 0.42),
        (-1.7, 0.38, -0.18, 0.02, 0.48),
        (1.55, 0.58, -0.18, 0.02, 0.48),
        (2.4, 0.25, 0.0, 0.12, 0.48),
    )
    vertices = []
    uvs = []
    triangles = []
    points_per_section = 5
    for section_index, (x, half_width, bottom, side, deck) in enumerate(sections):
        cross_section = (
            (bottom, 0),
            (side, -half_width * 0.72),
            (deck, -half_width),
            (deck, half_width),
            (side, half_width * 0.72),
        )
        for point_index, (y, z) in enumerate(cross_section):
            vertices.append((x, y, z))
            uvs.append(
                (section_index / (len(sections) - 1), point_index / points_per_section)
            )

    for section_index in range(len(sections) - 1):
        start = section_index * points_per_section
        next_start = start + points_per_section
        for point_index in range(points_per_section):
            next_point = (point_index + 1) % points_per_section
            triangles.extend(
                (
                    (start + point_index, start + next_point, next_start + next_point),
                    (start + point_index, next_start + next_point, next_start + point_index),
                )
            )

    for section_index, reverse in ((0, True), (len(sections) - 1, False)):
        center = len(vertices)
        x, _, bottom, _, _ = sections[section_index]
        vertices.append((x, bottom + 0.12, 0))
        uvs.append((section_index / (len(sections) - 1), 0.5))
        start = section_index * points_per_section
        for point_index in range(points_per_section):
            next_point = (point_index + 1) % points_per_section
            triangle = (center, start + point_index, start + next_point)
            triangles.append(triangle[::-1] if reverse else triangle)

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


def create_original_galaxy_sky(width=2048, height=1024, seed=31031):
    rng = random.Random(seed)
    sky = PILImage.new("RGB", (width, height))
    sky_draw = PILImageDraw.Draw(sky)
    for y in range(height):
        blend = y / max(1, height - 1)
        sky_draw.line(
            (0, y, width, y),
            fill=(
                round(2 + blend * 5),
                round(4 + blend * 6),
                round(15 + blend * 12),
            ),
        )
    sky = sky.convert("RGBA")
    center_x = width * 0.52
    center_y = height * 0.45
    disk_radius = width * 0.44
    disk_flattening = 0.24
    tilt_degrees = -11
    tilt = math.radians(tilt_degrees)

    def project(radius, angle):
        local_x = radius * math.cos(angle)
        local_y = radius * math.sin(angle) * disk_flattening
        return (
            center_x + local_x * math.cos(tilt) - local_y * math.sin(tilt),
            center_y + local_x * math.sin(tilt) + local_y * math.cos(tilt),
        )

    def oval_layer(rgb, opacity, radius_x, radius_y, blur):
        layer = PILImage.new("RGBA", (width, height))
        PILImageDraw.Draw(layer).ellipse(
            (
                center_x - radius_x,
                center_y - radius_y,
                center_x + radius_x,
                center_y + radius_y,
            ),
            fill=(*rgb, opacity),
        )
        layer = layer.rotate(
            tilt_degrees,
            resample=PILImage.Resampling.BICUBIC,
            center=(center_x, center_y),
        )
        return (
            layer.filter(PILImageFilter.GaussianBlur(blur))
            if blur
            else layer
        )

    sky.alpha_composite(
        oval_layer(
            (68, 96, 255),
            26,
            disk_radius * 1.12,
            disk_radius * 0.40,
            width // 28,
        )
    )
    sky.alpha_composite(
        oval_layer(
            (75, 96, 194),
            44,
            disk_radius,
            disk_radius * 0.30,
            width // 62,
        )
    )

    noise_size = (max(32, width // 10), max(16, height // 10))
    coarse_noise = PILImage.new("L", noise_size)
    coarse_noise.putdata(
        [rng.randrange(256) for _ in range(noise_size[0] * noise_size[1])]
    )
    noise = coarse_noise.resize((width, height), PILImage.Resampling.BICUBIC)
    fine_noise = PILImage.new("L", (width, height))
    fine_noise.putdata([rng.randrange(256) for _ in range(width * height)])
    noise = PILImage.blend(
        fine_noise.filter(PILImageFilter.GaussianBlur(width // 160)),
        noise,
        0.72,
    )

    arm_points = []
    arm_mask = PILImage.new("L", (width, height))
    arm_mask_draw = PILImageDraw.Draw(arm_mask)
    for arm_index in range(2):
        points = []
        for step in range(620):
            radius = disk_radius * (0.09 + 0.91 * step / 619)
            angle = (
                arm_index * math.pi
                + math.log(radius / (disk_radius * 0.09)) * 1.65
            )
            points.append(project(radius, angle))
        arm_points.append(points)
        arm_mask_draw.line(
            points,
            fill=255,
            width=max(18, width // 13),
            joint="curve",
        )
    arm_mask = arm_mask.filter(PILImageFilter.GaussianBlur(width // 30))
    textured_mask = PILImageChops.multiply(
        arm_mask,
        noise.point(lambda value: int(126 + value * 0.50)),
    )
    arms = PILImage.new("RGBA", (width, height), (145, 177, 255, 0))
    arms.putalpha(textured_mask.point(lambda value: int(value * 0.9)))
    sky.alpha_composite(arms)

    hii_regions = PILImage.new("RGBA", (width, height))
    hii_draw = PILImageDraw.Draw(hii_regions)
    for points in arm_points:
        for _ in range(170):
            x, y = points[rng.randrange(25, len(points) - 25)]
            radius = rng.uniform(width / 90, width / 28)
            hii_draw.ellipse(
                (x - radius, y - radius * 0.55, x + radius, y + radius * 0.55),
                fill=(
                    rng.randint(152, 218),
                    rng.randint(184, 232),
                    rng.randint(220, 255),
                    rng.randint(38, 118),
                ),
            )
    sky.alpha_composite(hii_regions.filter(PILImageFilter.GaussianBlur(width // 105)))

    dust = PILImage.new("RGBA", (width, height))
    dust_draw = PILImageDraw.Draw(dust)
    for arm_index, points in enumerate(arm_points):
        dust_lane = []
        for index in range(220, 600):
            previous = points[index - 1]
            following = points[index + 1]
            tangent_x = following[0] - previous[0]
            tangent_y = following[1] - previous[1]
            tangent_length = max(1.0, math.hypot(tangent_x, tangent_y))
            offset = width * (0.026 if arm_index == 0 else -0.026)
            dust_lane.append(
                (
                    points[index][0] - tangent_y / tangent_length * offset,
                    points[index][1] + tangent_x / tangent_length * offset,
                )
            )
        dust_draw.line(
            dust_lane,
            fill=(16, 11, 23, 104),
            width=max(4, width // 85),
            joint="curve",
        )
    sky.alpha_composite(dust.filter(PILImageFilter.GaussianBlur(width // 220)))

    sky.alpha_composite(
        oval_layer(
            (255, 190, 110),
            112,
            disk_radius * 0.32,
            disk_radius * 0.13,
            width // 26,
        )
    )
    bulge = PILImage.new("RGBA", (width, height))
    bulge_draw = PILImageDraw.Draw(bulge)
    for index in range(36, 0, -1):
        scale = index / 36
        radius_x = disk_radius * 0.27 * scale
        radius_y = disk_radius * 0.10 * scale
        opacity = int((1 - scale) ** 2 * 230)
        bulge_draw.ellipse(
            (
                center_x - radius_x,
                center_y - radius_y,
                center_x + radius_x,
                center_y + radius_y,
            ),
            fill=(
                255,
                int(205 + 40 * (1 - scale)),
                int(148 + 70 * (1 - scale)),
                opacity,
            ),
        )
    bulge = bulge.rotate(
        tilt_degrees,
        resample=PILImage.Resampling.BICUBIC,
        center=(center_x, center_y),
    )
    sky.alpha_composite(bulge.filter(PILImageFilter.GaussianBlur(width // 65)))

    star_layer = PILImage.new("RGBA", (width, height))
    star_draw = PILImageDraw.Draw(star_layer)
    for _ in range(width * height // 420):
        star_x = rng.randrange(width)
        star_y = rng.randrange(height)
        brightness = rng.randint(105, 220)
        star_draw.point(
            (star_x, star_y),
            fill=(brightness, brightness, min(255, brightness + 26), 255),
        )
    sky.alpha_composite(star_layer)
    return sky.convert("RGB")


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
