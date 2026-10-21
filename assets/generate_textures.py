import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


OUTPUT_DIR = Path(__file__).resolve().parent / "textures"
SEED = 1986


def noisy_surface(size, base_color, rng, amplitude=14, cells=24):
    width, height = size
    grid = [
        [rng.uniform(-amplitude, amplitude) for _ in range(cells)] for _ in range(cells)
    ]
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        gy = y * cells / height
        y0 = int(gy)
        fy = gy - y0
        for x in range(width):
            gx = x * cells / width
            x0 = int(gx)
            fx = gx - x0
            top = (
                grid[y0 % cells][x0 % cells] * (1 - fx)
                + grid[y0 % cells][(x0 + 1) % cells] * fx
            )
            bottom = (
                grid[(y0 + 1) % cells][x0 % cells] * (1 - fx)
                + grid[(y0 + 1) % cells][(x0 + 1) % cells] * fx
            )
            variation = top * (1 - fy) + bottom * fy + rng.uniform(-3, 3)
            pixels[x, y] = tuple(
                max(0, min(255, int(channel + variation))) for channel in base_color
            )
    return image


def make_tileable(image, blend_width=24):
    image = image.convert("RGB")
    width, height = image.size
    pixels = image.load()

    def blend_edges(length, outer_size, read_pixel, write_pixel):
        size = min(blend_width, length // 4)
        for outer in range(size):
            mix = (size - outer) / size * 0.5
            for offset in range(outer_size):
                first = read_pixel(outer, offset)
                last = read_pixel(length - outer - 1, offset)
                average = tuple(
                    int(first[channel] * (1 - mix) + last[channel] * mix)
                    for channel in range(3)
                )
                write_pixel(outer, offset, average)
                write_pixel(length - outer - 1, offset, average)
        return size

    blend_edges(
        width,
        height,
        lambda x, y: pixels[x, y],
        lambda x, y, value: pixels.__setitem__((x, y), value),
    )
    blend_edges(
        height,
        width,
        lambda y, x: pixels[x, y],
        lambda y, x, value: pixels.__setitem__((x, y), value),
    )
    return image


def make_cobblestone(rng):
    image = noisy_surface((512, 512), (61, 63, 59), rng, amplitude=8, cells=50)
    draw = ImageDraw.Draw(image)
    stone_colors = ((93, 91, 82), (82, 84, 78), (108, 103, 91), (73, 77, 72))
    for row in range(10):
        offset = 22 if row % 2 else 0
        y0 = row * 52
        for column in range(9):
            x0 = column * 62 - offset
            stone_color = rng.choice(stone_colors)
            points = [
                (x0 + rng.randrange(5, 11), y0 + rng.randrange(2, 8)),
                (x0 + rng.randrange(48, 59), y0 + rng.randrange(1, 9)),
                (x0 + rng.randrange(52, 62), y0 + rng.randrange(36, 48)),
                (x0 + rng.randrange(5, 15), y0 + rng.randrange(39, 51)),
            ]
            draw.rectangle(
                (x0 + 2, y0 + 2, x0 + 60, y0 + 50),
                fill=(44, 46, 43),
            )
            draw.polygon(points, fill=stone_color, outline=(47, 49, 45))
            for _ in range(24):
                x = rng.randrange(max(0, x0 + 8), min(512, x0 + 55))
                y = rng.randrange(y0 + 8, y0 + 45)
                draw.point(
                    (x, y),
                    fill=rng.choice(((67, 68, 61), (123, 118, 104), (75, 77, 71))),
                )
    return image


def make_wood(rng):
    image = noisy_surface((256, 256), (107, 80, 55), rng, amplitude=11)
    draw = ImageDraw.Draw(image)
    for x in range(0, 257, 32):
        draw.line((x, 0, x, 256), fill=(66, 54, 41), width=2)
        draw.line((x + 2, 0, x + 2, 256), fill=(145, 111, 73), width=1)
        for _ in range(13):
            grain_x = x + rng.randrange(4, 28)
            y = rng.randrange(256)
            draw.line(
                (
                    grain_x,
                    y,
                    grain_x + rng.randrange(-2, 3),
                    min(255, y + rng.randrange(8, 45)),
                ),
                fill=rng.choice(((81, 64, 47), (143, 105, 68), (94, 70, 49))),
                width=1,
            )
    for _ in range(10):
        x, y = rng.randrange(256), rng.randrange(256)
        draw.ellipse((x, y, x + 5, y + 2), fill=(65, 52, 40))
    return image


def make_worn_fabric(rng):
    image = noisy_surface((256, 256), (61, 63, 57), rng, amplitude=13, cells=40)
    draw = ImageDraw.Draw(image)
    for offset in range(0, 256, 3):
        thread = rng.choice((-3, -2, 2, 3))
        draw.line(
            (offset, 0, offset, 255),
            fill=tuple(max(0, min(255, channel + thread)) for channel in (61, 63, 57)),
            width=1,
        )
        draw.line(
            (0, offset, 255, offset),
            fill=tuple(max(0, min(255, channel - thread)) for channel in (61, 63, 57)),
            width=1,
        )
    for _ in range(35):
        x, y = rng.randrange(256), rng.randrange(256)
        draw.line(
            (
                x,
                y,
                min(255, x + rng.randrange(2, 14)),
                min(255, y + rng.randrange(8, 34)),
            ),
            fill=rng.choice(((38, 42, 40), (91, 86, 72), (106, 95, 75))),
            width=1,
        )
    return image.filter(ImageFilter.GaussianBlur(0.35))


def make_oxidized_metal(rng):
    image = noisy_surface((256, 256), (75, 79, 75), rng, amplitude=16, cells=36)
    patina = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(patina)
    for _ in range(95):
        x, y = rng.randrange(256), rng.randrange(256)
        radius = rng.randrange(3, 20)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=rng.choice(
                ((112, 66, 43, 150), (137, 83, 52, 130), (54, 87, 76, 115))
            ),
        )
    image = Image.alpha_composite(
        image.convert("RGBA"), patina.filter(ImageFilter.GaussianBlur(3))
    )
    draw = ImageDraw.Draw(image)
    for y in range(16, 256, 48):
        draw.line((0, y, 255, y), fill=(39, 43, 41, 210), width=2)
    return image.convert("RGB")


