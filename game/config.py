from pathlib import Path

from ursina import color

from .models import InteractableDefinition, SnackKind

PACKAGE_RETURN_POSITION = (6.0, 5.0)
PACKAGE_RETURN_RADIUS = 1.8
SUPER_PACKAGE_SPEED_MULTIPLIER = 4
SUPER_PACKAGE_DURATION = 12.0
OFFICER_SALUTE_RADIUS = 4.5

TEXTURE_DIR = Path(__file__).resolve().parent.parent / "assets" / "textures"

AMBIENTCG_DIR = TEXTURE_DIR / "ambientcg"

MISSION_SECONDS = 300

PLAYER_SPEED = 4.2

AI_DECISION_INTERVAL = 6.0

TOWN_HEIGHT = 27

MAP_HEIGHT = 47

PLAZA_CENTER = (6.0, 5.0)

CAMPFIRE_POSITION = (21.5, 35.5)

POLICE_CAR_POSITION = (7.0, 11.0)

PLAYER_START = (17.5, 0, 23.5)

PLAYER_START_ROTATION = 0

HOUSE_POSITIONS = (
    (3.5, 10.2),
    (13.5, 10.2),
    (3.5, 16.8),
    (8.5, 16.8),
    (12.0, 16.8),
    (21.5, 10.2),
    (30.5, 10.2),
    (22.2, 16.8),
)

HOUSE_ROTATIONS = (180, 180, 0, 0, 0, 180, 180, 0)

HOUSE_NAMES = (
    "Market Square Tenement",
    "Clothing Store",
    "Apartment No. 12",
    "PSS Grocery Store",
    "Corner Tenement",
    "House on the Street",
    "Neighborhood Kiosk",
    "Caretaker's Lodge",
)

HOUSE_FACADE_COLORS = (
    color.rgb(144, 137, 119),
    color.rgb(131, 139, 126),
    color.rgb(151, 135, 119),
    color.rgb(135, 133, 121),
    color.rgb(142, 137, 119),
    color.rgb(128, 138, 128),
    color.rgb(150, 137, 116),
    color.rgb(131, 130, 118),
)

HOUSE_SIGNS = (
    "PSS",
    "RUCH",
    "12",
    "PSS",
    "ESTATE",
    "DISTRICT",
    "RUCH",
    "CARETAKER",
)

OFFICER_COUNT = 2
NEIGHBOR_COUNT = 15
GUARD_COUNT = OFFICER_COUNT + NEIGHBOR_COUNT
OFFICER_VISION_RADIUS = 12.0
OFFICER_ELIMINATION_RADIUS = 1.0

NEIGHBOR_STARTS = (
    (13.5, 10.5),
    (21.5, 11.5),
    (29.5, 12.5),
    (14.5, 15.5),
)

NEIGHBOR_COATS = (
    color.rgb(37, 76, 132),
    color.rgb(69, 104, 65),
    color.rgb(79, 112, 67),
    color.rgb(62, 91, 60),
)

NEIGHBOR_TROUSERS = (
    color.rgb(35, 44, 62),
    color.rgb(55, 57, 48),
    color.rgb(57, 48, 41),
    color.rgb(44, 49, 44),
)

INTERACTABLES: tuple[InteractableDefinition, ...] = (
    {
        "x": 19.5,
        "z": 11.5,
        "kind": "payphone",
        "name": "Payphone",
        "message": "You call home — your family adds 20 seconds",
        "time_bonus": 20,
    },
    {
        "x": 29.5,
        "z": 11.5,
        "kind": "bus_stop",
        "name": "Bus Stop",
        "message": "The bus never came, but you rest and recover your sprint energy",
        "sprint": True,
    },
    {
        "x": 9.5,
        "z": 19.5,
        "kind": "vending_machine",
        "name": "Soda Machine",
        "message": "An ice-cold orange soda! Flashlight recharged",
        "torch": 45,
    },
    {
        "x": 24.5,
        "z": 24.5,
        "kind": "electrical_box",
        "name": "Electrical Box",
        "message": "You find an R-20 battery in the box",
        "torch": 30,
    },
    {
        "x": 32.5,
        "z": 11.5,
        "kind": "timetable",
        "name": "Bus Timetable",
        "message": "A 1986 timetable — only 40 years late",
        "time_bonus": 10,
    },
)

