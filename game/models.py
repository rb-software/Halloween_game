from __future__ import annotations

from typing import Literal, TypedDict

from ursina import Entity, Text

Cell = tuple[int, int]
SnackKind = Literal["lollipop", "fudge", "pumpkin"]
InteractableKind = Literal[
    "payphone",
    "bus_stop",
    "vending_machine",
    "electrical_box",
    "timetable",
]


class HouseState(TypedDict):
    x: float
    z: float
    visited: bool
    name: str


class HouseEntities(TypedDict):
    root: Entity
    base: Entity
    roof: Entity
    door: Entity
    name: str


class SnackState(TypedDict):
    x: float
    z: float
    phase: float
    kind: SnackKind
    collected: bool
    claimed_by: int | None
    path: list[Cell]
    repath_at: float
    entities: tuple[Entity, ...]


class InteractableDefinition(TypedDict, total=False):
    x: float
    z: float
    kind: InteractableKind
    name: str
    message: str
    time_bonus: int
    sprint: bool
    torch: int


class InteractableState(TypedDict):
    entity: InteractableDefinition
    used: bool
    position: tuple[float, float]


class GuardState(TypedDict):
    root: Entity
    head: Entity
    limbs: tuple[Entity, Entity, Entity, Entity]
    greeting_bubble: Text
    greeting_until: float
    sky_gazing_until: float
    next_sky_gaze_at: float
    sky_gaze_duration: float
    x: float
    z: float
    path: list[Cell]
    repath_at: float
    patrol_target: Cell
    phase: float
    speed: float
    chase_speed: float
    chase_radius: float
    model_controlled: bool
    is_officer: bool
    transformed_by_ufo: bool
    eliminated: bool
    ai_target: Cell | None
    ai_mode: Literal["patrol", "chase"]
    ai_inflight: bool
    ai_inflight_generation: int
    ai_retry_at: float
    package_glow: Entity
    package_count: int
    snack_target: int | None
    next_package_check_at: float
    speed_boost_until: float
    speed_boost_target: bool
    saluting_until: float
    throwing_until: float
    ufo_original_colors: list[tuple[Entity, object]] | None
