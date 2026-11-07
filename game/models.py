from typing import Literal, Optional, TypedDict

from ursina import Entity

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
    path: list[Cell]
    repath_at: float
    entities: tuple[Entity, Entity]


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
    x: float
    z: float
    path: list[Cell]
    repath_at: float
    waypoint_index: int
    phase: float
    speed: float
    chase_speed: float
    chase_radius: float
    model_controlled: bool
    ai_target: Optional[Cell]
    ai_mode: Literal["patrol", "chase"]
    ai_inflight: bool
    ai_inflight_generation: int
    ai_retry_at: float
