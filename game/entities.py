from .common import *


class EntityBuilder:
    def build_interactables(self):
        self.interactable_entities = []
        for prop in INTERACTABLES:
            x, z = prop["x"], prop["z"]
            if prop["kind"] == "telefon":
                Entity(
                    model="cube",
                    position=(x, 1.15, z),
                    scale=(0.55, 1.9, 0.42),
                    color=color.rgb(119, 115, 98),
                    texture=self.metal_texture,
                )
                Entity(
                    model="cube",
                    position=(x, 1.48, z - 0.23),
                    scale=(0.32, 0.48, 0.045),
                    color=color.rgb(62, 74, 70),
                )
                Entity(
                    model="cube",
                    position=(x, 1.76, z - 0.26),
                    scale=(0.25, 0.06, 0.04),
                    color=color.rgb(211, 185, 124),
                )
            elif prop["kind"] == "przystanek":
                Entity(
                    model="cube",
                    position=(x, 1.45, z),
                    scale=(2.0, 0.08, 0.08),
                    color=color.rgb(68, 77, 70),
                    texture=self.metal_texture,
                )
                for post_x in (-0.92, 0.92):
                    Entity(
                        model="cube",
                        position=(x + post_x, 0.9, z),
                        scale=(0.07, 1.1, 0.07),
                        color=color.rgb(70, 77, 67),
                        texture=self.metal_texture,
                    )
                Entity(
                    model="cube",
                    position=(x, 1.58, z - 0.05),
                    scale=(1.2, 0.4, 0.04),
                    color=color.rgb(141, 127, 95),
                )
            elif prop["kind"] == "automat":
                Entity(
                    model="cube",
                    position=(x, 0.95, z),
                    scale=(0.75, 1.8, 0.65),
                    color=color.rgb(102, 53, 49),
                    texture=self.metal_texture,
                )
                Entity(
                    model="cube",
                    position=(x, 1.15, z - 0.34),
                    scale=(0.45, 0.45, 0.035),
                    color=color.rgb(188, 163, 111),
                )
                Text(
                    parent=Entity(position=(x, 1.55, z - 0.37)),
                    text="ORANZADA",
                    origin=(0, 0),
                    scale=2,
                    color=color.rgb(240, 214, 164),
                )
            else:
                Entity(
                    model="cube",
                    position=(x, 1.55, z),
                    scale=(1.15, 1.5, 0.12),
                    color=color.rgb(117, 105, 77),
                    texture=self.metal_texture,
                )
                Entity(
                    model="cube",
                    position=(x, 1.63, z - 0.075),
                    scale=(0.9, 0.95, 0.035),
                    color=color.rgb(199, 190, 158),
                )
            self.interactable_entities.append(
                {"entity": prop, "used": False, "position": (x, z)}
            )

    def build_houses(self):
        for index, ((x, z), name, rotation) in enumerate(
            zip(HOUSE_POSITIONS, HOUSE_NAMES, HOUSE_ROTATIONS)
        ):
            root = Entity(position=(x, 0, z), rotation_y=rotation)
            base = Entity(
                parent=root,
                model=deepcopy(self.displaced_concrete_model),
                position=(0, 0.18, 0),
                scale=(3.2, 0.36, 2.1),
                color=color.rgb(146, 140, 124),
                texture=self.concrete_texture,
            )
            self.apply_surface_material(base, "concrete")
            facade_material = "brick" if index in (1, 4, 6) else "plaster"
            facade_color = HOUSE_FACADE_COLORS[index]
            facade_texture = (
                self.brick_texture if facade_material == "brick" else self.wall_texture
            )
            facade = Entity(
                parent=root,
                model=deepcopy(
                    self.brick_wall_model
                    if facade_material == "brick"
                    else self.displaced_wall_model
                ),
                position=(0, 1.68, 0),
                scale=(2.96, 2.86, 1.9),
                color=facade_color,
                texture=facade_texture,
            )
            facade.texture_scale = (2.3, 1.4)
            self.apply_surface_material(facade, facade_material)
            gable = Entity(
                parent=root,
                model=create_gable_mesh(2.96, 1.9, 0.86),
                position=(0, 3.08, 0),
                color=facade_color,
                texture=facade_texture,
                double_sided=True,
            )
            self.apply_surface_material(gable, facade_material)
            roof = Entity(
                parent=root,
                model="cube",
                position=(0, 3.39, -0.43),
                scale=(3.32, 0.13, 1.2),
                rotation_x=-30,
                color=color.rgb(155, 88, 66),
                texture=self.roof_texture,
            )
            roof.texture_scale = (3, 1.5)
            self.apply_surface_material(roof, "roofing")
            rear_roof = Entity(
                parent=root,
                model="cube",
                position=(0, 3.39, 0.43),
                scale=(3.32, 0.13, 1.2),
                rotation_x=30,
                color=color.rgb(155, 88, 66),
                texture=self.roof_texture,
            )
            rear_roof.texture_scale = (3, 1.5)
            self.apply_surface_material(rear_roof, "roofing")
            Entity(
                parent=root,
                model="cube",
                position=(0, 3.93, 0),
                scale=(3.42, 0.14, 0.16),
                color=color.rgb(119, 70, 54),
                texture=self.roof_texture,
            )
            chimney = Entity(
                parent=root,
                model="cube",
                position=(0.98, 4.12, 0.12),
                scale=(0.38, 0.68, 0.42),
                color=color.rgb(111, 83, 69),
                texture=self.brick_texture,
            )
            self.apply_surface_material(chimney, "brick")
            Entity(
                parent=root,
                model="cube",
                position=(0.98, 4.48, 0.12),
                scale=(0.48, 0.1, 0.5),
                color=color.rgb(101, 83, 72),
                texture=self.concrete_texture,
            )
            for gutter_side in (-1, 1):
                Entity(
                    parent=root,
                    model=self.cylinder_model,
                    position=(gutter_side * 1.48, 2.25, -0.97),
                    scale=(0.045, 2.1, 0.045),
                    color=color.rgb(92, 91, 82),
                    texture=self.metal_texture,
                )
            door = Entity(
                parent=root,
                model="cube",
                position=(0, 1.15, -1.0),
                scale=(0.58, 1.72, 0.07),
                color=color.rgb(109, 82, 60),
                texture=self.wood_texture,
            )
            Entity(
                parent=root,
                model="cube",
                position=(0, 2.06, -1.02),
                scale=(0.72, 0.1, 0.14),
                color=color.rgb(143, 131, 109),
                texture=self.concrete_texture,
            )
            for door_side in (-1, 1):
                Entity(
                    parent=root,
                    model="cube",
                    position=(door_side * 0.34, 1.18, -1.015),
                    scale=(0.1, 1.9, 0.16),
                    color=color.rgb(126, 116, 99),
                    texture=self.concrete_texture,
                )
            Entity(
                parent=root,
                model="cube",
                position=(0, 2.18, -1.02),
                scale=(0.76, 0.12, 0.17),
                color=color.rgb(126, 116, 99),
                texture=self.concrete_texture,
            )
            Entity(
                parent=root,
                model="cube",
                position=(0, 2.3, -1.22),
                scale=(1.32, 0.12, 0.66),
                color=color.rgb(128, 116, 95),
                texture=self.roof_texture,
            )
            for canopy_x in (-0.52, 0.52):
                Entity(
                    parent=root,
                    model="cube",
                    position=(canopy_x, 1.93, -1.43),
                    scale=(0.07, 0.64, 0.07),
                    color=color.rgb(98, 91, 77),
                    texture=self.wood_texture,
                )
            for floor_y in (1.15, 2.35):
                for window_x in (-0.89, 0.89):
                    Entity(
                        parent=root,
                        model="cube",
                        position=(window_x, floor_y, -1.0),
                        scale=(0.72, 0.88, 0.1),
                        color=color.rgb(105, 94, 75),
                        texture=self.wood_texture,
                    )
                    pane = Entity(
                        parent=root,
                        model="cube",
                        position=(window_x, floor_y, -1.057),
                        scale=(0.56, 0.68, 0.035),
                        color=color.rgba(89, 124, 132, 140),
                    )
                    enable_alpha_blending(pane)
                    Entity(
                        parent=root,
                        model="cube",
                        position=(window_x, floor_y, -1.08),
                        scale=(0.035, 0.68, 0.035),
                        color=color.rgb(132, 116, 90),
                    )
                    Entity(
                        parent=root,
                        model="cube",
                        position=(window_x, floor_y, -1.08),
                        scale=(0.56, 0.035, 0.035),
                        color=color.rgb(132, 116, 90),
                    )
                    Entity(
                        parent=root,
                        model="cube",
                        position=(window_x, floor_y - 0.49, -1.07),
                        scale=(0.82, 0.1, 0.25),
                        color=color.rgb(145, 136, 117),
                        texture=self.concrete_texture,
                    )
            for side in (-1, 1):
                Entity(
                    parent=root,
                    model=self.cylinder_model,
                    position=(side * 1.25, 0.55, -0.99),
                    scale=(0.065, 0.65, 0.065),
                    color=color.rgb(113, 106, 91),
                    texture=self.concrete_texture,
                )
            Entity(
                parent=root,
                model="cube",
                position=(0, 3.46, -1.0),
                scale=(0.52, 0.52, 0.08),
                color=color.rgb(110, 97, 79),
                texture=self.wood_texture,
            )
            Entity(
                parent=root,
                model="sphere",
                position=(0.19, 1.12, -1.07),
                scale=0.055,
                color=color.rgb(177, 151, 96),
            )
            Entity(
                parent=root,
                model="cube",
                position=(0, 3.46, -1.052),
                scale=(0.34, 0.34, 0.035),
                color=color.rgb(65, 76, 75),
            )
            Text(
                parent=root,
                text=HOUSE_SIGNS[index],
                origin=(0, 0),
                scale=1.0,
                color=color.rgb(66, 56, 44),
                position=(0, 2.48, -1.0),
            )
            self.house_entities.append(
                {
                    "root": root,
                    "base": base,
                    "roof": roof,
                    "door": door,
                    "name": name,
                }
            )

    def build_guard(self):
        self.guard_entities = []
        for index, (x, z) in enumerate(NEIGHBOR_STARTS):
            root = Entity(position=(x, 0, z))
            coat_color = NEIGHBOR_COATS[index]
            trouser_color = NEIGHBOR_TROUSERS[index]
            build = (0.94, 1.02, 0.98, 1.06)[index % 4]
            neck = Entity(
                parent=root,
                model=create_profile_mesh(
                    (
                        (0.78, 0.205, 0.135, 0),
                        (0.86, 0.225, 0.15, 0),
                        (1.02, 0.265, 0.165, 0),
                        (1.22, 0.29, 0.17, 0),
                        (1.39, 0.34, 0.155, 0),
                        (1.49, 0.30, 0.135, 0),
                        (1.54, 0.105, 0.095, 0),
                    ),
                    segments=24,
                ),
                scale=(build, build, build),
                color=coat_color,
                texture=self.fabric_texture,
            )
            Entity(
                parent=root,
                model=create_profile_mesh(
                    (
                        (0.70, 0.18, 0.125, 0),
                        (0.78, 0.23, 0.145, 0),
                        (0.87, 0.22, 0.14, 0),
                        (0.93, 0.19, 0.12, 0),
                    ),
                    segments=20,
                ),
                color=trouser_color,
                texture=self.fabric_texture,
            )
            Entity(
                parent=root,
                model=create_profile_mesh(
                    (
                        (1.43, 0.09, 0.085, 0),
                        (1.49, 0.105, 0.09, 0),
                        (1.60, 0.09, 0.085, 0),
                    ),
                    segments=16,
                ),
                color=color.white,
                texture=self.skin_texture,
            )
            self.apply_skin_material(neck)
            head = Entity(
                parent=root,
                position=(0, 1.48, 0.01),
            )
            face = Entity(
                parent=head,
                model=create_profile_mesh(
                    (
                        (0.045, 0.075, 0.082, 0),
                        (0.09, 0.105, 0.105, 0),
                        (0.17, 0.125, 0.115, 0),
                        (0.25, 0.135, 0.12, 0),
                        (0.34, 0.124, 0.11, 0),
                        (0.405, 0.085, 0.08, 0),
                        (0.43, 0.025, 0.03, 0),
                    ),
                    segments=24,
                ),
                scale=(build, 1, 1),
                color=color.white,
                texture=self.skin_texture,
            )
            self.apply_skin_material(face)
            hair_color = (
                color.rgb(48, 44, 39),
                color.rgb(77, 68, 53),
                color.rgb(55, 55, 54),
                color.rgb(64, 48, 39),
            )[index]
            nose = Entity(
                parent=head,
                model=create_profile_mesh(
                    (
                        (0.32, 0.124, 0.115, 0),
                        (0.37, 0.137, 0.12, 0),
                        (0.415, 0.117, 0.104, 0),
                        (0.445, 0.055, 0.055, 0),
                    ),
                    segments=20,
                ),
                color=hair_color,
                texture=self.fabric_texture,
            )
            for eye_x in (-0.049, 0.049):
                Entity(
                    parent=head,
                    model="sphere",
                    position=(eye_x, 0.251, 0.108),
                    scale=(0.041, 0.029, 0.018),
                    color=color.rgb(166, 139, 116),
                )
                Entity(
                    parent=head,
                    model="sphere",
                    position=(eye_x, 0.25, 0.124),
                    scale=(0.021, 0.018, 0.012),
                    color=color.rgb(34, 31, 29),
                )
            Entity(
                parent=head,
                model=create_profile_mesh(
                    (
                        (0.165, 0.012, 0.01, 0.135),
                        (0.205, 0.027, 0.025, 0.143),
                        (0.265, 0.014, 0.015, 0.122),
                    ),
                    segments=12,
                ),
                color=color.white,
                texture=self.skin_texture,
            )
            self.apply_skin_material(nose)
            Entity(
                parent=head,
                model="cube",
                position=(0, 0.137, 0.115),
                scale=(0.064, 0.009, 0.016),
                color=color.rgb(91, 58, 52),
            )
            for eye_x in (-0.049, 0.049):
                Entity(
                    parent=head,
                    model="sphere",
                    position=(eye_x, 0.29, 0.118),
                    scale=(0.046, 0.012, 0.022),
                    color=hair_color,
                )
            for side in (-1, 1):
                ear = Entity(
                    parent=head,
                    model="sphere",
                    position=(side * 0.13, 0.19, 0),
                    scale=(0.034, 0.065, 0.035),
                    color=color.white,
                    texture=self.skin_texture,
                )
                self.apply_skin_material(ear)

            for button_y in (0.96, 1.08, 1.20, 1.32):
                Entity(
                    parent=root,
                    model="sphere",
                    position=(0, button_y, 0.166 * build),
                    scale=0.018,
                    color=color.rgb(58, 52, 42),
                )
            for side in (-1, 1):
                Entity(
                    parent=root,
                    model="cube",
                    position=(side * 0.095, 1.39, 0.137),
                    scale=(0.11, 0.18, 0.025),
                    rotation=(0, side * 12, side * -22),
                    color=color.rgb(71, 67, 56),
                    texture=self.fabric_texture,
                )

            arms = []
            legs = []
            for side in (-1, 1):
                arm = Entity(
                    parent=root,
                    position=(side * 0.29 * build, 1.40, 0),
                )
                Entity(
                    parent=arm,
                    model=create_profile_mesh(
                        (
                            (-0.53, 0.065, 0.075, 0.015),
                            (-0.46, 0.075, 0.08, 0.012),
                            (-0.31, 0.092, 0.09, 0.008),
                            (-0.15, 0.105, 0.105, 0),
                            (-0.03, 0.105, 0.105, 0),
                        ),
                        segments=16,
                    ),
                    color=coat_color,
                    texture=self.fabric_texture,
                )
                Entity(
                    parent=arm,
                    model=create_profile_mesh(
                        (
                            (-0.68, 0.046, 0.055, 0.02),
                            (-0.61, 0.06, 0.065, 0.02),
                            (-0.48, 0.074, 0.075, 0.016),
                            (-0.38, 0.065, 0.07, 0.012),
                        ),
                        segments=16,
                    ),
                    color=coat_color,
                    texture=self.fabric_texture,
                )
                hand = Entity(
                    parent=arm,
                    model="sphere",
                    position=(0.02, -0.70, 0.025),
                    scale=(0.07, 0.095, 0.07),
                    color=color.white,
                    texture=self.skin_texture,
                )
                self.apply_skin_material(hand)
                arms.append(arm)

                leg = Entity(
                    parent=root,
                    position=(side * 0.12, 0.82, 0),
                )
                Entity(
                    parent=leg,
                    model=create_profile_mesh(
                        (
                            (-0.73, 0.075, 0.085, 0),
                            (-0.63, 0.085, 0.09, 0),
                            (-0.49, 0.09, 0.095, 0),
                            (-0.34, 0.105, 0.11, 0),
                            (-0.20, 0.12, 0.12, 0),
                            (-0.08, 0.12, 0.12, 0),
                            (0.02, 0.12, 0.12, 0),
                        ),
                        segments=16,
                    ),
                    color=trouser_color,
                    texture=self.fabric_texture,
                )
                Entity(
                    parent=leg,
                    model="cube",
                    position=(0, -0.765, 0.08),
                    scale=(0.15, 0.11, 0.29),
                    color=color.rgb(35, 35, 33),
                    texture=self.metal_texture,
                )
                Entity(
                    parent=leg,
                    model="cube",
                    position=(0, -0.65, 0.005),
                    scale=(0.15, 0.13, 0.15),
                    color=trouser_color,
                    texture=self.fabric_texture,
                )
                legs.append(leg)

            if index == 0:
                Entity(
                    parent=head,
                    model="cube",
                    position=(0, 0.43, -0.005),
                    scale=(0.31, 0.075, 0.26),
                    color=color.rgb(54, 59, 51),
                    texture=self.fabric_texture,
                )
                Entity(
                    parent=head,
                    model="sphere",
                    position=(0, 0.39, 0.115),
                    scale=(0.14, 0.035, 0.035),
                    color=color.rgb(42, 37, 32),
                )
            else:
                Entity(
                    parent=head,
                    model=create_profile_mesh(
                        (
                            (0.35, 0.125, 0.12, 0),
                            (0.39, 0.14, 0.13, 0),
                            (0.43, 0.11, 0.1, 0),
                            (0.445, 0.045, 0.045, 0),
                        ),
                        segments=20,
                    ),
                    color=color.rgb(56, 58, 52),
                    texture=self.fabric_texture,
                )
            self.guard_entities.append(
                {
                    "root": root,
                    "head": head,
                    "limbs": (arms[0], arms[1], legs[0], legs[1]),
                    "x": x,
                    "z": z,
                    "path": [],
                    "repath_at": 0.0,
                    "waypoint_index": index * 2,
                    "phase": index * 1.7,
                    "speed": 0.68 + index * 0.055,
                    "chase_speed": 1.2 + index * 0.06,
                    "chase_radius": 4.5 + index * 0.3,
                    "model_controlled": index == 0,
                    "ai_target": None,
                    "ai_mode": "patrol",
                    "ai_inflight": False,
                    "ai_inflight_generation": -1,
                    "ai_retry_at": 0.0,
                }
            )
