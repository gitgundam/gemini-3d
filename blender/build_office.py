#!/usr/bin/env python3
"""
Blender 5.2 procedural builder for the Office Pixel-Art Isometric Diorama.
Reconstructs the user's real office from the walkthrough videos in a crisp
Japanese low-poly + nearest-neighbor pixel-art diorama style.

Outputs:
  - /Users/wangwei/Desktop/demo/gemini-3d/blender/office_diorama.blend
  - /Users/wangwei/Desktop/demo/gemini-3d/web/public/office_diorama.glb
  - Preview renders in /Users/wangwei/Desktop/demo/gemini-3d/blender/renders/
"""
import os
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

TEX_DIR = "/Users/wangwei/Desktop/demo/gemini-3d/blender/textures"
BLEND_OUT = "/Users/wangwei/Desktop/demo/gemini-3d/blender/office_diorama.blend"
GLB_OUT = "/Users/wangwei/Desktop/demo/gemini-3d/web/public/office_diorama.glb"
RENDER_DIR = "/Users/wangwei/Desktop/demo/gemini-3d/blender/renders"

os.makedirs(os.path.dirname(GLB_OUT), exist_ok=True)
os.makedirs(RENDER_DIR, exist_ok=True)

random.seed(2026)

# ---------------------------------------------------------------------------
# 1. Reset scene & create parent groups
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Ensure unit settings (meters)
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

# Create semantic Empty parents (preserved cleanly in GLB hierarchy!)
GROUPS = {}
GROUP_NAMES = [
    "ArchitectureGroup",
    "CutawayFrontGroup",
    "CeilingGroup",
    "HangingSignsGroup",
    "PantryGroup",
    "WorkstationsGroup",
    "UserDeskGroup",
    "HeroDetailsGroup",
    "CharactersGroup",
]
for gname in GROUP_NAMES:
    emp = bpy.data.objects.new(gname, None)
    scene.collection.objects.link(emp)
    GROUPS[gname] = emp


# ---------------------------------------------------------------------------
# 2. Material & Texture Helpers (Crisp Nearest-Neighbor Pixel Art!)
# ---------------------------------------------------------------------------
MAT_CACHE = {}
IMG_CACHE = {}


def load_image(filename):
    if filename in IMG_CACHE:
        return IMG_CACHE[filename]
    path = os.path.join(TEX_DIR, filename)
    img = bpy.data.images.load(path, check_existing=True)
    img.pack()
    IMG_CACHE[filename] = img
    return img