def make_skin(rng):
    image = noisy_surface((256, 256), (117, 91, 72), rng, amplitude=6, cells=38)
    draw = ImageDraw.Draw(image)
    for _ in range(500):
        x, y = rng.randrange(256), rng.randrange(256)
        shade = rng.choice((-11, -8, -5, 5, 8))
        draw.point(
            (x, y),
            fill=tuple(max(0, min(255, channel + shade)) for channel in (117, 91, 72)),
        )
    for _ in range(22):
        x, y = rng.randrange(256), rng.randrange(256)
        radius = rng.choice((1, 1, 2))
        draw.ellipse(
            (x, y, x + radius, y + radius),
            fill=rng.choice(((106, 79, 64), (129, 99, 78), (143, 111, 87))),
        )
    return image.filter(ImageFilter.GaussianBlur(0.2))


def make_stained_paper(rng):
    image = noisy_surface((256, 256), (105, 96, 78), rng, amplitude=15, cells=34)
    draw = ImageDraw.Draw(image)
    for _ in range(95):
        x, y = rng.randrange(256), rng.randrange(256)
        length = rng.randrange(8, 64)
        shade = rng.choice((55, 64, 77, 128, 143))
        draw.line(
            (x, y, min(255, x + length), max(0, y + rng.randrange(-3, 4))),
            fill=(shade, shade - 3, max(0, shade - 10)),
            width=rng.choice((1, 1, 2)),
        )
    for _ in range(14):
        x, y = rng.randrange(256), rng.randrange(256)
        radius = rng.randrange(3, 13)
        draw.ellipse((x, y, x + radius, y + radius), fill=(73, 65, 54))
    return image.filter(ImageFilter.GaussianBlur(0.3))


def make_sky(rng):
    width, height = 1024, 512
    resampling = getattr(Image, "Resampling", Image).BICUBIC
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    top, horizon = (54, 132, 201), (197, 218, 225)
    for y in range(height):
        t = y / (height - 1)
        blend = t * t * (3 - 2 * t)
        haze = max(0.0, (t - 0.56) / 0.44)
        row_color = tuple(
            int(
                top[channel] * (1 - blend)
                + horizon[channel] * blend
                + (9, 3, -4)[channel] * haze
            )
            for channel in range(3)
        )
        for x in range(width):
            noise = rng.randrange(-2, 3)
            pixels[x, y] = tuple(
                max(0, min(255, channel + noise)) for channel in row_color
            )

    sun_x, sun_y = 765, 300
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for radius, alpha in ((118, 10), (76, 18), (42, 36), (23, 90)):
        glow_draw.ellipse(
            (sun_x - radius, sun_y - radius, sun_x + radius, sun_y + radius),
            fill=(255, 224, 164, alpha),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    image = Image.alpha_composite(image.convert("RGBA"), glow)

    noise_layers = []
    for noise_width, noise_height in ((32, 16), (64, 32), (128, 64)):
        noise = Image.new("L", (noise_width, noise_height))
        noise_pixels = noise.load()
        for y in range(noise_height):
            for x in range(noise_width):
                noise_pixels[x, y] = rng.randrange(256)
            noise_pixels[noise_width - 1, y] = noise_pixels[0, y]
        noise_layers.append(noise.resize((width, height), resampling))
    cloud_mask = Image.new("L", (width, height))
    cloud_pixels = cloud_mask.load()
    for y in range(height):
        for x in range(width):
            cloud_value = (
                noise_layers[0].getpixel((x, y)) * 0.55
                + noise_layers[1].getpixel((x, y)) * 0.3
                + noise_layers[2].getpixel((x, y)) * 0.15
            )
            height_fade = min(1.0, max(0.0, (y - 125) / 45), max(0.0, (375 - y) / 55))
            cloud_pixels[x, y] = int(
                max(0, min(175, (cloud_value - 122) * 2.2)) * height_fade
            )
    cloud_mask = cloud_mask.filter(ImageFilter.GaussianBlur(1.8))
    clouds = Image.new("RGBA", (width, height), (235, 241, 245, 0))
    clouds.putalpha(cloud_mask)
    image = Image.alpha_composite(image, clouds)
    draw = ImageDraw.Draw(image)
    draw.ellipse(
        (sun_x - 13, sun_y - 13, sun_x + 13, sun_y + 13),
        fill=(255, 245, 215, 240),
    )
    return image.convert("RGB")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    textures = {
        "cobblestone.png": make_cobblestone(rng),
        "weathered_wood.png": make_wood(rng),
        "worn_fabric.png": make_worn_fabric(rng),
        "oxidized_metal.png": make_oxidized_metal(rng),
        "weathered_skin.png": make_skin(rng),
        "stained_paper.png": make_stained_paper(rng),
        "overcast_sky.png": make_sky(rng),
    }
    for filename, image in textures.items():
        if filename != "overcast_sky.png":
            image = make_tileable(image)
        image.save(OUTPUT_DIR / filename, format="PNG", optimize=True)
        print(f"Generated {filename}: {image.width}x{image.height}")


if __name__ == "__main__":
    main()