SNACK_COUNT = 36

SNACK_MIN_SPACING = 1.8
NEIGHBOR_CHASE_SPEED_MULTIPLIER = 2
NEIGHBOR_PACKAGE_CAPACITY = 3

SNACK_KINDS: tuple[SnackKind, ...] = ("lollipop", "fudge", "pumpkin")

SNACK_COLORS = (
    color.rgb(255, 52, 94),
    color.rgb(255, 176, 38),
    color.rgb(45, 237, 255),
    color.rgb(205, 72, 255),
    color.rgb(84, 255, 92),
    color.rgb(255, 70, 224),
)


def create_map():
    width, height = 35, MAP_HEIGHT
    grid = [["." for _ in range(width)] for _ in range(height)]

    for x in range(width):
        grid[0][x] = grid[height - 1][x] = "#"
    for y in range(height):
        grid[y][0] = grid[y][width - 1] = "#"

    # Keep the original compact neighborhood as the old town district.
    for y in range(1, 10):
        if y not in (3, 7):
            grid[y][5] = "#"
    for x in range(5, 12):
        if x != 8:
            grid[4][x] = "#"
    for y in range(1, 5):
        if y != 2:
            grid[y][11] = "#"
    for x in range(1, 6):
        if x != 3:
            grid[8][x] = "#"
    for x in range(6, 16):
        if x not in (9, 13):
            grid[8][x] = "#"
    for x in range(11, 16):
        if x != 13:
            grid[6][x] = "#"
    for y in range(7, 12):
        if y != 9:
            grid[y][11] = "#"

    for z in (2, 6, 10):
        grid[z][16] = "."
    for x in (3, 8, 14):
        grid[12][x] = "."

    def perimeter(x1, z1, x2, z2, openings):
        for x in range(x1, x2 + 1):
            if (x, z1) not in openings:
                grid[z1][x] = "#"
            if (x, z2) not in openings:
                grid[z2][x] = "#"
        for z in range(z1, z2 + 1):
            if (x1, z) not in openings:
                grid[z][x1] = "#"
            if (x2, z) not in openings:
                grid[z][x2] = "#"

    perimeter(21, 2, 23, 8, {(22, 2), (21, 5), (23, 6)})
    perimeter(30, 3, 33, 8, {(31, 3), (30, 6), (33, 7)})
    perimeter(21, 19, 23, 24, {(22, 19), (21, 20), (23, 21)})
    perimeter(30, 19, 33, 24, {(31, 19), (30, 20), (33, 21)})

    for z in range(11, 16):
        for x in range(1, width - 1):
            grid[z][x] = "."
    for x in range(15, 20):
        for z in range(1, height - 1):
            grid[z][x] = "."
    for x in range(24, 29):
        for z in range(1, height - 1):
            grid[z][x] = "."
    for z in range(1, 9):
        for x in range(2, 10):
            grid[z][x] = "."

    for x in range(width):
        grid[TOWN_HEIGHT - 1][x] = "#"
    for x in range(15, 20):
        grid[TOWN_HEIGHT - 1][x] = "."
    for x in range(1, width - 1):
        grid[16][x] = "."
    for (house_x, house_z), rotation in zip(HOUSE_POSITIONS, HOUSE_ROTATIONS):
        min_x = int(house_x - 1.48)
        max_x = int(house_x + 1.48)
        min_z = int(house_z - 0.95)
        max_z = int(house_z + 0.95)
        for cell_z in range(min_z, max_z + 1):
            for cell_x in range(min_x, max_x + 1):
                if (
                    0 <= cell_x < width
                    and 0 <= cell_z < height
                    and abs(cell_x + 0.5 - house_x) <= 1.48
                    and abs(cell_z + 0.5 - house_z) <= 0.95
                ):
                    grid[cell_z][cell_x] = "H"
        grid[int(house_z)][int(house_x)] = "H"
        entrance_z = house_z + (1.5 if rotation == 180 else -1.5)
        grid[int(entrance_z)][int(house_x)] = "."
    for prop in INTERACTABLES:
        grid[int(prop["z"])][int(prop["x"])] = "."
    return grid
