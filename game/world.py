from .world_city import WorldCityBuilder
from .world_fire import WorldFireBuilder
from .world_landmarks import WorldLandmarkBuilder
from .world_nature import WorldNatureBuilder


class WorldBuilder(
    WorldCityBuilder,
    WorldNatureBuilder,
    WorldFireBuilder,
    WorldLandmarkBuilder,
):
    pass