def make_color_mat(name, rgba, roughness=0.92, metallic=0.0, emission=0.0, alpha=1.0):
    if name in MAT_CACHE:
        return MAT_CACHE[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (rgba[0], rgba[1], rgba[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.12
    if alpha < 0.999:
        bsdf.inputs["Alpha"].default_value = alpha
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
    if emission > 0.0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (rgba[0], rgba[1], rgba[2], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission
    MAT_CACHE[name] = mat
    return mat


def make_tex_mat(name, filename, roughness=0.92, metallic=0.0, emission=0.0, use_alpha=False, alpha_clip=False):
    if name in MAT_CACHE:
        return MAT_CACHE[name]
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.08

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = load_image(filename)
    tex.interpolation = 'Closest'  # CRISP PIXEL ART!
    tex.extension = 'REPEAT'
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    if emission > 0.0 and "Emission Color" in bsdf.inputs:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission

    if use_alpha:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'CLIP' if alpha_clip else 'BLEND'
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'DITHERED' if alpha_clip else 'BLENDED'
        if alpha_clip and hasattr(mat, "alpha_threshold"):
            mat.alpha_threshold = 0.5

    MAT_CACHE[name] = mat
    return mat


# Pre-build Material Library (Cohesive warm-pastel Image #1 diorama palette)
M = {
    "floor_marble": make_tex_mat("M_FloorMarble", "floor_marble.png", roughness=0.82),
    "wall_plaster": make_tex_mat("M_WallPlaster", "wall_plaster.png", roughness=0.95),
    "wall_wood": make_tex_mat("M_WallWood", "wall_wood_panel.png", roughness=0.90),
    "cab_taupe": make_tex_mat("M_CabTaupe", "cabinet_taupe.png", roughness=0.88),
    "cab_white": make_tex_mat("M_CabWhite", "cabinet_white.png", roughness=0.88),
    "dark_door": make_tex_mat("M_DarkDoor", "dark_door.png", roughness=0.85),
    "pennant": make_tex_mat("M_Pennant", "pennant_hangbaole.png", roughness=0.88, use_alpha=True, alpha_clip=True),
    "wall_honor": make_tex_mat("M_WallHonor", "wall_honor.png", roughness=0.92),
    "wall_info": make_tex_mat("M_WallInfo", "wall_infographic.png", roughness=0.92),
    "lobby_fu": make_tex_mat("M_LobbyFu", "lobby_fu.png", roughness=0.92),
    "wuhan_glass": make_tex_mat("M_WuhanGlass", "wuhan_glass.png", roughness=0.35, use_alpha=True, alpha_clip=False),
    "window_city": make_tex_mat("M_WindowCity", "window_city.png", roughness=0.45, emission=0.22),
    "blind_grey": make_tex_mat("M_BlindGrey", "blind_grey.png", roughness=0.94),
    "sign_jishu": make_tex_mat("M_SignJishu", "sign_jishu.png", roughness=0.86),
    "sign_pinye": make_tex_mat("M_SignPinye", "sign_pinye.png", roughness=0.86),
    "sign_promo": make_tex_mat("M_SignPromo", "sign_promo.png", roughness=0.86),
    "exit_sign": make_tex_mat("M_ExitSign", "exit_sign.png", roughness=0.6, emission=1.2),
    "screen_ide": make_tex_mat("M_ScreenIDE", "screen_ide.png", roughness=0.5, emission=0.65),
    "screen_user_l": make_tex_mat("M_ScreenUserL", "screen_user_left.png", roughness=0.5, emission=0.72),
    "screen_user_r": make_tex_mat("M_ScreenUserR", "screen_user_right.png", roughness=0.5, emission=0.72),
    "screen_chat": make_tex_mat("M_ScreenChat", "screen_chat.png", roughness=0.5, emission=0.65),
    "screen_tv": make_tex_mat("M_ScreenTV", "screen_tv.png", roughness=0.5, emission=0.75),
    "kb_user": make_tex_mat("M_KbUser", "keyboard_user.png", roughness=0.88),
    "kb_std": make_tex_mat("M_KbStd", "keyboard_std.png", roughness=0.88),
    "fridge_front": make_tex_mat("M_FridgeFront", "fridge_front.png", roughness=0.86),
    "disp_front": make_tex_mat("M_DispFront", "dispenser_front.png", roughness=0.86),
    "micro_front": make_tex_mat("M_MicroFront", "microwave_front.png", roughness=0.86),
    "coffee_front": make_tex_mat("M_CoffeeFront", "coffee_front.png", roughness=0.86),
    "air_purifier": make_tex_mat("M_AirPurifier", "air_purifier.png", roughness=0.86),
    "ac_cassette": make_tex_mat("M_ACCassette", "ac_cassette.png", roughness=0.88),
    "foliage": make_tex_mat("M_Foliage", "foliage_pothos.png", roughness=0.92),
    "plinth_edge": make_tex_mat("M_PlinthEdge", "plinth_edge.png", roughness=0.92),
    "award_plaque": make_tex_mat("M_AwardPlaque", "award_plaque.png", roughness=0.82),
    "cup_milktea": make_tex_mat("M_CupMilkTea", "cup_milktea.png", roughness=0.88),
    "tissue_red": make_tex_mat("M_TissueRed", "tissue_red.png", roughness=0.88),
    "desk_top": make_tex_mat("M_DeskTop", "desk_top.png", roughness=0.88),
    "ceiling_dark": make_tex_mat("M_CeilingDark", "ceiling_dark.png", roughness=0.95),

    # Solid cohesive matte diorama colors
    "white": make_color_mat("M_White", (0.93, 0.93, 0.92)),
    "offwhite": make_color_mat("M_OffWhite", (0.87, 0.86, 0.83)),
    "cream": make_color_mat("M_Cream", (0.90, 0.87, 0.78)),
    "taupe": make_color_mat("M_Taupe", (0.59, 0.52, 0.45)),
    "marble_top": make_color_mat("M_MarbleTop", (0.86, 0.87, 0.88), roughness=0.75),
    "charcoal": make_color_mat("M_Charcoal", (0.16, 0.17, 0.20)),
    "dark_metal": make_color_mat("M_DarkMetal", (0.12, 0.13, 0.16), roughness=0.72),
    "silver": make_color_mat("M_Silver", (0.72, 0.75, 0.78), roughness=0.65),
    "dark_wood": make_color_mat("M_DarkWood", (0.20, 0.13, 0.11)),
    "divider_teal": make_color_mat("M_DividerTeal", (0.58, 0.76, 0.74), roughness=0.78),
    "glass_clear": make_color_mat("M_GlassClear", (0.76, 0.87, 0.94), roughness=0.25, alpha=0.28),
    "led_glow": make_color_mat("M_LedGlow", (0.99, 0.98, 0.95), roughness=0.5, emission=2.4),
    "pot_terracotta": make_color_mat("M_PotTerra", (0.72, 0.42, 0.29)),
    "pot_white": make_color_mat("M_PotWhite", (0.91, 0.90, 0.88)),
    "soil": make_color_mat("M_Soil", (0.24, 0.18, 0.14)),
    "green_mint": make_color_mat("M_GreenMint", (0.54, 0.79, 0.68)),
    "green_leaf": make_color_mat("M_GreenLeaf", (0.26, 0.56, 0.25)),
    "red_bin": make_color_mat("M_RedBin", (0.80, 0.22, 0.24), alpha=0.85),
    "blue_bin": make_color_mat("M_BlueBin", (0.45, 0.70, 0.84)),
    "cardboard": make_color_mat("M_Cardboard", (0.69, 0.54, 0.38)),
    "gold": make_color_mat("M_Gold", (0.85, 0.67, 0.24), roughness=0.65),
    "conf_table": make_color_mat("M_ConfTable", (0.36, 0.38, 0.42)),
    "plinth_top": make_color_mat("M_PlinthTop", (0.76, 0.78, 0.80)),
    "plinth_dark": make_color_mat("M_PlinthDark", (0.36, 0.38, 0.42)),
    "fluffy_beige": make_color_mat("M_FluffyBeige", (0.90, 0.85, 0.76)),

    # Character outfit palette
    "skin": make_color_mat("M_Skin", (0.94, 0.79, 0.67)),
    "hair_dark": make_color_mat("M_HairDark", (0.14, 0.13, 0.14)),
    "hair_brown": make_color_mat("M_HairBrown", (0.30, 0.20, 0.15)),
    "shirt_blue": make_color_mat("M_ShirtBlue", (0.20, 0.39, 0.66)),
    "shirt_pink": make_color_mat("M_ShirtPink", (0.92, 0.74, 0.79)),
    "shirt_black": make_color_mat("M_ShirtBlack", (0.15, 0.16, 0.19)),
    "shirt_navy": make_color_mat("M_ShirtNavy", (0.19, 0.25, 0.38)),
    "shirt_beige": make_color_mat("M_ShirtBeige", (0.82, 0.77, 0.69)),
    "shirt_olive": make_color_mat("M_ShirtOlive", (0.36, 0.47, 0.36)),
    "shirt_grey": make_color_mat("M_ShirtGrey", (0.50, 0.53, 0.57)),
    "pants_dark": make_color_mat("M_PantsDark", (0.18, 0.20, 0.25)),
    "cap_grey": make_color_mat("M_CapGrey", (0.44, 0.47, 0.52)),
    "shoe_white": make_color_mat("M_ShoeWhite", (0.92, 0.92, 0.92)),
    "phone_glow": make_color_mat("M_PhoneGlow", (0.75, 0.88, 1.0), emission=1.1),
    "bag_brown": make_color_mat("M_BagBrown", (0.42, 0.30, 0.23)),
    "bag_navy": make_color_mat("M_BagNavy", (0.22, 0.27, 0.38)),
}


# ---------------------------------------------------------------------------
# 3. Clean BMesh Primitive Builders with Exact Upright UVs
# ---------------------------------------------------------------------------
def _assign_face_uv(face, uv_layer, sx, sy, sz, uv_scale=None, fit_01=False):
    """Assign upright, never-mirrored UVs based on dominant face normal."""
    n = face.normal
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5

    for loop in face.loops:
        co = loop.vert.co
        if ax >= ay and ax >= az:
            # +X face (facing East): viewer looks West -> right is +Y
            # -X face (facing West): viewer looks East -> right is -Y
            u_raw = (co.y + hy) if n.x > 0 else (hy - co.y)
            v_raw = (co.z + hz)
            w_span, h_span = sy, sz
        elif ay >= ax and ay >= az:
            # +Y face (facing North): viewer looks South -> right is -X
            # -Y face (facing South): viewer looks North -> right is +X
            u_raw = (hx - co.x) if n.y > 0 else (co.x + hx)
            v_raw = (co.z + hz)
            w_span, h_span = sx, sz
        else:
            # +Z / -Z top/bottom face: u along +X, v along +Y
            u_raw = (co.x + hx)
            v_raw = (co.y + hy) if n.z > 0 else (hy - co.y)
            w_span, h_span = sx, sy

        if fit_01 or uv_scale is None:
            u = u_raw / max(w_span, 1e-5)
            v = v_raw / max(h_span, 1e-5)
        else:
            u = u_raw / uv_scale
            v = v_raw / uv_scale
        loop[uv_layer].uv = (u, v)


def _match_face(normal, face_key):
    if face_key == '+X':
        return normal.x > 0.7
    if face_key == '-X':
        return normal.x < -0.7
    if face_key == '+Y':
        return normal.y > 0.7
    if face_key == '-Y':
        return normal.y < -0.7
    if face_key == '+Z':
        return normal.z > 0.7
    if face_key == '-Z':
        return normal.z < -0.7
    return False


def make_box(
    name,
    cx,
    cy,
    cz,
    sx,
    sy,
    sz,
    mat,
    group="ArchitectureGroup",
    uv_scale=None,
    face_mats=None,
    rot_z=0.0,
    rot_euler=None,
    parent_obj=None,
):
    """
    Create a centered box at (cx, cy, cz) with dimensions (sx, sy, sz).
    face_mats: optional dict like {'+X': M['fridge_front'], '+Z': M['desk_top']}
    Faces listed in face_mats get exact [0,1]x[0,1] UVs; others use uv_scale (or fit_01 if None).
    """
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((sx, sy, sz, 1.0)))
    bm.faces.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    materials = [mat]
    face_mat_idx = {}
    if face_mats:
        for fk, fmat in face_mats.items():
            if fmat not in materials:
                materials.append(fmat)
            face_mat_idx[fk] = materials.index(fmat)

    for face in bm.faces:
        matched = False
        if face_mats:
            for fk, idx in face_mat_idx.items():
                if _match_face(face.normal, fk):
                    face.material_index = idx
                    _assign_face_uv(face, uv_layer, sx, sy, sz, uv_scale=None, fit_01=True)
                    matched = True
                    break
        if not matched:
            face.material_index = 0
            _assign_face_uv(face, uv_layer, sx, sy, sz, uv_scale=uv_scale, fit_01=(uv_scale is None))

    bm.to_mesh(mesh)
    bm.free()

    for m in materials:
        mesh.materials.append(m)

    obj = bpy.data.objects.new(name, mesh)
    obj.location = (cx, cy, cz)
    if rot_euler is not None:
        obj.rotation_euler = rot_euler
    elif rot_z != 0.0:
        obj.rotation_euler = (0.0, 0.0, rot_z)
    scene.collection.objects.link(obj)
    obj.parent = parent_obj if parent_obj is not None else GROUPS[group]
    return obj


def make_cyl(name, cx, cy, cz, radius, height, mat, segments=10, group="WorkstationsGroup", rot_euler=None, parent_obj=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=height,
    )
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            angle = math.atan2(co.y, co.x)
            u = (angle / (2.0 * math.pi)) + 0.5
            v = (co.z / max(height, 1e-5)) + 0.5
            loop[uv_layer].uv = (u, v)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (cx, cy, cz)
    if rot_euler is not None:
        obj.rotation_euler = rot_euler
    scene.collection.objects.link(obj)
    obj.parent = parent_obj if parent_obj is not None else GROUPS[group]
    return obj


# ---------------------------------------------------------------------------
# 4. Architecture: Diorama Plinth, Marble Floor, Walls, Windows & Rooms
# ---------------------------------------------------------------------------
FLOOR_Z = 0.0
WALL_H = 3.15
CUTAWAY_H = 0.68  # Crisp low cutaway sill on foreground East/South walls for Diorama Mode!

# Overall office coordinates:
# Main floor: X in [0.0, 9.4], Y in [0.0, 23.0]
# Wait: South-West behind pantry (X in [0.0, 2.2], Y in [0.0, 5.2]) is elevator core / exterior cutout -> L-shaped sleek architectural plinth!
# West extensions:
#   - Lobby entry peek behind glass door: X in [-1.8, 0.0], Y in [5.2, 7.2]
#   - North pantry alcove: X in [-0.9, 0.0], Y in [17.4, 19.6]
#   - Wuhan Conference Room: X in [-3.1, 0.0], Y in [19.6, 23.0]


def build_architecture():
    # --- A. Diorama Plinth Base Slab (Clean L-shaped footprint matching the real office!) ---
    # South Bay plinth: X[2.0, 9.7], Y[-0.3, 5.4]
    make_box("Plinth_SouthBay", 5.85, 2.55, -0.24, 7.7, 5.7, 0.46, M["plinth_top"], "ArchitectureGroup",
             face_mats={"+X": M["plinth_edge"], "-X": M["plinth_edge"], "+Y": M["plinth_edge"], "-Y": M["plinth_edge"]})
    # Main Open Office plinth: X[-0.2, 9.7], Y[5.2, 23.3]
    make_box("Plinth_Main", 4.75, 14.25, -0.24, 9.9, 18.1, 0.46, M["plinth_top"], "ArchitectureGroup",
             face_mats={"+X": M["plinth_edge"], "-X": M["plinth_edge"], "+Y": M["plinth_edge"], "-Y": M["plinth_edge"]})
    # Lobby vestibule plinth: X[-2.0, 0.0], Y[5.0, 7.3]
    make_box("Plinth_Lobby", -1.0, 6.15, -0.24, 2.0, 2.3, 0.46, M["plinth_top"], "ArchitectureGroup",
             face_mats={"+X": M["plinth_edge"], "-X": M["plinth_edge"], "+Y": M["plinth_edge"], "-Y": M["plinth_edge"]})
    # Alcove + Wuhan Room plinth: X[-3.3, 0.0], Y[17.3, 23.3]
    make_box("Plinth_Wuhan", -1.65, 20.3, -0.24, 3.3, 6.0, 0.46, M["plinth_top"], "ArchitectureGroup",
             face_mats={"+X": M["plinth_edge"], "-X": M["plinth_edge"], "+Y": M["plinth_edge"], "-Y": M["plinth_edge"]})

    # Polished Grey Marble Floor Tiles (uv_scale = 1.6m for 2x2 tiles -> 0.8m tile size!)
    make_box("Floor_SouthBay", 5.8, 2.7, -0.01, 7.2, 5.4, 0.02, M["floor_marble"], "ArchitectureGroup", uv_scale=1.6)
    make_box("Floor_MainOpen", 4.7, 14.2, -0.01, 9.4, 17.6, 0.02, M["floor_marble"], "ArchitectureGroup", uv_scale=1.6)
    make_box("Floor_LobbyPeek", -0.9, 6.2, -0.01, 1.8, 2.0, 0.02, M["floor_marble"], "ArchitectureGroup", uv_scale=1.6)
    make_box("Floor_Alcove", -0.45, 18.5, -0.01, 0.9, 2.2, 0.02, M["floor_marble"], "ArchitectureGroup", uv_scale=1.6)
    make_box("Floor_WuhanRoom", -1.55, 21.3, -0.01, 3.1, 3.4, 0.02, M["floor_marble"], "ArchitectureGroup", uv_scale=1.6)

    # --- B. South-West Pantry Core Block & Dark Brown "夯爆了" Door (ON WEST WALL beside Fridge!) ---
    # Wall behind pantry & door at X = 2.1, Y in [0.0, 5.45]
    make_box("Wall_PantryBack", 2.1, 2.72, WALL_H * 0.5, 0.20, 5.45, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    # Pantry north return wall returning to X = 0.0 (forming south side of entrance glass door vestibule!)
    make_box("Wall_PantryNorthReturn", 1.1, 5.45, WALL_H * 0.5, 2.2, 0.20, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    # Small white structural wall pillar separating the "夯爆了" door from the fridge niche (Video 1 00:02!)
    make_box("Wall_DoorFridgePillar", 2.30, 1.50, WALL_H * 0.5, 0.22, 0.22, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    # Baseboard along pantry wall
    make_box("Baseboard_Pantry", 2.21, 3.50, 0.05, 0.02, 3.85, 0.10, M["charcoal"], "ArchitectureGroup")

    # Dark mahogany "夯爆了" door on the WEST wall (X = 2.2, Y = 0.80, right next to the cream fridge!)
    make_box("DoorFrame_Hangbaole", 2.22, 0.80, 1.18, 0.12, 1.12, 2.36, M["dark_wood"], "HeroDetailsGroup")
    make_box("Door_Hangbaole", 2.25, 0.80, 1.16, 0.10, 1.02, 2.30, M["dark_wood"], "HeroDetailsGroup",
             face_mats={"+X": M["dark_door"], "-X": M["dark_door"]})
    # Iconic "夯爆了" Red Velvet Pennant hanging on inside (+X) face of the dark door!
    make_box("Pennant_Hangbaole", 2.32, 0.80, 1.56, 0.015, 0.52, 0.78, M["pennant"], "HeroDetailsGroup",
             face_mats={"+X": M["pennant"]})

    # --- C. West Corridor Wall (X = 0.0, Y from 5.3 to 23.0) — Always Facing Isometric Camera! ---
    # 1) Entrance Glass Double Door (Y in [5.4, 7.0]) + Elevator Lobby Peek with Red "福"
    make_box("DoorFrame_MainGlass_Top", 0.0, 6.2, 2.78, 0.18, 1.8, 0.74, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("GlassDoor_MainLeft", 0.0, 5.80, 1.20, 0.05, 0.78, 2.40, M["glass_clear"], "ArchitectureGroup")
    make_box("GlassDoor_MainRight", 0.0, 6.60, 1.20, 0.05, 0.78, 2.40, M["glass_clear"], "ArchitectureGroup")
    # Black aluminum door frames & handles
    for fy in (5.40, 6.20, 7.00):
        make_box(f"GlassDoor_Mullion_{fy:.1f}", 0.0, fy, 1.20, 0.09, 0.06, 2.42, M["charcoal"], "ArchitectureGroup")
    make_box("GlassDoor_MainHead", 0.0, 6.20, 2.40, 0.10, 1.66, 0.07, M["charcoal"], "ArchitectureGroup")
    make_box("GlassDoor_HandleL", 0.04, 6.08, 1.10, 0.04, 0.04, 0.45, M["charcoal"], "ArchitectureGroup")
    make_box("GlassDoor_HandleR", 0.04, 6.32, 1.10, 0.04, 0.04, 0.45, M["charcoal"], "ArchitectureGroup")
    # Glowing Green EXIT Sign above entrance glass door!
    make_box("ExitSign_Main", 0.09, 6.20, 2.62, 0.05, 0.40, 0.18, M["white"], "HeroDetailsGroup",
             face_mats={"+X": M["exit_sign"]})
    # Lobby Backdrop behind glass door with Red "福" diamond!
    make_box("Lobby_BackWall", -1.8, 6.2, WALL_H * 0.5, 0.16, 2.1, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Lobby_SouthWall", -0.9, 5.2, WALL_H * 0.5, 1.8, 0.16, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Lobby_NorthWall", -0.9, 7.1, WALL_H * 0.5, 1.8, 0.16, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Lobby_FuDecal", -1.70, 6.2, 1.65, 0.02, 0.72, 0.72, M["lobby_fu"], "HeroDetailsGroup",
             face_mats={"+X": M["lobby_fu"]})

    # 2) HONOR "25项 软著认证" Wall (Y in [7.0, 10.6])
    make_box("Wall_HonorBase", -0.10, 8.8, WALL_H * 0.5, 0.20, 3.6, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Decal_HonorWall", 0.015, 8.8, 1.62, 0.02, 3.30, 1.65, M["wall_honor"], "HeroDetailsGroup",
             face_mats={"+X": M["wall_honor"]})
    make_box("Baseboard_Honor", 0.01, 8.8, 0.05, 0.02, 3.6, 0.10, M["charcoal"], "ArchitectureGroup")

    # 3) Warm Taupe Wood-Paneled Wall Section (Y in [10.6, 13.4])
    make_box("Wall_WoodPanel", -0.06, 12.0, WALL_H * 0.5, 0.24, 2.8, WALL_H, M["wall_wood"], "ArchitectureGroup", uv_scale=1.2)
    # Row of white light switches on the north edge of wood paneling (Video 2 00:21!)
    make_box("LightSwitch_Panel", 0.075, 13.25, 1.30, 0.02, 0.26, 0.09, M["white"], "HeroDetailsGroup")

    # 4) Company Culture Circular Infographic Wall (Y in [13.4, 16.0])
    make_box("Wall_InfoBase", -0.10, 14.7, WALL_H * 0.5, 0.20, 2.6, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Decal_InfoWall", 0.015, 14.7, 1.62, 0.02, 2.40, 1.25, M["wall_info"], "HeroDetailsGroup",
             face_mats={"+X": M["wall_info"]})
    make_box("Baseboard_Info", 0.01, 14.7, 0.05, 0.02, 2.6, 0.10, M["charcoal"], "ArchitectureGroup")

    # 5) West Mid Glass Double Door (Y in [16.0, 17.5])
    make_box("Wall_MidDoorTop", -0.10, 16.75, 2.78, 0.20, 1.5, 0.74, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Wall_MidDoorBack", -0.65, 16.75, WALL_H * 0.5, 0.14, 1.6, WALL_H, M["offwhite"], "ArchitectureGroup")
    make_box("GlassDoor_Mid", 0.0, 16.75, 1.20, 0.05, 1.44, 2.40, M["glass_clear"], "ArchitectureGroup")
    for fy in (16.02, 16.75, 17.48):
        make_box(f"MidDoor_Frame_{fy:.1f}", 0.0, fy, 1.20, 0.08, 0.05, 2.42, M["charcoal"], "ArchitectureGroup")
    make_box("MidDoor_Head", 0.0, 16.75, 2.40, 0.09, 1.50, 0.06, M["charcoal"], "ArchitectureGroup")

    # 6) North Recessed Tea/Storage Alcove (X in [-0.9, 0.0], Y in [17.5, 19.6])
    make_box("Alcove_BackWall", -0.95, 18.55, WALL_H * 0.5, 0.16, 2.2, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Alcove_SouthWall", -0.45, 17.50, WALL_H * 0.5, 1.0, 0.16, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Alcove_NorthWall", -0.45, 19.60, WALL_H * 0.5, 1.0, 0.16, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    # Alcove lower & upper taupe cabinets
    make_box("Alcove_LowerCab", -0.52, 18.55, 0.42, 0.65, 1.92, 0.84, M["taupe"], "PantryGroup",
             face_mats={"+X": M["cab_taupe"]})
    make_box("Alcove_Counter", -0.50, 18.55, 0.86, 0.70, 1.94, 0.05, M["marble_top"], "PantryGroup")
    make_box("Alcove_UpperCab", -0.64, 18.55, 2.15, 0.42, 1.92, 0.82, M["taupe"], "PantryGroup",
             face_mats={"+X": M["cab_taupe"]})

    # 7) "武汉 WUHAN 会议室" Conference Room (X in [-3.1, 0.0], Y in [19.6, 23.0])
    make_box("Wuhan_WestWall", -3.1, 21.3, WALL_H * 0.5, 0.18, 3.5, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Wuhan_SouthWall", -1.55, 19.6, WALL_H * 0.5, 3.1, 0.18, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("Wuhan_NorthWindow", -1.55, 23.0, WALL_H * 0.5, 3.1, 0.14, WALL_H, M["window_city"], "ArchitectureGroup",
             face_mats={"-Y": M["window_city"], "+Y": M["window_city"]})
    # Glass front wall with Wuhan frosted decal (facing +X into the main corridor!)
    make_box("Wuhan_GlassWall", 0.0, 21.8, 1.48, 0.04, 2.20, 2.96, M["wuhan_glass"], "HeroDetailsGroup",
             face_mats={"+X": M["wuhan_glass"], "-X": M["wuhan_glass"]})
    make_box("Wuhan_GlassDoor", 0.0, 20.15, 1.20, 0.04, 0.95, 2.40, M["glass_clear"], "ArchitectureGroup")
    for fy in (19.65, 20.65, 21.80, 22.95):
        make_box(f"Wuhan_Mullion_{fy:.1f}", 0.0, fy, 1.50, 0.07, 0.05, 3.00, M["charcoal"], "ArchitectureGroup")
    make_box("Wuhan_Header", 0.0, 21.3, 3.02, 0.08, 3.40, 0.10, M["charcoal"], "ArchitectureGroup")
    # Conference Table & 6 Meeting Chairs inside Wuhan Room!
    make_box("Wuhan_TableTop", -1.65, 21.4, 0.74, 1.15, 2.15, 0.06, M["conf_table"], "WorkstationsGroup")
    make_box("Wuhan_TableLeg1", -1.65, 20.7, 0.36, 0.65, 0.10, 0.70, M["charcoal"], "WorkstationsGroup")
    make_box("Wuhan_TableLeg2", -1.65, 22.1, 0.36, 0.65, 0.10, 0.70, M["charcoal"], "WorkstationsGroup")
    for cy in (20.7, 21.4, 22.1):
        build_office_chair(f"Wuhan_ChairW_{cy:.1f}", -2.42, cy, rot_z=-math.pi * 0.5, group="WorkstationsGroup")
        build_office_chair(f"Wuhan_ChairE_{cy:.1f}", -0.88, cy, rot_z=math.pi * 0.5, group="WorkstationsGroup")

    # --- D. North Wall (Y = 23.0, X in [0.0, 9.4]) — Always Visible in Isometric View! ---
    # Structural white columns + tall city windows + vertical blinds!
    north_cols = [0.0, 1.8, 3.6, 5.4, 6.2, 7.8, 9.4]
    for i, cx in enumerate(north_cols):
        make_box(f"North_Col_{i}", cx, 23.0, WALL_H * 0.5, 0.24, 0.24, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    for i in range(len(north_cols) - 1):
        x0, x1 = north_cols[i] + 0.12, north_cols[i + 1] - 0.12
        w = x1 - x0
        if w > 0.3:
            mx = (x0 + x1) * 0.5
            # Low window sill
            make_box(f"North_Sill_{i}", mx, 22.96, 0.22, w, 0.26, 0.44, M["offwhite"], "ArchitectureGroup")
            # Window pane
            make_box(f"North_Glass_{i}", mx, 23.05, 1.78, w, 0.05, 2.68, M["window_city"], "ArchitectureGroup",
                     face_mats={"-Y": M["window_city"], "+Y": M["window_city"]})
            # Grey roller blind at varied heights
            bh = [1.8, 1.9, 1.6, 0.6, 1.7, 1.4][i % 6]
            make_box(f"North_Blind_{i}", mx, 22.95, WALL_H - bh * 0.5, w - 0.06, 0.04, bh, M["blind_grey"], "ArchitectureGroup",
                     face_mats={"-Y": M["blind_grey"]})

    # North-East Glass Private Office Partition (X in [5.9, 7.6], Y in [20.2, 22.8])
    make_box("NE_Office_WestWall", 5.9, 21.4, WALL_H * 0.5, 0.16, 2.8, WALL_H, M["wall_plaster"], "ArchitectureGroup", uv_scale=1.8)
    make_box("NE_Office_SouthGlass", 6.75, 20.0, 1.48, 1.70, 0.04, 2.96, M["glass_clear"], "ArchitectureGroup")
    make_box("NE_Office_EastGlass", 7.60, 21.4, 1.48, 0.04, 2.80, 2.96, M["glass_clear"], "ArchitectureGroup")
    for fx, fy in [(5.9, 20.0), (6.75, 20.0), (7.6, 20.0), (7.6, 21.4), (7.6, 22.8)]:
        make_box(f"NE_Frame_{fx:.1f}_{fy:.1f}", fx, fy, 1.50, 0.06, 0.06, 3.00, M["charcoal"], "ArchitectureGroup")
    make_box("NE_HeaderS", 6.75, 20.0, 3.02, 1.74, 0.08, 0.10, M["charcoal"], "ArchitectureGroup")
    make_box("NE_HeaderE", 7.60, 21.4, 3.02, 0.08, 2.84, 0.10, M["charcoal"], "ArchitectureGroup")
    # Desk inside NE glass office
    make_box("NE_Office_Desk", 6.75, 21.6, 0.73, 1.20, 0.65, 0.04, M["desk_top"], "WorkstationsGroup",
             face_mats={"+Z": M["desk_top"]})
    make_box("NE_Office_LegL", 6.20, 21.6, 0.36, 0.05, 0.60, 0.72, M["white"], "WorkstationsGroup")
    make_box("NE_Office_LegR", 7.30, 21.6, 0.36, 0.05, 0.60, 0.72, M["white"], "WorkstationsGroup")
    build_office_chair("NE_Office_Chair", 6.75, 22.2, rot_z=0.0, group="WorkstationsGroup")

    # Large Black Corner TV Screen + Lounge Chairs (North-East Window Corner, Video 1 00:38-00:39!)
    make_box("CornerTV_Stand", 8.55, 22.25, 0.58, 0.10, 0.10, 1.16, M["charcoal"], "WorkstationsGroup")
    make_box("CornerTV_Base", 8.55, 22.25, 0.03, 0.75, 0.42, 0.05, M["charcoal"], "WorkstationsGroup")
    make_box("CornerTV_Body", 8.55, 22.22, 1.42, 1.48, 0.07, 0.88, M["charcoal"], "WorkstationsGroup",
             face_mats={"-Y": M["screen_tv"]})
    build_office_chair("CornerTV_Chair1", 8.15, 20.75, rot_z=math.pi * 0.85, group="WorkstationsGroup")
    build_office_chair("CornerTV_Chair2", 8.95, 20.75, rot_z=-math.pi * 0.85, group="WorkstationsGroup")

    # --- E. Foreground East & South Curtain Walls (Split into Low Cutaway + CutawayFrontGroup!) ---
    # Low architectural window sill ALWAYS visible (full South curtain wall from X=2.2 to 9.4!)
    make_box("South_LowSill", 5.82, 0.08, 0.22, 7.25, 0.34, 0.44, M["offwhite"], "ArchitectureGroup")
    make_box("East_LowSill", 9.32, 11.5, 0.22, 0.34, 23.1, 0.44, M["offwhite"], "ArchitectureGroup")
    # Short architectural corner column stubs at cutaway height (always visible)
    east_cols = [0.0, 2.8, 5.6, 8.4, 11.2, 14.0, 16.8, 19.6, 23.0]
    for i, cy in enumerate(east_cols):
        make_box(f"East_ColBase_{i}", 9.4, cy, CUTAWAY_H * 0.5, 0.24, 0.24, CUTAWAY_H, M["wall_plaster"], "ArchitectureGroup")
        # Full-height upper column + windows in CutawayFrontGroup (shown in Walk-In Mode!)
        make_box(f"East_ColUpper_{i}", 9.4, cy, CUTAWAY_H + (WALL_H - CUTAWAY_H) * 0.5, 0.24, 0.24, WALL_H - CUTAWAY_H,
                 M["wall_plaster"], "CutawayFrontGroup", uv_scale=1.8)
    for i in range(len(east_cols) - 1):
        y0, y1 = east_cols[i] + 0.12, east_cols[i + 1] - 0.12
        span = y1 - y0
        my = (y0 + y1) * 0.5
        # Low glass edge strip (cute crisp cutaway glass edge in Diorama Mode!)
        make_box(f"East_GlassLow_{i}", 9.42, my, 0.56, 0.04, span, 0.24, M["glass_clear"], "ArchitectureGroup")
        # Upper full-height window pane + grey blind in CutawayFrontGroup
        make_box(f"East_GlassUpper_{i}", 9.42, my, 1.92, 0.05, span, 2.48, M["window_city"], "CutawayFrontGroup",
                 face_mats={"-X": M["window_city"], "+X": M["window_city"]})
        bh = [1.85, 1.45, 1.95, 1.55, 1.80, 1.35, 1.75, 1.65][i % 8]
        make_box(f"East_BlindUpper_{i}", 9.30, my, WALL_H - bh * 0.5, 0.04, span - 0.08, bh, M["blind_grey"], "CutawayFrontGroup",
                 face_mats={"-X": M["blind_grey"]})

    # Full South window curtain wall (X in [2.2, 9.4], Y = 0.0) right up to the "夯爆了" door corner!
    south_cols = [2.20, 4.60, 7.00, 9.40]
    for sx_c in (4.60, 7.00):
        make_box(f"South_ColBase_{sx_c:.1f}", sx_c, 0.0, CUTAWAY_H * 0.5, 0.24, 0.24, CUTAWAY_H, M["wall_plaster"], "ArchitectureGroup")
        make_box(f"South_ColUpper_{sx_c:.1f}", sx_c, 0.0, CUTAWAY_H + (WALL_H - CUTAWAY_H) * 0.5, 0.24, 0.24, WALL_H - CUTAWAY_H,
                 M["wall_plaster"], "CutawayFrontGroup")
    for i in range(len(south_cols) - 1):
        x0, x1 = south_cols[i] + 0.12, south_cols[i + 1] - 0.12
        w = x1 - x0
        mx = (x0 + x1) * 0.5
        make_box(f"South_GlassLow_{i}", mx, -0.02, 0.56, w, 0.04, 0.24, M["glass_clear"], "ArchitectureGroup")
        make_box(f"South_GlassUpper_{i}", mx, -0.02, 1.92, w, 0.05, 2.48, M["window_city"], "CutawayFrontGroup",
                 face_mats={"+Y": M["window_city"], "-Y": M["window_city"]})
        bh = [0.55, 1.75, 1.85][i]  # First pane by the "夯爆了" door has blind raised high just like Video 1 00:00!
        make_box(f"South_BlindUpper_{i}", mx, 0.08, WALL_H - bh * 0.5, w - 0.08, 0.04, bh, M["blind_grey"], "CutawayFrontGroup",
                 face_mats={"+Y": M["blind_grey"]})

    # --- F. Ceiling, Linear LED Lights, Cassette AC Units & Hanging Signs ---
    # Exposed Matte Dark Charcoal Ceiling over open office (X in [2.3, 9.5], Y in [0.0, 23.0])
    make_box("Ceiling_DarkMain", 5.9, 11.5, WALL_H + 0.05, 7.3, 23.2, 0.10, M["ceiling_dark"], "CeilingGroup", uv_scale=2.0)
    # White Dropped Soffit Ceiling over West Corridor, Pantry Vestibule & Wuhan Room
    make_box("Ceiling_WhiteCorridor", 1.15, 14.1, 2.92, 2.5, 18.0, 0.14, M["white"], "CeilingGroup")
    make_box("Ceiling_WhiteWuhan", -1.55, 21.3, 2.92, 3.2, 3.6, 0.14, M["white"], "CeilingGroup")
    make_box("Ceiling_WhiteLobby", -0.90, 6.2, 2.92, 1.9, 2.1, 0.14, M["white"], "CeilingGroup")
    make_box("Ceiling_WhitePantry", 3.2, 2.7, 2.96, 2.2, 5.4, 0.12, M["white"], "CeilingGroup")

    # Bright Linear LED Pendant Light Strips running East-West!
    led_ys = [2.6, 5.2, 7.6, 10.2, 12.8, 15.4, 18.0, 20.8]
    for i, ly in enumerate(led_ys):
        lx_start = 4.4 if ly < 5.5 else 2.8
        lw = 9.0 - lx_start
        make_box(f"LED_Strip_{i}", lx_start + lw * 0.5, ly, 2.92, lw, 0.09, 0.06, M["led_glow"], "CeilingGroup")
    # Recessed corridor downlights
    for i, ly in enumerate(range(6, 23, 2)):
        make_cyl(f"Downlight_{i}", 1.15, float(ly), 2.84, 0.08, 0.02, M["led_glow"], segments=8, group="CeilingGroup")
    # Wuhan room light
    make_box("LED_Wuhan", -1.65, 21.4, 2.83, 0.45, 1.50, 0.04, M["led_glow"], "CeilingGroup")

    # 4-Way White Ceiling Cassette AC Units (吸顶中央空调)
    for i, (ax, ay) in enumerate([(4.2, 8.9), (7.2, 8.9), (4.2, 14.1), (7.2, 14.1), (4.2, 19.3), (7.2, 19.3)]):
        make_box(f"AC_Cassette_{i}", ax, ay, 3.03, 0.88, 0.88, 0.14, M["white"], "CeilingGroup",
                 face_mats={"-Z": M["ac_cassette"]})

    # Suspended Hanging Department Signs ("技术中心", "聘也科技", Promo banners)
    def add_hanging_sign(name, sx, sy, w, h, mat, face_y=True):
        z_top = 3.05
        z_mid = 2.48
        # Hanging wires
        if face_y:
            make_box(name + "_WireL", sx - w * 0.38, sy, (z_top + z_mid + h * 0.5) * 0.5, 0.015, 0.015, z_top - z_mid - h * 0.5, M["silver"], "HangingSignsGroup")
            make_box(name + "_WireR", sx + w * 0.38, sy, (z_top + z_mid + h * 0.5) * 0.5, 0.015, 0.015, z_top - z_mid - h * 0.5, M["silver"], "HangingSignsGroup")
            make_box(name, sx, sy, z_mid, w, 0.03, h, M["white"], "HangingSignsGroup", face_mats={"-Y": mat, "+Y": mat})
        else:
            make_box(name + "_WireL", sx, sy - w * 0.38, (z_top + z_mid + h * 0.5) * 0.5, 0.015, 0.015, z_top - z_mid - h * 0.5, M["silver"], "HangingSignsGroup")
            make_box(name + "_WireR", sx, sy + w * 0.38, (z_top + z_mid + h * 0.5) * 0.5, 0.015, 0.015, z_top - z_mid - h * 0.5, M["silver"], "HangingSignsGroup")
            make_box(name, sx, sy, z_mid, 0.03, w, h, M["white"], "HangingSignsGroup", face_mats={"+X": mat, "-X": mat})

    add_hanging_sign("Sign_JishuCenter", 2.9, 6.8, 0.96, 0.34, M["sign_jishu"], face_y=True)
    add_hanging_sign("Sign_PinyeTech", 3.6, 20.1, 1.04, 0.34, M["sign_pinye"], face_y=True)
    add_hanging_sign("Sign_Promo_1", 5.6, 9.0, 0.86, 0.42, M["sign_promo"], face_y=True)
    add_hanging_sign("Sign_Promo_2", 3.6, 13.8, 0.86, 0.42, M["sign_promo"], face_y=True)
    add_hanging_sign("Sign_Promo_3", 6.2, 16.5, 0.86, 0.42, M["sign_promo"], face_y=True)


# ---------------------------------------------------------------------------
# 5. Reusable Modular Furniture Builders (Chairs, Desks, Plants, Monitors)
# ---------------------------------------------------------------------------
def build_office_chair(name, x, y, rot_z=0.0, group="WorkstationsGroup", has_jacket=False, recline=False):
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0.0)
    root.rotation_euler = (0.0, 0.0, rot_z)
    scene.collection.objects.link(root)
    root.parent = GROUPS[group]

    # 5-star caster base + pneumatic stem
    make_cyl(name + "_Stem", 0, 0, 0.24, 0.035, 0.36, M["charcoal"], segments=8, parent_obj=root)
    for k in range(5):
        ang = k * (2.0 * math.pi / 5.0)
        lx, ly = math.cos(ang) * 0.16, math.sin(ang) * 0.16
        make_box(f"{name}_Leg{k}", lx, ly, 0.07, 0.28, 0.04, 0.035, M["charcoal"], rot_z=ang, parent_obj=root)
        make_cyl(f"{name}_Wheel{k}", lx * 1.65, ly * 1.65, 0.03, 0.025, 0.04, M["dark_metal"], segments=6, parent_obj=root)

    # Seat cushion
    make_box(name + "_Seat", 0, 0, 0.44, 0.48, 0.46, 0.07, M["charcoal"], parent_obj=root)
    # Armrests
    for sx in (-0.25, 0.25):
        make_box(f"{name}_ArmPost_{sx:+.2f}", sx, -0.02, 0.55, 0.04, 0.04, 0.20, M["charcoal"], parent_obj=root)
        make_box(f"{name}_ArmPad_{sx:+.2f}", sx, 0.02, 0.65, 0.06, 0.26, 0.035, M["dark_metal"], parent_obj=root)

    # Mesh Backrest (Right-hand rule around +X: positive angle tilts +Z backward toward -Y!)
    if recline:
        make_box(name + "_Back", 0, -0.34, 0.64, 0.44, 0.06, 0.56, M["charcoal"],
                 rot_euler=(0.72, 0.0, 0.0), parent_obj=root)
        make_box(name + "_Headrest", 0, -0.58, 0.86, 0.26, 0.06, 0.14, M["charcoal"],
                 rot_euler=(0.72, 0.0, 0.0), parent_obj=root)
        # Extended footrest!
        make_box(name + "_FootBar", 0, 0.32, 0.38, 0.10, 0.34, 0.03, M["silver"], parent_obj=root)
        make_box(name + "_FootPad", 0, 0.48, 0.40, 0.36, 0.18, 0.05, M["charcoal"], parent_obj=root)
    else:
        make_box(name + "_Back", 0, -0.23, 0.76, 0.44, 0.05, 0.54, M["charcoal"],
                 rot_euler=(0.12, 0.0, 0.0), parent_obj=root)
        make_box(name + "_Headrest", 0, -0.28, 1.09, 0.24, 0.05, 0.13, M["charcoal"], parent_obj=root)

    if has_jacket:
        # Cozy beige fluffy jacket draped over chair backrest (Video 1 00:33 / Video 2 00:40!)
        make_box(name + "_Jacket", 0, -0.24, 0.78, 0.48, 0.12, 0.44, M["fluffy_beige"], parent_obj=root)
    return root


def build_pothos_plant(name, x, y, z, scale=1.0, group="WorkstationsGroup", white_pot=False):
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, z)
    scene.collection.objects.link(root)
    root.parent = GROUPS[group]

    pm = M["pot_white"] if white_pot else M["pot_terracotta"]
    make_cyl(name + "_Pot", 0, 0, 0.10 * scale, 0.11 * scale, 0.20 * scale, pm, segments=8, parent_obj=root)
    make_cyl(name + "_Soil", 0, 0, 0.195 * scale, 0.095 * scale, 0.02 * scale, M["soil"], segments=8, parent_obj=root)
    # Lush cascading blocky pixel foliage clusters (Image #1 style!)
    clusters = [
        (0.0, 0.0, 0.28, 0.24, 0.24, 0.18, 0.2),
        (0.11, 0.08, 0.25, 0.18, 0.16, 0.15, 0.6),
        (-0.12, 0.06, 0.24, 0.17, 0.18, 0.14, -0.4),
        (0.06, -0.11, 0.23, 0.18, 0.15, 0.14, 0.9),
        (-0.08, -0.10, 0.22, 0.16, 0.16, 0.13, 1.2),
        (0.0, 0.02, 0.37, 0.15, 0.15, 0.12, 0.4),
    ]
    for i, (ox, oy, oz, sx, sy, sz, rz) in enumerate(clusters):
        make_box(f"{name}_Leaf{i}", ox * scale, oy * scale, oz * scale,
                 sx * scale, sy * scale, sz * scale, M["foliage"], rot_z=rz, parent_obj=root)
    return root


def build_tall_corner_plant(name, x, y, z=0.0):
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, z)
    scene.collection.objects.link(root)
    root.parent = GROUPS["WorkstationsGroup"]

    make_cyl(name + "_Pot", 0, 0, 0.22, 0.20, 0.44, M["pot_white"], segments=10, parent_obj=root)
    make_cyl(name + "_Soil", 0, 0, 0.43, 0.18, 0.03, M["soil"], segments=10, parent_obj=root)
    # Tall leafy stems & wide pixel-foliage fronds (Bird of Paradise by the East window!)
    fronds = [
        (0.0, 0.0, 1.05, 0.16, 0.05, 1.15, 0.1, 0.15, 0.0),
        (0.18, 0.12, 1.12, 0.28, 0.04, 0.62, 0.25, 0.35, 0.5),
        (-0.20, 0.14, 1.24, 0.30, 0.04, 0.68, -0.22, 0.30, 1.2),
        (0.16, -0.18, 0.98, 0.26, 0.04, 0.56, 0.35, -0.28, 2.1),
        (-0.16, -0.16, 1.32, 0.28, 0.04, 0.64, -0.30, -0.25, 2.9),
        (0.02, 0.22, 1.46, 0.26, 0.04, 0.54, 0.18, 0.40, 0.8),
        (-0.08, -0.02, 1.56, 0.24, 0.04, 0.50, -0.15, 0.18, 1.8),
    ]
    for i, (ox, oy, oz, sx, sy, sz, rx, ry, rz) in enumerate(fronds):
        make_box(f"{name}_Frond{i}", ox, oy, oz, sx, sy, sz, M["foliage"],
                 rot_euler=(rx, ry, rz), parent_obj=root)
    return root


def build_monitor(name, x, y, z, width=0.52, height=0.32, screen_mat=None, rot_z=0.0, group="WorkstationsGroup", webcam=False):
    if screen_mat is None:
        screen_mat = M["screen_ide"]
    root = bpy.data.objects.new(name, None)
    root.location = (x, y, z)
    root.rotation_euler = (0.0, 0.0, rot_z)
    scene.collection.objects.link(root)
    root.parent = GROUPS[group]

    # Base foot + neck
    make_box(name + "_Base", 0, 0, 0.012, 0.18, 0.14, 0.022, M["charcoal"], parent_obj=root)
    make_box(name + "_Neck", 0, 0.02, 0.11, 0.045, 0.035, 0.19, M["charcoal"], parent_obj=root)
    # Screen panel (faces -Y in local space!)
    make_box(name + "_Panel", 0, 0.0, 0.15 + height * 0.5, width, 0.032, height, M["charcoal"],
             face_mats={"-Y": screen_mat}, parent_obj=root)
    if webcam:
        make_box(name + "_Webcam", 0, -0.01, 0.15 + height + 0.02, 0.07, 0.035, 0.032, M["dark_metal"], parent_obj=root)
    return root


def build_character(name, x, y, rot_z=0.0, shirt_mat=None, hair_mat=None, seated=True, recline=False, has_cap=False, holding_phone=False):
    """Charming stylized low-poly pixel-diorama miniature colleague!"""
    if shirt_mat is None:
        shirt_mat = M["shirt_black"]
    if hair_mat is None:
        hair_mat = M["hair_dark"]

    root = bpy.data.objects.new(name, None)
    root.location = (x, y, 0.0)
    root.rotation_euler = (0.0, 0.0, rot_z)
    scene.collection.objects.link(root)
    root.parent = GROUPS["CharactersGroup"]

    if recline:
        # Reclining colleague kicking back in chair scrolling phone (Video 1 00:06, Video 2 00:01!)
        # Positive X rotation leans torso BACKWARD (-Y) cleanly onto the reclined backrest!
        make_box(name + "_Torso", 0, -0.15, 0.68, 0.34, 0.20, 0.44, shirt_mat, rot_euler=(0.68, 0.0, 0.0), parent_obj=root)
        # Head + grey cap resting on headrest
        make_box(name + "_Head", 0, -0.36, 0.94, 0.21, 0.21, 0.21, M["skin"], rot_euler=(0.30, 0.0, 0.0), parent_obj=root)
        make_box(name + "_Cap", 0, -0.39, 1.03, 0.22, 0.23, 0.09, M["cap_grey"], rot_euler=(0.30, 0.0, 0.0), parent_obj=root)
        make_box(name + "_CapBrim", 0, -0.27, 1.00, 0.20, 0.11, 0.03, M["cap_grey"], rot_euler=(0.30, 0.0, 0.0), parent_obj=root)
        # Legs stretched forward onto footrest!
        for sx in (-0.09, 0.09):
            make_box(f"{name}_Leg_{sx:+.2f}", sx, 0.24, 0.49, 0.13, 0.56, 0.14, M["pants_dark"], rot_euler=(-0.10, 0.0, 0.0), parent_obj=root)
            make_box(f"{name}_Shoe_{sx:+.2f}", sx, 0.54, 0.51, 0.11, 0.16, 0.09, M["shoe_white"], parent_obj=root)
        # Arms raised holding glowing smartphone!
        for sx in (-0.18, 0.18):
            make_box(f"{name}_Arm_{sx:+.2f}", sx, 0.02, 0.80, 0.10, 0.34, 0.10, shirt_mat, rot_euler=(0.32, 0.0, 0.0), parent_obj=root)
        make_box(name + "_Phone", 0, 0.16, 0.90, 0.09, 0.02, 0.15, M["charcoal"],
                 face_mats={"-Y": M["phone_glow"]}, rot_euler=(0.45, 0.0, 0.0), parent_obj=root)
        return root

    if seated:
        # Seated at desk (local +Y = forward toward desk)
        for sx in (-0.09, 0.09):
            make_box(f"{name}_Thigh_{sx:+.2f}", sx, 0.11, 0.50, 0.13, 0.34, 0.12, M["pants_dark"], parent_obj=root)
            make_box(f"{name}_Shin_{sx:+.2f}", sx, 0.24, 0.27, 0.12, 0.12, 0.38, M["pants_dark"], parent_obj=root)
            make_box(f"{name}_Shoe_{sx:+.2f}", sx, 0.28, 0.06, 0.12, 0.18, 0.08, M["shoe_white"], parent_obj=root)
        tilt = 0.22 if holding_phone else -0.06
        make_box(name + "_Torso", 0, -0.02, 0.78, 0.34, 0.20, 0.44, shirt_mat, rot_euler=(tilt, 0.0, 0.0), parent_obj=root)
        hy_off = -0.06 if holding_phone else 0.01
        make_box(name + "_Head", 0, hy_off, 1.12, 0.21, 0.21, 0.21, M["skin"], parent_obj=root)
        make_box(name + "_HairTop", 0, hy_off - 0.01, 1.21, 0.23, 0.23, 0.08, hair_mat, parent_obj=root)
        make_box(name + "_HairBack", 0, hy_off - 0.10, 1.12, 0.22, 0.07, 0.18, hair_mat, parent_obj=root)
        # Cute minimal pixel eyes on front (+Y) face!
        for ex in (-0.045, 0.045):
            make_box(f"{name}_Eye_{ex:+.2f}", ex, hy_off + 0.108, 1.12, 0.028, 0.01, 0.032, M["hair_dark"], parent_obj=root)
        if holding_phone:
            for sx in (-0.19, 0.19):
                make_box(f"{name}_Arm_{sx:+.2f}", sx, 0.10, 0.86, 0.10, 0.30, 0.10, shirt_mat, rot_euler=(0.30, 0.0, 0.0), parent_obj=root)
            make_box(name + "_Phone", 0, 0.24, 0.96, 0.10, 0.02, 0.14, M["charcoal"], face_mats={"-Y": M["phone_glow"]}, parent_obj=root)
        else:
            for sx in (-0.21, 0.21):
                make_box(f"{name}_Arm_{sx:+.2f}", sx, 0.12, 0.78, 0.10, 0.34, 0.10, shirt_mat, rot_euler=(-0.12, 0.0, 0.0), parent_obj=root)
    else:
        # Standing / Walking figure (e.g., two colleagues walking in West corridor from Video 1 00:16!)
        make_box(name + "_LegL", -0.08, 0.05, 0.38, 0.12, 0.13, 0.64, M["pants_dark"], rot_euler=(0.18, 0, 0), parent_obj=root)
        make_box(name + "_LegR", 0.08, -0.05, 0.38, 0.12, 0.13, 0.64, M["pants_dark"], rot_euler=(-0.18, 0, 0), parent_obj=root)
        make_box(name + "_ShoeL", -0.08, 0.12, 0.05, 0.12, 0.18, 0.08, M["shoe_white"], parent_obj=root)
        make_box(name + "_ShoeR", 0.08, -0.06, 0.05, 0.12, 0.18, 0.08, M["shoe_white"], parent_obj=root)
        make_box(name + "_Torso", 0, 0, 0.96, 0.38, 0.24, 0.56, shirt_mat, parent_obj=root)
        make_box(name + "_ArmL", -0.24, -0.04, 0.94, 0.11, 0.12, 0.44, shirt_mat, rot_euler=(-0.18, 0, 0), parent_obj=root)
        make_box(name + "_ArmR", 0.24, 0.04, 0.94, 0.11, 0.12, 0.44, shirt_mat, rot_euler=(0.18, 0, 0), parent_obj=root)
        make_box(name + "_Head", 0, 0, 1.37, 0.21, 0.21, 0.21, M["skin"], parent_obj=root)
        make_box(name + "_HairTop", 0, -0.01, 1.46, 0.23, 0.23, 0.08, hair_mat, parent_obj=root)
        make_box(name + "_HairBack", 0, -0.09, 1.37, 0.22, 0.07, 0.18, hair_mat, parent_obj=root)
        make_box(name + "_Ponytail", 0, -0.15, 1.31, 0.10, 0.10, 0.22, hair_mat, parent_obj=root)
        # Cute pixel eyes on front (+Y) face!
        for ex in (-0.045, 0.045):
            make_box(f"{name}_Eye_{ex:+.2f}", ex, 0.108, 1.37, 0.028, 0.01, 0.032, M["hair_dark"], parent_obj=root)
    return root


# ---------------------------------------------------------------------------
# 6. Build Pantry (South-West Wall X = 2.2 facing +X East, right next to "夯爆了" Door!)
# ---------------------------------------------------------------------------
def build_pantry():
    # Cream Two-Door Retro Mini-Fridge — right next to the "夯爆了" door pillar! (Y = 1.92)
    make_box("Pantry_Fridge", 2.52, 1.92, 0.62, 0.58, 0.56, 1.24, M["cream"], "PantryGroup",
             face_mats={"+X": M["fridge_front"]})

    # Two White Floor-Standing Water Dispensers (Y = 2.46 and Y = 2.86)
    for i, dy in enumerate((2.46, 2.86)):
        make_box(f"Pantry_Dispenser_{i}", 2.46, dy, 0.55, 0.42, 0.36, 1.10, M["white"], "PantryGroup",
                 face_mats={"+X": M["disp_front"]})

    # Long Warm-Taupe Kitchenette Counter (Y in [3.12, 5.32], 3 compact double-door modules)
    for i in range(3):
        cy = 3.49 + i * 0.73
        make_box(f"Pantry_LowerCab_{i}", 2.54, cy, 0.42, 0.62, 0.71, 0.84, M["taupe"], "PantryGroup",
                 face_mats={"+X": M["cab_taupe"]})
        make_box(f"Pantry_UpperCab_{i}", 2.42, cy, 2.08, 0.40, 0.71, 0.86, M["taupe"], "PantryGroup",
                 face_mats={"+X": M["cab_taupe"]})
    # White marble countertop
    make_box("Pantry_Countertop", 2.55, 4.22, 0.865, 0.66, 2.22, 0.05, M["marble_top"], "PantryGroup")

    # Appliances on Countertop (South -> North, matching Video 1 00:03 & Video 2 00:05!)
    make_box("Pantry_Microwave", 2.54, 3.42, 1.04, 0.36, 0.48, 0.30, M["white"], "PantryGroup",
             face_mats={"+X": M["micro_front"]})
    make_box("Pantry_Toaster", 2.52, 3.86, 1.02, 0.28, 0.28, 0.25, M["white"], "PantryGroup")
    make_box("Pantry_ToasterTop", 2.52, 3.86, 1.15, 0.26, 0.26, 0.03, M["charcoal"], "PantryGroup")
    make_box("Pantry_Coffee", 2.52, 4.24, 1.08, 0.32, 0.28, 0.38, M["charcoal"], "PantryGroup",
             face_mats={"+X": M["coffee_front"]})
    make_box("Pantry_SinkRim", 2.54, 4.70, 0.895, 0.40, 0.46, 0.02, M["silver"], "PantryGroup")
    make_box("Pantry_SinkBasin", 2.54, 4.70, 0.885, 0.32, 0.38, 0.02, M["charcoal"], "PantryGroup")
    make_cyl("Pantry_FaucetPost", 2.34, 4.70, 1.03, 0.018, 0.26, M["silver"], segments=8, group="PantryGroup")
    make_box("Pantry_FaucetSpout", 2.42, 4.70, 1.16, 0.16, 0.03, 0.03, M["silver"], "PantryGroup")
    make_box("Pantry_BoxNorth", 2.52, 5.14, 1.01, 0.32, 0.30, 0.24, M["white"], "PantryGroup",
             face_mats={"+X": M["micro_front"]})
    make_cyl("Pantry_GreenBin", 2.95, 5.20, 0.18, 0.15, 0.36, M["green_mint"], segments=10, group="PantryGroup")


# ---------------------------------------------------------------------------
# 7. Build South Bay (4 Sill Monitors right beside "夯爆了" Door, Reclining Colleague, SE Island)
# ---------------------------------------------------------------------------
def build_south_bay():
    # 4 Black Computer Monitors lined up on the South window sill right next to the "夯爆了" door! (Video 1 00:00, Video 2 00:00!)
    for i in range(4):
        mx = 2.68 + i * 0.44
        build_monitor(f"Sill_Monitor_{i}", mx, 0.18, 0.44, width=0.40, height=0.26,
                      screen_mat=M["charcoal"], rot_z=math.pi + (0.08 if i == 3 else -0.04), group="HeroDetailsGroup")

    # Iconic Reclining Colleague in Blue Jacket & Grey Cap right beside the 4 monitors by South Window!
    rx, ry = 4.85, 1.15
    build_office_chair("Chair_Recliner", rx, ry, rot_z=math.pi * 0.62, group="HeroDetailsGroup", recline=True)
    build_character("Char_Recliner", rx, ry, rot_z=math.pi * 0.62, shirt_mat=M["shirt_blue"], recline=True)

    # South-East North-South Double-Sided Workstation Island (X in [6.3, 8.3], Y in [2.2, 5.4])
    # Tabletop
    make_box("SE_Island_Top", 7.3, 3.8, 0.73, 1.56, 3.30, 0.045, M["desk_top"], "WorkstationsGroup", uv_scale=1.1)
    # Central frosted teal divider running N-S
    make_box("SE_Island_Divider", 7.3, 3.8, 0.93, 0.035, 3.28, 0.36, M["divider_teal"], "WorkstationsGroup")
    # Desk legs & white drawer pedestals
    for ly in (2.22, 3.80, 5.38):
        make_box(f"SE_Leg_{ly:.1f}", 7.3, ly, 0.36, 1.48, 0.05, 0.70, M["white"], "WorkstationsGroup")
    for dy in (2.65, 3.75, 4.85):
        make_box(f"SE_DrawerW_{dy:.1f}", 6.72, dy - 0.35, 0.32, 0.42, 0.38, 0.62, M["white"], "WorkstationsGroup",
                 face_mats={"-X": M["cab_white"]})
        make_box(f"SE_DrawerE_{dy:.1f}", 7.88, dy + 0.35, 0.32, 0.42, 0.38, 0.62, M["white"], "WorkstationsGroup",
                 face_mats={"+X": M["cab_white"]})
        # West-facing monitors (sit at X=6.0 facing +X East -> screen faces -X West -> rot_z = -pi/2)
        build_monitor(f"SE_MonW_{dy:.1f}", 7.08, dy, 0.75, screen_mat=M["screen_ide"] if dy != 3.75 else M["screen_chat"],
                      rot_z=-math.pi * 0.5)
        make_box(f"SE_KbW_{dy:.1f}", 6.78, dy, 0.765, 0.16, 0.38, 0.02, M["kb_std"], "WorkstationsGroup",
                 face_mats={"+Z": M["kb_std"]})
        build_office_chair(f"SE_ChairW_{dy:.1f}", 6.08, dy, rot_z=-math.pi * 0.5 + random.uniform(-0.2, 0.2))
        # East-facing monitors
        build_monitor(f"SE_MonE_{dy:.1f}", 7.52, dy, 0.75, screen_mat=M["screen_chat"], rot_z=math.pi * 0.5)
        build_office_chair(f"SE_ChairE_{dy:.1f}", 8.52, dy, rot_z=math.pi * 0.5 + random.uniform(-0.2, 0.2))

    # Black desktop PC tower + scanner on SE island (Video 1 00:08-00:10!)
    make_box("SE_PCTower", 6.82, 5.18, 0.96, 0.22, 0.42, 0.42, M["charcoal"], "WorkstationsGroup")
    make_box("SE_Printer", 6.85, 2.35, 0.88, 0.36, 0.42, 0.24, M["charcoal"], "WorkstationsGroup")
    # Iconic White Xiaomi Air Purifier standing clearly in front of SE island (Video 1 00:05, 00:08!)
    make_box("SE_AirPurifier", 4.95, 3.35, 0.34, 0.28, 0.28, 0.68, M["white"], "HeroDetailsGroup",
             face_mats={"-X": M["air_purifier"], "+X": M["air_purifier"], "-Y": M["air_purifier"]})
    # Tall Leafy Potted Plant in the corner between SE island and East Window (Video 2 00:08!)
    build_tall_corner_plant("SE_TallPlant", 8.75, 5.75, 0.0)


# ---------------------------------------------------------------------------
# 8. Build Main 5 East-West Workstation Rows + White Plant Cabinets + USER'S DESK!
# ---------------------------------------------------------------------------
def build_main_workstations():
    row_ys = [7.6, 10.2, 12.8, 15.4, 18.0]  # 5 double-sided E-W desk banks!
    desk_xs = [3.55, 4.90, 6.25, 7.65]      # 4 workstations per side (total 8 seats per row!)

    # Which seats have seated colleagues (row_idx, side: 'S'|'N', seat_idx, shirt, hair, phone)
    seated_roster = [
        (0, 'N', 1, M["shirt_black"], M["hair_dark"], False),
        (0, 'N', 3, M["shirt_beige"], M["hair_brown"], False),
        (1, 'S', 0, M["shirt_black"], M["hair_dark"], False),   # Guy in black hoodie at seat 0 of user's aisle!
        (1, 'N', 1, M["shirt_pink"], M["hair_dark"], False),
        (1, 'N', 2, M["shirt_grey"], M["hair_dark"], False),
        (0, 'N', 3, M["shirt_navy"], M["hair_dark"], True),     # Colleague across aisle leaning back w/ phone (Video 2 00:53!)
        (2, 'S', 1, M["shirt_navy"], M["hair_dark"], False),
        (2, 'S', 3, M["shirt_olive"], M["hair_dark"], False),
        (2, 'N', 0, M["shirt_black"], M["hair_dark"], False),
        (3, 'S', 0, M["shirt_black"], M["hair_dark"], False),
        (3, 'N', 2, M["shirt_beige"], M["hair_brown"], False),
        (4, 'S', 1, M["shirt_navy"], M["hair_dark"], False),
        (4, 'N', 2, M["shirt_black"], M["hair_dark"], False),
    ]
    seated_map = {(r, s, k): (sh, hr, ph) for (r, s, k, sh, hr, ph) in seated_roster}

    for r_idx, ry in enumerate(row_ys):
        # 1) White Low Storage Cabinet (矮柜) lining the East edge of the West corridor (X = 2.55)
        cab_h = 1.02 if r_idx > 0 else 0.96
        make_box(f"Row{r_idx+1}_WhiteCab", 2.56, ry, cab_h * 0.5, 0.48, 1.56, cab_h, M["white"], "WorkstationsGroup",
                 face_mats={"-X": M["cab_white"], "+X": M["cab_white"]})
        # 3 Lush Potted Pothos Plants on top of each white cabinet! (Super iconic in Video 1 & 2!)
        plant_offsets = [-0.50, 0.0, 0.50] if r_idx != 3 else [-0.50, 0.48]
        for p_i, po in enumerate(plant_offsets):
            build_pothos_plant(f"Row{r_idx+1}_Plant_{p_i}", 2.56, ry + po, cab_h, scale=1.05)
        # On Row 4's white cabinet: Standing Gold Corporate Award Plaque! (Video 1 00:28, Video 2 00:27!)
        if r_idx == 3:
            make_box("Row4_AwardPlaque", 2.54, ry + 0.02, cab_h + 0.22, 0.04, 0.28, 0.38, M["gold"], "HeroDetailsGroup",
                     face_mats={"-X": M["award_plaque"], "+X": M["award_plaque"]}, rot_z=0.18)

        # 2) Double-Sided White Workstation Desk Bank (X from 2.85 to 8.40, depth 1.38m)
        make_box(f"Row{r_idx+1}_DeskTop", 5.62, ry, 0.73, 5.56, 1.38, 0.045, M["desk_top"], "WorkstationsGroup", uv_scale=1.35)
        # Central frosted mint-teal acrylic divider
        make_box(f"Row{r_idx+1}_Divider", 5.62, ry, 0.93, 5.52, 0.032, 0.36, M["divider_teal"], "WorkstationsGroup")
        # Desk structural legs
        for lx in (2.92, 4.25, 5.62, 6.95, 8.32):
            make_box(f"Row{r_idx+1}_Leg_{lx:.1f}", lx, ry, 0.36, 0.05, 1.30, 0.70, M["white"], "WorkstationsGroup")

        # 3) Populate all 4 seats on South side (-Y, facing North +Y) and North side (+Y, facing South -Y)
        for s_idx, dx in enumerate(desk_xs):
            for side in ('S', 'N'):
                is_user_desk = (r_idx == 1 and side == 'S' and s_idx == 3)  # ROW 2 SOUTH-FACING WINDOW SEAT!
                # Drawer pedestal under desk
                ped_y = ry - 0.42 if side == 'S' else ry + 0.42
                ped_face = "-Y" if side == 'S' else "+Y"
                make_box(f"Row{r_idx+1}_{side}{s_idx}_Ped", dx - 0.44, ped_y, 0.32, 0.40, 0.44, 0.62, M["white"],
                         "UserDeskGroup" if is_user_desk else "WorkstationsGroup", face_mats={ped_face: M["cab_white"]})

                chair_y = ry - 0.86 if side == 'S' else ry + 0.86
                chair_rot = 0.0 if side == 'S' else math.pi  # Local +Y = toward desk!

                if is_user_desk:
                    build_user_desk(dx, ry, chair_y)
                    continue

                # Standard colleague desk setup (dual or single monitors, keyboard, mouse, clutter)
                mon_y = ry - 0.22 if side == 'S' else ry + 0.22
                mon_rot = 0.0 if side == 'S' else math.pi
                dual = ((r_idx + s_idx) % 2 == 0)
                if dual:
                    build_monitor(f"R{r_idx+1}_{side}{s_idx}_MonL", dx - 0.26, mon_y, 0.75, width=0.48, height=0.30,
                                  screen_mat=M["screen_ide"], rot_z=mon_rot + (0.08 if side == 'S' else -0.08))
                    build_monitor(f"R{r_idx+1}_{side}{s_idx}_MonR", dx + 0.24, mon_y, 0.75, width=0.44, height=0.28,
                                  screen_mat=M["screen_chat"], rot_z=mon_rot - (0.08 if side == 'S' else -0.08))
                else:
                    build_monitor(f"R{r_idx+1}_{side}{s_idx}_Mon", dx, mon_y, 0.75, width=0.52, height=0.32,
                                  screen_mat=M["screen_ide"] if (s_idx % 2 == 0) else M["screen_chat"], rot_z=mon_rot)

                # Keyboard & mouse
                kb_y = ry - 0.48 if side == 'S' else ry + 0.48
                make_box(f"R{r_idx+1}_{side}{s_idx}_Kb", dx - 0.04, kb_y, 0.765, 0.36, 0.14, 0.02, M["kb_std"],
                         "WorkstationsGroup", face_mats={"+Z": M["kb_std"]})
                make_box(f"R{r_idx+1}_{side}{s_idx}_Mouse", dx + 0.24, kb_y, 0.765, 0.07, 0.11, 0.025, M["charcoal"], "WorkstationsGroup")

                # Small authentic desk props (mugs, notebooks, blue trash basket, backpack)
                if (r_idx + s_idx) % 3 == 0:
                    mug_y = ry - 0.44 if side == 'S' else ry + 0.44
                    make_cyl(f"R{r_idx+1}_{side}{s_idx}_Mug", dx + 0.42, mug_y, 0.80, 0.042, 0.095,
                             M["offwhite"] if s_idx % 2 == 0 else M["blue_bin"], segments=8)
                if r_idx == 1 and side == 'S' and s_idx == 0:
                    # Blue mesh trash basket seen in Video 2 00:51!
                    make_cyl("Aisle_BlueTrashBin", dx - 0.62, ry - 0.72, 0.16, 0.13, 0.32, M["blue_bin"], segments=8)
                if r_idx == 1 and side == 'S' and s_idx == 1:
                    # Brown backpack sitting on desk (Video 2 00:52!)
                    make_box("Aisle_Backpack", dx - 0.34, ry - 0.44, 0.92, 0.30, 0.20, 0.34, M["bag_brown"], "WorkstationsGroup", rot_z=0.3)

                # Chair (+ beige fluffy jacket on Row 5's corridor seat like Video 1 00:33 / Video 2 00:40!)
                has_jacket = (r_idx == 4 and side == 'S' and s_idx == 0)
                build_office_chair(f"R{r_idx+1}_{side}{s_idx}_Chair", dx, chair_y,
                                   rot_z=chair_rot + random.uniform(-0.18, 0.18), has_jacket=has_jacket)

                # Seated Colleague if in roster
                if (r_idx, side, s_idx) in seated_map:
                    sh, hr, ph = seated_map[(r_idx, side, s_idx)]
                    build_character(f"Char_R{r_idx+1}_{side}{s_idx}", dx, chair_y, rot_z=chair_rot,
                                    shirt_mat=sh, hair_mat=hr, seated=True, holding_phone=ph)

    # Two walking colleagues in the West Corridor (Pink & Black puffer jackets, Video 1 00:16-00:19!)
    build_character("Char_WalkPink", 0.95, 11.4, rot_z=0.12, shirt_mat=M["shirt_pink"], hair_mat=M["hair_dark"], seated=False)
    build_character("Char_WalkBlack", 1.52, 12.0, rot_z=-0.10, shirt_mat=M["shirt_black"], hair_mat=M["hair_dark"], seated=False)


def build_user_desk(dx, ry, chair_y):
    """
    THE USER'S OWN DESK (Video 2 00:55-00:56) — Extra love & faithful pixel-art micro-details!
    Located at Row 2 South-facing East-window seat (X=7.65, Y=10.2, facing +Y North).
    """
    g = "UserDeskGroup"
    # 1) Large Left Monitor (warm editor UI) + Medium Right Monitor (peach card UI + webcam!)
    build_monitor("User_MonitorLeft", dx - 0.28, ry - 0.22, 0.75, width=0.58, height=0.35,
                  screen_mat=M["screen_user_l"], rot_z=0.06, group=g)
    build_monitor("User_MonitorRight", dx + 0.30, ry - 0.24, 0.75, width=0.46, height=0.29,
                  screen_mat=M["screen_user_r"], rot_z=-0.16, group=g, webcam=True)

    # 2) Crisp White/Black 75% Mechanical Keyboard + Black Coiled Aviator Cable!
    make_box("User_Keyboard", dx + 0.02, ry - 0.50, 0.768, 0.34, 0.145, 0.028, M["white"], g,
             face_mats={"+Z": M["kb_user"]}, rot_z=0.04)
    # Coiled cable running from keyboard back-left toward monitor!
    for c_i in range(6):
        make_cyl(f"User_Coil_{c_i}", dx - 0.14 - c_i * 0.022, ry - 0.38, 0.768, 0.014, 0.016, M["charcoal"],
                 segments=6, group=g, rot_euler=(0.0, math.pi * 0.5, 0.0))
    make_box("User_CableTail", dx - 0.08, ry - 0.41, 0.762, 0.12, 0.014, 0.012, M["charcoal"], g)

    # 3) Dark Mousepad + White Wireless Mouse
    make_box("User_Mousepad", dx + 0.32, ry - 0.49, 0.756, 0.24, 0.20, 0.008, M["charcoal"], g)
    make_box("User_Mouse", dx + 0.32, ry - 0.50, 0.774, 0.068, 0.115, 0.030, M["white"], g)

    # 4) Tall Takeaway Coffee / Milk-Tea Cup (White/Yellow/Red + Black Lid!) + Ceramic Mug
    make_cyl("User_MilkTeaCup", dx - 0.34, ry - 0.50, 0.835, 0.044, 0.16, M["cup_milktea"], segments=10, group=g)
    make_cyl("User_MilkTeaLid", dx - 0.34, ry - 0.50, 0.922, 0.048, 0.02, M["charcoal"], segments=10, group=g)
    make_cyl("User_CeramicMug", dx - 0.46, ry - 0.44, 0.80, 0.045, 0.095, M["offwhite"], segments=8, group=g)

    # 5) Red Tissue Box + Small Red/Green Stacked Boxes on right side (Video 2 00:56!)
    make_box("User_RedTissue", dx + 0.18, ry - 0.34, 0.795, 0.19, 0.11, 0.085, M["tissue_red"], g,
             face_mats={"+Z": M["tissue_red"], "-Y": M["tissue_red"]}, rot_z=-0.12)
    make_box("User_GreenBox", dx + 0.52, ry - 0.36, 0.795, 0.14, 0.12, 0.08, M["green_leaf"], g, rot_z=0.15)
    make_box("User_RedBox", dx + 0.50, ry - 0.48, 0.785, 0.15, 0.10, 0.06, M["tissue_red"], g, rot_z=-0.10)

    # 6) Red Translucent Trash Bin under desk + Cardboard Box against East Window Wall!
    make_cyl("User_RedTrashBin", dx + 0.56, ry - 0.86, 0.16, 0.125, 0.32, M["red_bin"], segments=10, group=g)
    make_box("User_CardboardBox", 8.88, ry - 0.42, 0.16, 0.38, 0.34, 0.32, M["cardboard"], g, rot_z=0.06)

    # 7) User's Ergonomic Mesh Chair — welcomingly slightly angled out!
    build_office_chair("User_Chair", dx + 0.06, chair_y - 0.06, rot_z=-0.38, group=g)


# ---------------------------------------------------------------------------
# 9. North End "聘也科技" 2x2 Desk Cluster
# ---------------------------------------------------------------------------
def build_north_zone():
    # Compact 2x2 white desk bank under "聘也科技" sign (X in [2.6, 5.2], Y = 21.1)
    make_box("North_DeskTop", 3.9, 21.1, 0.73, 2.55, 1.32, 0.045, M["desk_top"], "WorkstationsGroup", uv_scale=1.2)
    make_box("North_Divider", 3.9, 21.1, 0.93, 2.52, 0.032, 0.36, M["divider_teal"], "WorkstationsGroup")
    for lx in (2.70, 3.90, 5.10):
        make_box(f"North_Leg_{lx:.1f}", lx, 21.1, 0.36, 0.05, 1.24, 0.70, M["white"], "WorkstationsGroup")
    for dx in (3.28, 4.52):
        # South side
        build_monitor(f"North_MonS_{dx:.1f}", dx, 20.88, 0.75, screen_mat=M["screen_ide"], rot_z=0.0)
        build_office_chair(f"North_ChairS_{dx:.1f}", dx, 20.15, rot_z=0.1)
        # North side
        build_monitor(f"North_MonN_{dx:.1f}", dx, 21.32, 0.75, screen_mat=M["screen_chat"], rot_z=math.pi)
        build_office_chair(f"North_ChairN_{dx:.1f}", dx, 22.05, rot_z=math.pi - 0.1)
    build_character("Char_North1", 3.28, 20.15, rot_z=0.0, shirt_mat=M["shirt_black"], seated=True)
    build_character("Char_North2", 4.52, 22.05, rot_z=math.pi, shirt_mat=M["shirt_beige"], seated=True)


# ---------------------------------------------------------------------------
# 10. Build Everything, Pack, Save .blend, Export .glb, Render Previews!
# ---------------------------------------------------------------------------
def setup_lighting_and_world():
    world = bpy.data.worlds.new("DioramaWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.96, 0.965, 0.975, 1.0)
        bg.inputs["Strength"].default_value = 0.85

    # Warm soft sun key light (angled from South-East like Image #1!)
    sun_data = bpy.data.lights.new("Sun_Key", type='SUN')
    sun_data.energy = 2.6
    sun_data.color = (1.0, 0.97, 0.92)
    sun_data.angle = math.radians(6.0)
    sun_obj = bpy.data.objects.new("Sun_Key", sun_data)
    sun_obj.rotation_euler = (math.radians(48), math.radians(15), math.radians(-38))
    scene.collection.objects.link(sun_obj)

    # Soft cool fill sun from opposite direction
    fill_data = bpy.data.lights.new("Sun_Fill", type='SUN')
    fill_data.energy = 0.65
    fill_data.color = (0.86, 0.92, 1.0)
    fill_obj = bpy.data.objects.new("Sun_Fill", fill_data)
    fill_obj.rotation_euler = (math.radians(55), math.radians(-10), math.radians(145))
    scene.collection.objects.link(fill_obj)


def set_group_visible(group_name, visible):
    parent = GROUPS[group_name]
    parent.hide_render = not visible
    parent.hide_viewport = not visible
    for obj in bpy.data.objects:
        p = obj.parent
        while p is not None:
            if p == parent:
                obj.hide_render = not visible
                obj.hide_viewport = not visible
                break
            p = p.parent


def render_previews():
    # Use EEVEE for fast crisp preview renders with Freestyle ink outlines!
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else ('BLENDER_EEVEE' if 'BLENDER_EEVEE' in engines else 'CYCLES')
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 860
    scene.render.image_settings.file_format = 'PNG'
    if hasattr(scene, "view_settings"):
        scene.view_settings.view_transform = 'Standard'

    # Enable Freestyle crisp ink outlines for Blender preview renders (just like Image #1!)
    scene.render.use_freestyle = True
    vl = scene.view_layers[0]
    if vl.freestyle_settings.linesets:
        ls = vl.freestyle_settings.linesets[0]
    else:
        ls = vl.freestyle_settings.linesets.new("DioramaInk")
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new("DioramaInkStyle")
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.linestyle.color = (0.16, 0.17, 0.21)
    ls.linestyle.thickness = 1.1

    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_obj = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    def aim_camera(pos, target, ortho=False, ortho_scale=22.0, lens=28.0):
        cam_obj.location = Vector(pos)
        direction = Vector(target) - Vector(pos)
        cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        cam_data.type = 'ORTHO' if ortho else 'PERSP'
        cam_data.ortho_scale = ortho_scale
        cam_data.lens = lens
        cam_data.clip_start = 0.05
        cam_data.clip_end = 200.0

    # 1) Isometric Diorama Preview (Ceiling & Front Cutaway hidden!)
    set_group_visible("CeilingGroup", False)
    set_group_visible("CutawayFrontGroup", False)
    set_group_visible("HangingSignsGroup", False)
    aim_camera((24.0, -7.0, 19.5), (3.6, 11.2, 0.6), ortho=True, ortho_scale=24.5)
    scene.render.filepath = os.path.join(RENDER_DIR, "iso_diorama.png")
    bpy.ops.render.render(write_still=True)

    # 2) Close-up of User's Desk + HONOR Wall + Pantry (Isometric Zoom!)
    aim_camera((16.5, -1.5, 9.0), (5.2, 7.2, 0.8), ortho=True, ortho_scale=11.5)
    scene.render.filepath = os.path.join(RENDER_DIR, "iso_closeup_user_pantry.png")
    bpy.ops.render.render(write_still=True)

    # 3) First-Person Interior Walk-in View (Corridor looking North with Ceiling & Windows ON!)
    set_group_visible("CeilingGroup", True)
    set_group_visible("CutawayFrontGroup", True)
    set_group_visible("HangingSignsGroup", True)
    aim_camera((1.25, 7.2, 1.58), (2.2, 18.0, 1.45), ortho=False, lens=24.0)
    scene.render.filepath = os.path.join(RENDER_DIR, "walkin_corridor.png")
    bpy.ops.render.render(write_still=True)

    # 4) Close-up of South Bay ("夯爆了" Door on West Wall right next to Fridge + Recliner!)
    aim_camera((5.5, 3.8, 1.58), (2.4, 1.2, 1.25), ortho=False, lens=24.0)
    scene.render.filepath = os.path.join(RENDER_DIR, "walkin_south_hangbaole.png")
    bpy.ops.render.render(write_still=True)

    # Restore everything visible for .blend & .glb export!
    set_group_visible("CeilingGroup", True)
    set_group_visible("CutawayFrontGroup", True)
    set_group_visible("HangingSignsGroup", True)
    # Remove preview camera so user gets a clean scene + isometric camera
    aim_camera((24.0, -7.0, 19.5), (3.6, 11.2, 0.6), ortho=True, ortho_scale=24.5)


if __name__ == "__main__":
    build_architecture()
    build_pantry()
    build_south_bay()
    build_main_workstations()
    build_north_zone()
    setup_lighting_and_world()

    # Pack all pixel-art textures into the .blend file
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print(f"Saved Blender file: {BLEND_OUT}")

    # Export clean GLB with all textures embedded for Three.js web viewer!
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        export_format='GLB',
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )
    print(f"Exported Web GLB: {GLB_OUT} ({os.path.getsize(GLB_OUT) / 1024:.1f} KB)")

    # Render visual verification PNGs from Blender!
    render_previews()
    print("Done rendering Blender verification previews!")
