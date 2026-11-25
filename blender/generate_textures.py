#!/usr/bin/env python3
"""
Generate crisp pixel-art textures for the Office Isometric Diorama.
Matches the Japanese retro low-poly + nearest-neighbor pixel-art diorama style.
"""
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "/Users/wangwei/Desktop/demo/gemini-3d/blender/textures"
os.makedirs(OUT_DIR, exist_ok=True)

random.seed(42)

# Find best available Chinese font
FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)


def get_font(size):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_crisp_text(img, pos, text, size, fill, anchor="lt", bold_offset=False, threshold=100):
    """Draw text sharply without soft anti-aliasing by thresholding alpha."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    font = get_font(size)
    md.text(pos, text, fill=255, font=font, anchor=anchor)
    if bold_offset:
        md.text((pos[0] + 1, pos[1]), text, fill=255, font=font, anchor=anchor)
    # Threshold to hard crisp pixel edges
    mask = mask.point(lambda p: 255 if p >= threshold else 0)
    color_layer = Image.new(img.mode, (w, h), fill)
    img.paste(color_layer, (0, 0), mask)


def save(img, name):
    path = os.path.join(OUT_DIR, name)
    img.save(path)
    return path


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))


def jitter_color(rgb, amt=6):
    d = random.randint(-amt, amt)
    return (clamp(rgb[0] + d), clamp(rgb[1] + d), clamp(rgb[2] + d))


# 1. Floor marble tile (64x64 seamless, 2x2 tiles)
def gen_floor_marble():
    img = Image.new("RGB", (64, 64), (194, 198, 203))
    px = img.load()
    tile_tones = [(194, 198, 204), (190, 194, 200), (197, 201, 206), (188, 193, 199)]
    for y in range(64):
        for x in range(64):
            ti = (x // 32) + (y // 32) * 2
            base = tile_tones[ti]
            # Subtle marble diagonal wave
            v = math.sin((x * 0.22 + y * 0.14) + ti * 1.7) + 0.5 * math.sin(x * 0.09 - y * 0.25)
            delta = 0
            if v > 0.95:
                delta = 10
            elif v < -0.9:
                delta = -10
            elif (x + y * 3) % 11 == 0:
                delta = -4
            # Crisp tile grout lines
            if x % 32 == 0 or y % 32 == 0:
                px[x, y] = (164, 168, 175)
            elif x % 32 == 1 or y % 32 == 1:
                px[x, y] = (206, 210, 215)
            else:
                px[x, y] = (clamp(base[0] + delta), clamp(base[1] + delta), clamp(base[2] + delta))
    save(img, "floor_marble.png")


# 2. Architectural cream-white wall with subtle panel/tile texture (like Image #1!)
def gen_wall_plaster():
    img = Image.new("RGB", (64, 64), (242, 239, 233))
    px = img.load()
    for y in range(64):
        for x in range(64):
            base = (242, 239, 233)
            if x % 32 == 0:
                px[x, y] = (224, 220, 213)
            elif y % 16 == 0 and (x % 2 == 0):
                px[x, y] = (234, 231, 224)
            else:
                d = random.choice([-3, -1, 0, 0, 0, 2])
                px[x, y] = (clamp(base[0] + d), clamp(base[1] + d), clamp(base[2] + d))
    save(img, "wall_plaster.png")


# 3. Warm taupe vertical-grooved wood paneling
def gen_wall_wood_panel():
    img = Image.new("RGB", (64, 64), (164, 150, 134))
    px = img.load()
    for y in range(64):
        for x in range(64):
            if x % 16 == 0:
                px[x, y] = (114, 102, 89)
            elif x % 16 == 1:
                px[x, y] = (179, 165, 149)
            else:
                grain = int(4 * math.sin(y * 0.25 + (x % 16) * 0.9))
                d = random.choice([-2, 0, 0, 2]) + grain
                px[x, y] = (clamp(164 + d), clamp(150 + d), clamp(134 + d))
    save(img, "wall_wood_panel.png")


# 4. Taupe pantry cabinet doors
def gen_cabinet_taupe():
    img = Image.new("RGB", (64, 64), (168, 153, 137))
    d = ImageDraw.Draw(img)
    px = img.load()
    for y in range(64):
        for x in range(64):
            g = int(3 * math.sin(y * 0.35 + x * 0.1))
            px[x, y] = (clamp(168 + g), clamp(153 + g), clamp(137 + g))
    # Two cabinet doors
    d.rectangle([0, 0, 63, 63], outline=(112, 99, 86))
    d.line([32, 0, 32, 63], fill=(102, 90, 78))
    d.line([31, 1, 31, 62], fill=(182, 167, 152))
    d.line([33, 1, 33, 62], fill=(182, 167, 152))
    # Black modern handles near bottom/center seam
    d.rectangle([26, 44, 28, 56], fill=(42, 42, 48))
    d.rectangle([36, 44, 38, 56], fill=(42, 42, 48))
    save(img, "cabinet_taupe.png")


# 5. White low cabinet front
def gen_cabinet_white():
    img = Image.new("RGB", (64, 64), (244, 245, 247))
    d = ImageDraw.Draw(img)
    # Horizontal panel seams (3 subtle horizontal bands like the video!)
    d.rectangle([0, 0, 63, 63], outline=(206, 210, 216))
    for y in (21, 42):
        d.line([1, y, 62, y], fill=(214, 218, 224))
        d.line([1, y + 1, 62, y + 1], fill=(252, 253, 255))
    d.line([32, 1, 32, 62], fill=(224, 227, 232))
    save(img, "cabinet_white.png")


# 6. Dark mahogany molded security door
def gen_dark_door():
    img = Image.new("RGB", (48, 96), (62, 42, 39))
    d = ImageDraw.Draw(img)
    # Outer frame
    d.rectangle([0, 0, 47, 95], outline=(38, 24, 22), width=2)
    d.rectangle([2, 2, 45, 93], outline=(82, 58, 53))
    # 3 recessed classic molded panels (top tall, middle small, bottom tall)
    panels = [(8, 8, 39, 36), (8, 41, 39, 55), (8, 60, 39, 87)]
    for x0, y0, x1, y1 in panels:
        d.rectangle([x0, y0, x1, y1], fill=(54, 36, 33), outline=(36, 22, 20))
        d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=(66, 45, 42), outline=(88, 62, 57))
        d.line([x0 + 2, y1 - 2, x1 - 2, y1 - 2], fill=(40, 25, 23))
        d.line([x1 - 2, y0 + 2, x1 - 2, y1 - 2], fill=(40, 25, 23))
    # Black smart handle lock on right
    d.rectangle([38, 46, 44, 62], fill=(26, 27, 32), outline=(14, 14, 18))
    d.rectangle([36, 52, 43, 54], fill=(48, 50, 58))
    d.point((41, 49), fill=(110, 200, 255))
    save(img, "dark_door.png")


# 7. Iconic "夯爆了" Red Velvet Pennant Flag (RGBA with gold fringe!)
def gen_pennant_hangbaole():
    w, h = 96, 144
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Hanging golden string + top rod
    d.line([48, 2, 16, 12], fill=(232, 190, 62, 255), width=2)
    d.line([48, 2, 80, 12], fill=(232, 190, 62, 255), width=2)
    d.rectangle([6, 12, 90, 17], fill=(215, 166, 52, 255), outline=(142, 98, 24, 255))
    d.rectangle([4, 11, 8, 18], fill=(242, 202, 78, 255))
    d.rectangle([88, 11, 92, 18], fill=(242, 202, 78, 255))

    # Main crimson pennant polygon (rectangular top + V-shaped bottom point)
    poly = [(12, 18), (84, 18), (84, 108), (48, 134), (12, 108)]
    d.polygon(poly, fill=(178, 24, 28, 255))

    # Subtle fabric pixel shading folds
    px = img.load()
    for y in range(18, 134):
        for x in range(12, 85):
            if px[x, y][3] > 0:
                if x < 18 or x > 78:
                    px[x, y] = (150, 18, 22, 255)
                elif (x + y) % 9 == 0:
                    px[x, y] = (165, 20, 25, 255)

    # Golden yellow trim & hanging fringe tassels along bottom V-edge
    d.line([(12, 18), (12, 108), (48, 134), (84, 108), (84, 18)], fill=(240, 192, 44, 255), width=3)
    d.line([(16, 21), (80, 21)], fill=(232, 184, 42, 255))
    for x in range(12, 85, 3):
        t = abs(x - 48) / 36.0
        y_edge = int(134 - t * 26)
        fringe_len = 8 if (x % 6 == 0) else 6
        col = (244, 198, 52, 255) if (x % 6 == 0) else (218, 166, 36, 255)
        d.line([(x, y_edge + 1), (x, min(h - 1, y_edge + fringe_len))], fill=col, width=2)

    # Bold golden vertical Chinese text: "夯爆了"
    draw_crisp_text(img, (48, 38), "夯", 24, (252, 218, 72, 255), anchor="mm", bold_offset=True)
    draw_crisp_text(img, (48, 67), "爆", 24, (252, 218, 72, 255), anchor="mm", bold_offset=True)
    draw_crisp_text(img, (48, 96), "了", 24, (252, 218, 72, 255), anchor="mm", bold_offset=True)

    # Tiny vertical side inscription dots (authentic Chinese pennant detail)
    for y in range(28, 50, 4):
        d.rectangle([71, y, 73, y + 2], fill=(238, 196, 72, 255))
    for y in range(74, 102, 4):
        d.rectangle([22, y, 24, y + 2], fill=(238, 196, 72, 255))

    save(img, "pennant_hangbaole.png")


# 8. "25项 软著认证 HONOR" Wall + 5x4 framed certificates grid
def gen_wall_honor():
    w, h = 384, 192
    img = Image.new("RGB", (w, h), (244, 243, 240))
    d = ImageDraw.Draw(img)
    px = img.load()
    for y in range(h):
        for x in range(w):
            if (x * 7 + y * 13) % 31 == 0:
                px[x, y] = (236, 235, 230)

    # Left side typography (crisp, clearly readable pixel text)
    draw_crisp_text(img, (22, 26), "25项", 34, (54, 60, 72), anchor="lt", bold_offset=True)
    draw_crisp_text(img, (24, 66), "软著认证", 20, (82, 88, 100), anchor="lt", threshold=85)
    draw_crisp_text(img, (20, 92), "HONOR", 40, (32, 94, 188), anchor="lt", bold_offset=True)
    draw_crisp_text(img, (22, 140), "浙江省创新型中小企业", 13, (88, 94, 108), anchor="lt", threshold=80)
    draw_crisp_text(img, (22, 160), "浙江省专精特新中小企业", 13, (88, 94, 108), anchor="lt", threshold=80)

    # Right side: 5 columns x 4 rows of framed certificate plaques!
    start_x, start_y = 186, 20
    cw, ch = 30, 34
    gx, gy = 7, 6
    palette_inner = [(216, 234, 246), (244, 236, 210), (220, 238, 226), (224, 232, 248)]
    for row in range(4):
        for col in range(5):
            x0 = start_x + col * (cw + gx)
            y0 = start_y + row * (ch + gy)
            inner = palette_inner[(row + col) % len(palette_inner)]
            d.rectangle([x0 + 2, y0 + 2, x0 + cw + 2, y0 + ch + 2], fill=(212, 214, 218))
            d.rectangle([x0, y0, x0 + cw, y0 + ch], fill=(252, 252, 254), outline=(168, 176, 188), width=2)
            d.rectangle([x0 + 3, y0 + 3, x0 + cw - 3, y0 + ch - 3], fill=inner)
            d.rectangle([x0 + 7, y0 + 7, x0 + cw - 7, y0 + 9], fill=(78, 114, 162))
            for ly in (14, 18, 22):
                d.line([x0 + 6, y0 + ly, x0 + cw - 6, y0 + ly], fill=(138, 150, 166))
            d.rectangle([x0 + cw - 10, y0 + ch - 10, x0 + cw - 6, y0 + ch - 6], fill=(208, 66, 62))

    save(img, "wall_honor.png")


# 9. Company Culture Circular Infographic Wall ("HRIS SaaS", "灵活用工", etc.)
def gen_wall_infographic():
    w, h = 384, 192
    img = Image.new("RGB", (w, h), (244, 244, 242))
    d = ImageDraw.Draw(img)

    center = (192, 96)
    nodes = [
        (82, 52, 34, (74, 166, 98), "智能调度"),
        (72, 138, 34, (56, 126, 196), "灵活用工"),
        (192, 96, 40, (240, 242, 246), "聘也科技"),
        (304, 52, 34, (64, 134, 204), "HRIS"),
        (310, 138, 34, (88, 174, 102), "人才供应"),
        (192, 26, 21, (234, 146, 56), "SaaS"),
        (192, 166, 21, (68, 156, 178), "数智化"),
    ]
    for nx, ny, nr, col, label in nodes:
        if (nx, ny) != center:
            d.line([center, (nx, ny)], fill=(182, 190, 200), width=3)
    d.ellipse([114, 26, 270, 166], outline=(208, 214, 222), width=2)

    for nx, ny, nr, col, label in nodes:
        d.ellipse([nx - nr + 2, ny - nr + 2, nx + nr + 2, ny + nr + 2], fill=(210, 214, 220))
        outline = (214, 72, 58) if (nx, ny) == center else (248, 250, 252)
        d.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=col, outline=outline, width=3)
        txt_col = (48, 54, 66) if (nx, ny) == center else (252, 252, 254)
        fsize = 16 if (nx, ny) == center else (14 if nr >= 30 else 12)
        draw_crisp_text(img, (nx, ny), label, fsize, txt_col, anchor="mm", threshold=80)

    save(img, "wall_infographic.png")


# 10. Elevator lobby wall with red "福" diamond
def gen_lobby_fu():
    img = Image.new("RGB", (96, 96), (235, 233, 228))
    d = ImageDraw.Draw(img)
    d.polygon([(48, 16), (80, 48), (48, 80), (16, 48)], fill=(204, 34, 36), outline=(234, 186, 60))
    draw_crisp_text(img, (48, 48), "福", 32, (246, 204, 72), anchor="mm", bold_offset=True)
    save(img, "lobby_fu.png")


# 11. Wuhan Conference Room Frosted Glass Decal (RGBA)
def gen_wuhan_glass():
    w, h = 192, 96
    img = Image.new("RGBA", (w, h), (195, 220, 236, 70))
    d = ImageDraw.Draw(img)
    # Frosted translucent middle band
    d.rectangle([0, 28, w - 1, 70], fill=(242, 246, 250, 205))
    d.line([0, 28, w - 1, 28], fill=(215, 224, 232, 235))
    d.line([0, 70, w - 1, 70], fill=(215, 224, 232, 235))
    # Subtle glass highlight diagonal
    for i in range(6):
        d.line([(10 + i * 34, 2), (2 + i * 34, 25)], fill=(255, 255, 255, 95), width=2)
    draw_crisp_text(img, (96, 43), "武汉", 20, (214, 74, 72, 255), anchor="mm", bold_offset=True)
    draw_crisp_text(img, (96, 61), "WUHAN 会议室", 10, (186, 92, 90, 255), anchor="mm")
    save(img, "wuhan_glass.png")


# 12. Curtain Wall Window with Pixel City Skyscraper Outside + Image #1 Diagonal Sheen
def gen_window_city():
    w, h = 64, 128
    img = Image.new("RGB", (w, h), (150, 186, 214))
    d = ImageDraw.Draw(img)
    # Sky gradient top->bottom
    for y in range(h):
        t = y / h
        r = int(146 + t * 54)
        g = int(184 + t * 44)
        b = int(216 + t * 24)
        d.line([(0, y), (w - 1, y)], fill=(r, g, b))
    # Distant modern white-finned office tower silhouette (just like outside their window!)
    d.rectangle([6, 18, 56, 127], fill=(176, 198, 212))
    for x in range(8, 56, 8):
        d.rectangle([x, 18, x + 2, 127], fill=(236, 238, 240))
    for y in range(24, 126, 10):
        d.line([(6, y), (56, y)], fill=(142, 168, 186), width=2)
    # Image #1 crisp diagonal pixel glass sheen!
    for offset in (-20, -14, 10, 16):
        d.line([(offset, 100), (offset + 52, 18)], fill=(224, 240, 252), width=2)
    # Dark blue inner glass edge
    d.rectangle([0, 0, w - 1, h - 1], outline=(98, 124, 146), width=2)
    save(img, "window_city.png")


# 13. Grey Roller Blind Fabric
def gen_blind_grey():
    img = Image.new("RGB", (32, 64), (168, 173, 179))
    px = img.load()
    for y in range(64):
        for x in range(32):
            if y >= 61:
                px[x, y] = (132, 137, 144)
            elif y % 2 == 0:
                px[x, y] = (172, 177, 183)
            else:
                px[x, y] = (162, 167, 173)
    save(img, "blind_grey.png")


# 14. Hanging Sign "技术中心"
def gen_sign_jishu():
    img = Image.new("RGB", (128, 48), (248, 248, 246))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 127, 47], outline=(194, 198, 204), width=2)
    d.rectangle([0, 0, 127, 10], fill=(236, 134, 54))
    draw_crisp_text(img, (64, 29), "技术中心", 20, (54, 60, 72), anchor="mm", bold_offset=True)
    save(img, "sign_jishu.png")


# 15. Hanging Sign "聘也科技"
def gen_sign_pinye():
    img = Image.new("RGB", (128, 48), (52, 58, 68))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 127, 47], outline=(232, 236, 240), width=2)
    d.rectangle([0, 38, 127, 47], fill=(228, 120, 48))
    draw_crisp_text(img, (64, 21), "聘也科技", 20, (248, 250, 252), anchor="mm", bold_offset=True)
    save(img, "sign_pinye.png")


# 16. Hanging Promo / Department Banner (orange-red accent like ceiling signs in videos)
def gen_sign_promo():
    img = Image.new("RGB", (128, 64), (250, 246, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 127, 22], fill=(226, 86, 52))
    d.rectangle([0, 0, 127, 63], outline=(206, 174, 152), width=2)
    draw_crisp_text(img, (64, 11), "业务创新 · 高效协作", 11, (255, 250, 242), anchor="mm")
    draw_crisp_text(img, (64, 43), "产研效能部", 16, (62, 66, 76), anchor="mm", bold_offset=True)
    save(img, "sign_promo.png")


# 17. Glowing Green EXIT Sign
def gen_exit_sign():
    img = Image.new("RGB", (64, 32), (34, 186, 98))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 63, 31], outline=(228, 246, 234), width=2)
    draw_crisp_text(img, (32, 16), "EXIT", 15, (248, 255, 250), anchor="mm", bold_offset=True)
    save(img, "exit_sign.png")


# 18. Monitor Screens (Pixel Art UIs!)
def gen_screens():
    # Dark IDE
    img = Image.new("RGB", (64, 40), (30, 34, 44))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 12, 39], fill=(24, 27, 36))
    d.rectangle([0, 0, 63, 5], fill=(40, 45, 58))
    colors = [(108, 188, 246), (236, 184, 92), (144, 212, 134), (224, 122, 132), (196, 204, 216)]
    for i, y in enumerate(range(8, 30, 3)):
        indent = 16 + (i % 3) * 4
        length = 12 + ((i * 11) % 24)
        d.line([(indent, y), (min(60, indent + length), y)], fill=colors[i % len(colors)], width=2)
    d.rectangle([13, 31, 63, 39], fill=(22, 25, 32))
    d.line([(16, 35), (42, 35)], fill=(120, 214, 146))
    save(img, "screen_ide.png")

    # User Left Monitor (Light warm-amber IDE/app with dark left sidebar, matching Video 2 00:56!)
    img = Image.new("RGB", (80, 48), (242, 224, 186))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 18, 47], fill=(42, 46, 56))
    d.rectangle([0, 0, 79, 7], fill=(224, 206, 172))
    for y in range(11, 42, 4):
        d.line([(3, y), (14, y)], fill=(192, 146, 84) if y == 15 else (112, 120, 136), width=2)
    for i, y in enumerate(range(12, 42, 4)):
        d.line([(23, y), (23 + 22 + (i * 9) % 28, y)], fill=(166, 146, 114), width=2)
    d.rectangle([22, 36, 74, 44], fill=(252, 244, 224), outline=(204, 186, 152))
    save(img, "screen_user_left.png")

    # User Right Monitor (Dark top header + warm cream/peach screen, matching Video 2 00:56!)
    img = Image.new("RGB", (64, 40), (238, 204, 154))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 63, 7], fill=(40, 42, 48))
    d.rectangle([26, 18, 40, 22], fill=(128, 108, 86))
    d.rectangle([4, 34, 60, 38], fill=(226, 188, 136))
    save(img, "screen_user_right.png")

    # Light Chat / Dashboard screen
    img = Image.new("RGB", (64, 40), (244, 247, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, 39], fill=(54, 106, 178))
    d.rectangle([18, 6, 40, 18], fill=(220, 236, 252), outline=(144, 186, 232))
    d.rectangle([44, 6, 60, 18], fill=(252, 232, 212), outline=(232, 168, 118))
    # Mini bar chart
    bars = [12, 18, 10, 15, 20, 14]
    for i, bh in enumerate(bars):
        d.rectangle([20 + i * 6, 36 - bh, 24 + i * 6, 36], fill=(74, 156, 218) if i % 2 == 0 else (98, 192, 136))
    save(img, "screen_chat.png")

    # Large Corner TV Screen
    img = Image.new("RGB", (96, 56), (26, 38, 56))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 95, 10], fill=(36, 62, 98))
    draw_crisp_text(img, (48, 5), "DATA CENTER", 8, (226, 240, 255), anchor="mm")
    d.rectangle([6, 14, 46, 34], fill=(34, 52, 76), outline=(74, 136, 196))
    d.rectangle([50, 14, 90, 34], fill=(34, 52, 76), outline=(88, 186, 138))
    d.rectangle([6, 38, 90, 50], fill=(34, 52, 76), outline=(228, 156, 72))
    for i in range(6):
        d.rectangle([10 + i * 5, 30 - (i * 3 + 4) % 14, 13 + i * 5, 31], fill=(96, 198, 246))
    d.line([(54, 28), (64, 22), (74, 26), (86, 18)], fill=(108, 232, 156), width=2)
    save(img, "screen_tv.png")


# 19. Keyboards (User white 75% mechanical + standard black)
def gen_keyboards():
    # User's white/black 75% mechanical keyboard (Video 2 00:56!)
    img = Image.new("RGB", (64, 28), (196, 200, 208))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 63, 27], outline=(118, 124, 134), width=2)
    for row in range(5):
        y = 3 + row * 4
        for col in range(14):
            x = 4 + col * 4
            is_dark = (row == 0 and col in (0, 13)) or (col == 0) or (col == 13 and row >= 2) or (row == 4 and col in (1, 10, 11, 12))
            if row == 4 and 3 <= col <= 8:
                col_fill = (248, 249, 252)
            elif row == 0 and col == 0:
                col_fill = (224, 96, 74)
            else:
                col_fill = (48, 52, 62) if is_dark else (248, 249, 252)
            d.rectangle([x, y, x + 2, y + 2], fill=col_fill)
    save(img, "keyboard_user.png")

    # Standard black keyboard
    img = Image.new("RGB", (48, 20), (38, 40, 46))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 47, 19], outline=(24, 26, 30))
    for row in range(4):
        for col in range(11):
            d.rectangle([3 + col * 4, 3 + row * 4, 5 + col * 4, 5 + row * 4], fill=(64, 68, 76))
    save(img, "keyboard_std.png")


# 20. Pantry Appliances & Office Props
def gen_appliances():
    # Cream Retro Fridge
    img = Image.new("RGB", (48, 96), (236, 229, 210))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 47, 95], outline=(176, 168, 148), width=2)
    d.line([(2, 42), (45, 42)], fill=(144, 136, 120), width=2)
    d.rectangle([36, 36, 43, 39], fill=(186, 178, 160))
    d.rectangle([36, 46, 43, 49], fill=(186, 178, 160))
    # Tiny Chinese blue energy label sticker!
    d.rectangle([34, 12, 43, 24], fill=(64, 146, 214), outline=(245, 245, 245))
    d.line([(36, 16), (41, 16)], fill=(102, 206, 114))
    d.line([(36, 19), (40, 19)], fill=(242, 208, 72))
    d.line([(36, 22), (39, 22)], fill=(232, 92, 74))
    save(img, "fridge_front.png")

    # White Water Dispenser
    img = Image.new("RGB", (32, 80), (242, 244, 247))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 79], outline=(188, 194, 202), width=2)
    d.rectangle([4, 6, 27, 13], fill=(46, 52, 62))
    d.point((10, 9), fill=(242, 86, 74))
    d.point((21, 9), fill=(76, 174, 242))
    d.rectangle([5, 17, 26, 36], fill=(198, 206, 214), outline=(146, 152, 162))
    d.rectangle([9, 20, 12, 24], fill=(214, 72, 62))
    d.rectangle([19, 20, 22, 24], fill=(62, 142, 214))
    d.rectangle([4, 42, 27, 74], fill=(234, 237, 242), outline=(196, 202, 210))
    save(img, "dispenser_front.png")

    # White Microwave
    img = Image.new("RGB", (48, 32), (244, 245, 247))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 47, 31], outline=(176, 180, 188), width=2)
    d.rectangle([4, 5, 33, 26], fill=(42, 46, 54), outline=(112, 116, 126))
    d.line([(8, 12), (16, 8)], fill=(86, 94, 108))
    d.rectangle([37, 6, 44, 11], fill=(38, 44, 52))
    d.line([(39, 8), (42, 8)], fill=(116, 226, 144))
    for by in (15, 19, 23):
        d.rectangle([38, by, 43, by + 2], fill=(184, 188, 196))
    save(img, "microwave_front.png")

    # Black Coffee Machine
    img = Image.new("RGB", (32, 40), (42, 44, 50))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 39], outline=(24, 25, 30), width=2)
    d.rectangle([4, 4, 27, 11], fill=(56, 60, 68))
    d.point((8, 7), fill=(242, 164, 68))
    d.point((13, 7), fill=(112, 216, 134))
    d.rectangle([6, 15, 25, 32], fill=(26, 28, 33))
    d.rectangle([12, 15, 19, 20], fill=(148, 154, 164))
    d.rectangle([4, 33, 27, 37], fill=(168, 174, 182))
    save(img, "coffee_front.png")

    # Xiaomi White Air Purifier
    img = Image.new("RGB", (32, 64), (244, 245, 247))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 63], outline=(196, 200, 208), width=2)
    # Circular OLED display
    d.ellipse([11, 12, 20, 21], fill=(34, 38, 44))
    d.point((15, 16), fill=(102, 224, 132))
    d.point((16, 16), fill=(102, 224, 132))
    # Iconic perforated intake dot grid on lower half!
    for y in range(28, 58, 3):
        for x in range(5, 27, 3):
            d.point((x, y), fill=(138, 144, 152))
    save(img, "air_purifier.png")

    # Ceiling Cassette AC Unit (4-way louvers)
    img = Image.new("RGB", (48, 48), (244, 246, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 47, 47], outline=(176, 182, 190), width=2)
    # 4 perimeter vent louvers
    d.rectangle([8, 4, 39, 8], fill=(64, 70, 78))
    d.rectangle([8, 39, 39, 43], fill=(64, 70, 78))
    d.rectangle([4, 8, 8, 39], fill=(64, 70, 78))
    d.rectangle([39, 8, 43, 39], fill=(64, 70, 78))
    # Center return grille
    d.rectangle([13, 13, 34, 34], fill=(228, 232, 238), outline=(182, 188, 196))
    for y in range(16, 33, 3):
        d.line([(15, y), (32, y)], fill=(168, 174, 182))
    save(img, "ac_cassette.png")


# 21. Foliage, Plinth, Award Plaque, User Desk Props, Desk Top, Ceiling
def gen_misc():
    # Lush Pixel Pothos Foliage
    img = Image.new("RGB", (32, 32), (76, 146, 68))
    px = img.load()
    greens = [(54, 114, 52), (68, 136, 60), (86, 158, 72), (112, 178, 84), (44, 96, 44)]
    for y in range(32):
        for x in range(32):
            v = (x * 5 + y * 7 + (x ^ y) * 3) % len(greens)
            px[x, y] = greens[v]
    save(img, "foliage_pothos.png")

    # Diorama Plinth Base Edge (matches Image #1's layered grey slab!)
    img = Image.new("RGB", (64, 32), (132, 136, 144))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 63, 7], fill=(196, 200, 206))
    d.line([(0, 8), (63, 8)], fill=(96, 100, 108))
    d.rectangle([0, 9, 63, 26], fill=(138, 142, 150))
    d.rectangle([0, 27, 63, 31], fill=(94, 98, 106))
    for x in range(0, 64, 16):
        d.line([(x, 0), (x, 31)], fill=(116, 120, 128))
    save(img, "plinth_edge.png")

    # Gold Corporate Award Plaque (on Row 4 white cabinet)
    img = Image.new("RGB", (48, 64), (218, 176, 76))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 47, 63], outline=(146, 112, 38), width=3)
    d.rectangle([5, 5, 42, 58], fill=(42, 40, 38), outline=(238, 206, 112))
    d.rectangle([14, 14, 33, 20], fill=(238, 198, 88))
    for y in (28, 34, 40, 46):
        d.line([(12, y), (35, y)], fill=(214, 186, 116), width=2)
    save(img, "award_plaque.png")

    # User's Takeaway Milk-Tea / Coffee Cup
    img = Image.new("RGB", (32, 32), (246, 244, 238))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 8, 31, 22], fill=(242, 192, 54))
    d.rectangle([0, 13, 31, 18], fill=(208, 54, 48))
    d.rectangle([10, 11, 21, 20], fill=(248, 244, 232))
    save(img, "cup_milktea.png")

    # User's Red Tissue Box
    img = Image.new("RGB", (32, 24), (206, 52, 52))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 31, 23], outline=(156, 34, 34), width=2)
    d.rectangle([6, 8, 25, 16], fill=(248, 244, 236))
    d.line([(9, 12), (22, 12)], fill=(206, 52, 52), width=2)
    save(img, "tissue_red.png")

    # Desk top laminate
    img = Image.new("RGB", (64, 64), (242, 243, 244))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 63, 63], outline=(218, 221, 226))
    d.ellipse([28, 6, 35, 13], fill=(172, 176, 184), outline=(140, 144, 152))
    save(img, "desk_top.png")

    # Dark Exposed Industrial Ceiling
    img = Image.new("RGB", (64, 64), (44, 47, 54))
    d = ImageDraw.Draw(img)
    for x in range(0, 64, 16):
        d.line([(x, 0), (x, 63)], fill=(34, 37, 44), width=2)
    for y in range(0, 64, 32):
        d.line([(0, y), (63, y)], fill=(54, 58, 66), width=1)
    save(img, "ceiling_dark.png")


if __name__ == "__main__":
    gen_floor_marble()
    gen_wall_plaster()
    gen_wall_wood_panel()
    gen_cabinet_taupe()
    gen_cabinet_white()
    gen_dark_door()
    gen_pennant_hangbaole()
    gen_wall_honor()
    gen_wall_infographic()
    gen_lobby_fu()
    gen_wuhan_glass()
    gen_window_city()
    gen_blind_grey()
    gen_sign_jishu()
    gen_sign_pinye()
    gen_sign_promo()
    gen_exit_sign()
    gen_screens()
    gen_keyboards()
    gen_appliances()
    gen_misc()

    # Also build a quick visual contact sheet (scaled 3x nearest) for QA!
    names = sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".png") and f != "_preview_sheet.png")
    cols = 6
    cell = 180
    rows = math.ceil(len(names) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), (32, 34, 40))
    sd = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        im = Image.open(os.path.join(OUT_DIR, name)).convert("RGBA")
        # Scale up crisply to fit cell-24
        scale = min((cell - 24) / im.width, (cell - 36) / im.height)
        nw = max(1, int(im.width * scale))
        nh = max(1, int(im.height * scale))
        im_s = im.resize((nw, nh), Image.NEAREST)
        cx = (i % cols) * cell
        cy = (i // cols) * cell
        bg = Image.new("RGBA", (nw, nh), (245, 245, 245, 255))
        bg.alpha_composite(im_s)
        sheet.paste(bg.convert("RGB"), (cx + (cell - nw) // 2, cy + 8 + (cell - 32 - nh) // 2))
        sd.text((cx + 6, cy + cell - 18), name[:-4][:22], fill=(220, 224, 232))
    sheet.save(os.path.join(OUT_DIR, "_preview_sheet.png"))
    print(f"Generated {len(names)} crisp pixel-art textures in {OUT_DIR}")
