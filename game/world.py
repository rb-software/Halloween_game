from .world_city import WorldCityBuilder
from .world_fire import WorldFireBuilder
from .world_landmarks import WorldLandmarkBuilder
from .world_nature import WorldNatureBuilder
from .world_ufo import WorldUFOBuilder


class WorldBuilder(
    WorldCityBuilder,
    WorldNatureBuilder,
    WorldFireBuilder,
    WorldLandmarkBuilder,
    WorldUFOBuilder,
):
    pass
