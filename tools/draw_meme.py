#!/usr/bin/env python3
"""GTA VI meme (make.fun bounty gta6-meme-x-01).

Two-panel "13 years of waiting" meme:

  panel 1 ("2013") - young CJ (black man, short hair, GREEN t-shirt) holding
                     hands with his young girlfriend (long hair)
  panel 2 ("2026") - the same couple, still holding hands, now grandpa &
                     grandma (white hair, white beard, glasses / white bun),
                     with the make.fun ghost (grim-reaper scythe in hand)
                     standing BEHIND them, taller than them

Big English headline above, centred "my AI made money on make.fun" line below.

Canvas: 1024x1024, all copy readable when scaled down to 480x480.
"""

import math

from PIL import Image, ImageDraw, ImageFont

W = H = 1024

PW, PH = 960, 280                  # panel size
PX = (W - PW) // 2                 # panel left edge (32)
PANEL_Y = (168, 456)               # top edge of panel 1 / panel 2
PANEL_R = 26                       # panel corner radius

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---------------------------------------------------------------- palette ----
BLACK = (12, 12, 16)
OUT = (20, 18, 22)                 # outline colour for artwork
WHITE = (255, 255, 255)
CREAM = (255, 247, 230)
NAVY = (18, 22, 46)
NAVY_D = (10, 12, 28)
YELLOW = (255, 214, 0)
GOLD = (244, 186, 42)
MAGENTA = (226, 40, 170)
MAGENTA_LT = (255, 92, 200)
GREEN = (46, 160, 84)              # CJ's t-shirt
GREEN_D = (32, 120, 62)
PANTS = (46, 56, 78)
SKIN_CJ = (128, 84, 56)            # young CJ skin
SKIN_CJ_SH = (104, 66, 42)
SKIN_CJ_OLD = (120, 82, 58)
SKIN_HER = (238, 190, 158)
SKIN_HER_SH = (214, 162, 130)
SKIN_HER_OLD = (232, 184, 152)
DRESS_HER = (228, 96, 112)
DRESS_HER_OLD = (206, 108, 126)
HAIR_BLACK = (28, 24, 24)
HAIR_WHITE = (238, 238, 240)
HAIR_GREY = (214, 214, 218)


def font(sz):
    return ImageFont.truetype(FONT_PATH, sz)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def text(d, xy, s, size, fill, stroke_width=0, stroke_fill=OUT, anchor="mm"):
    """Single entry point for copy so every call uses font=font(size)."""
    d.text(xy, s, font=font(size), fill=fill, stroke_width=stroke_width,
           stroke_fill=stroke_fill, anchor=anchor)


def fit_size(d, s, max_w, start, floor=16):
    """Largest point size (<= start) at which `s` fits inside max_w pixels."""
    size = start
    while size > floor:
        if d.textlength(s, font=font(size)) <= max_w:
            break
        size -= 1
    return size


def vgrad(img, y0, y1, c0, c1):
    d = ImageDraw.Draw(img)
    span = max(1, y1 - y0 - 1)
    for i in range(y1 - y0):
        d.line([(0, y0 + i), (img.width, y0 + i)], fill=lerp(c0, c1, i / span))


# ------------------------------------------------------------- primitives ----
def sparkle4(d, cx, cy, r, fill):
    k = r * 0.26
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
               (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)],
              fill=fill)


def star5(cx, cy, R, r, rot=-90):
    pts = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return pts


def heart(d, cx, cy, s, fill, outline=OUT, width=3):
    pts = []
    for i in range(0, 360, 5):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 16.0, cy - y * s / 16.0))
    d.polygon(pts, fill=fill, outline=outline, width=width)


# ----------------------------------------------------------------- people ----
HEAD_CY, HEAD_RX, HEAD_RY = 84, 30, 34
FEET_Y = 256
SH_Y = 136


def _hair_cap(d, x, colour, hairline):
    top = HEAD_CY - HEAD_RY + 4
    d.pieslice([x - HEAD_RX - 3, top, x + HEAD_RX + 3, hairline + (hairline - top)],
               180, 360, fill=colour, outline=OUT, width=3)


def draw_person(d, x, cfg):
    """One character; `x` is the vertical body axis, feet on FEET_Y."""
    skin, shade = cfg["skin"], cfg["shade"]
    old = cfg["old"]

    # ---- legs -------------------------------------------------------
    if cfg["dress"]:
        for dx in (-14, 14):
            d.rounded_rectangle([x + dx - 8, 226, x + dx + 8, FEET_Y - 6],
                                radius=7, fill=skin, outline=OUT, width=3)
            d.ellipse([x + dx - 13, FEET_Y - 16, x + dx + 13, FEET_Y + 2],
                      fill=(74, 58, 54), outline=OUT, width=3)
        d.polygon([(x - 30, 166), (x + 30, 166), (x + 46, 232), (x - 46, 232)],
                  fill=cfg["dress"], outline=OUT, width=3)
    else:
        for dx in (-15, 15):
            d.rounded_rectangle([x + dx - 12, 174, x + dx + 12, FEET_Y - 6],
                                radius=9, fill=PANTS, outline=OUT, width=3)
            d.ellipse([x + dx - 17, FEET_Y - 16, x + dx + 17, FEET_Y + 2],
                      fill=(46, 46, 54), outline=OUT, width=3)

    # ---- neck / torso -----------------------------------------------
    d.rectangle([x - 10, 106, x + 10, 130], fill=shade)
    d.rounded_rectangle([x - 34, 122, x + 34, 184], radius=16,
                        fill=cfg["shirt"], outline=OUT, width=3)
    d.rectangle([x - 30, 126, x + 30, 136], fill=cfg["shirt_d"])
    if not cfg["dress"]:
        d.rectangle([x - 6, 186, x + 6, 196], fill=cfg["shirt_d"])   # belt gap

    # ---- outer arm --------------------------------------------------
    ox = 1 if cfg["side"] == "left" else -1
    d.line([(x + ox * 30, SH_Y), (x + ox * 40, 190)], fill=OUT, width=15)
    d.line([(x + ox * 30, SH_Y), (x + ox * 40, 190)], fill=skin, width=9)
    d.ellipse([x + ox * 40 - 9, 190 - 9, x + ox * 40 + 9, 190 + 9],
              fill=skin, outline=OUT, width=3)

    # ---- head -------------------------------------------------------
    if cfg["long_hair"]:
        d.ellipse([x - HEAD_RX - 8, HEAD_CY - HEAD_RY - 6,
                   x + HEAD_RX + 8, HEAD_CY + 26], fill=cfg["hair"], outline=OUT, width=3)
        d.rounded_rectangle([x - HEAD_RX - 8, HEAD_CY - 6, x - HEAD_RX + 12, HEAD_CY + 78],
                            radius=10, fill=cfg["hair"], outline=OUT, width=3)
        d.rounded_rectangle([x + HEAD_RX - 12, HEAD_CY - 6, x + HEAD_RX + 8, HEAD_CY + 78],
                            radius=10, fill=cfg["hair"], outline=OUT, width=3)

    d.ellipse([x - HEAD_RX, HEAD_CY - HEAD_RY, x + HEAD_RX, HEAD_CY + HEAD_RY],
              fill=skin, outline=OUT, width=3)
    d.ellipse([x - HEAD_RX - 4, HEAD_CY - 6, x - HEAD_RX + 4, HEAD_CY + 8],
              fill=skin, outline=OUT, width=3)
    d.ellipse([x + HEAD_RX - 4, HEAD_CY - 6, x + HEAD_RX + 4, HEAD_CY + 8],
              fill=skin, outline=OUT, width=3)

    _hair_cap(d, x, cfg["hair"], HEAD_CY - (22 if old and not cfg["bun"] else 14))

    if cfg["bun"]:
        d.ellipse([x + 8, HEAD_CY - HEAD_RY - 22, x + 40, HEAD_CY - HEAD_RY + 10],
                  fill=cfg["hair"], outline=OUT, width=3)
        d.arc([x - 4, HEAD_CY - HEAD_RY - 2, x + 30, HEAD_CY - HEAD_RY + 22],
              200, 340, fill=OUT, width=3)

    # ---- face -------------------------------------------------------
    if old:
        if cfg["beard"]:
            d.ellipse([x - 25, HEAD_CY + 2, x + 25, HEAD_CY + 44],
                      fill=cfg["hair"], outline=OUT, width=3)
            d.ellipse([x - 13, HEAD_CY + 6, x + 13, HEAD_CY + 20],
                      fill=cfg["hair"], outline=OUT, width=2)
        for ex in (-12, 12):
            d.ellipse([x + ex - 5, HEAD_CY - 8, x + ex + 5, HEAD_CY + 2], fill=OUT)
        d.arc([x - 12, HEAD_CY + 12, x + 12, HEAD_CY + 34], 20, 160, fill=OUT, width=4)
        if cfg["glasses"]:
            for ex in (-13, 13):
                d.ellipse([x + ex - 13, HEAD_CY - 15, x + ex + 13, HEAD_CY + 11],
                          outline=(38, 34, 38), width=4)
            d.line([(x - 1, HEAD_CY - 4), (x + 1, HEAD_CY - 4)], fill=(38, 34, 38), width=4)
            d.line([(x - 26, HEAD_CY - 6), (x - HEAD_RX, HEAD_CY - 8)], fill=(38, 34, 38), width=4)
            d.line([(x + 26, HEAD_CY - 6), (x + HEAD_RX, HEAD_CY - 8)], fill=(38, 34, 38), width=4)
        # brows
        d.line([(x - 22, HEAD_CY - 20), (x - 8, HEAD_CY - 24)], fill=cfg["hair"], width=4)
        d.line([(x + 8, HEAD_CY - 24), (x + 22, HEAD_CY - 20)], fill=cfg["hair"], width=4)
    else:
        for ex in (-11, 11):
            d.ellipse([x + ex - 6, HEAD_CY - 8, x + ex + 6, HEAD_CY + 4], fill=OUT)
            d.ellipse([x + ex - 2, HEAD_CY - 6, x + ex + 2, HEAD_CY - 1], fill=WHITE)
        d.arc([x - 11, HEAD_CY + 10, x + 11, HEAD_CY + 28], 20, 160, fill=OUT, width=4)
        d.line([(x - 20, HEAD_CY - 22), (x - 6, HEAD_CY - 24)], fill=OUT, width=3)
        d.line([(x + 6, HEAD_CY - 24), (x + 20, HEAD_CY - 22)], fill=OUT, width=3)


def draw_couple(d, old):
    """CJ + partner, hands clasped in the middle with a small heart."""
    cj_x, her_x = 372, 588
    hx, hy = 480, 196

    if old:
        cj = dict(skin=SKIN_CJ_OLD, shade=(96, 66, 48), shirt=GREEN, shirt_d=GREEN_D,
                  old=True, dress=False, long_hair=False, bun=False, glasses=True,
                  beard=True, hair=HAIR_WHITE, side="left")
        her = dict(skin=SKIN_HER_OLD, shade=SKIN_HER_SH, shirt=DRESS_HER_OLD,
                   shirt_d=(178, 88, 104), old=True, dress=True, long_hair=False,
                   bun=True, glasses=True, beard=False, hair=HAIR_WHITE, side="right")
    else:
        cj = dict(skin=SKIN_CJ, shade=SKIN_CJ_SH, shirt=GREEN, shirt_d=GREEN_D,
                  old=False, dress=False, long_hair=False, bun=False, glasses=False,
                  beard=False, hair=HAIR_BLACK, side="left")
        her = dict(skin=SKIN_HER, shade=SKIN_HER_SH, shirt=DRESS_HER,
                   shirt_d=(196, 74, 92), old=False, dress=True, long_hair=True,
                   bun=False, glasses=False, beard=False, hair=HAIR_BLACK, side="right")

    draw_person(d, cj_x, cj)
    draw_person(d, her_x, her)

    # inner arms reaching for each other -------------------------------
    d.line([(cj_x + 30, SH_Y + 4), (hx - 14, hy - 6)], fill=OUT, width=16)
    d.line([(cj_x + 30, SH_Y + 4), (hx - 14, hy - 6)], fill=cj["skin"], width=10)
    d.line([(her_x - 30, SH_Y + 4), (hx + 14, hy - 6)], fill=OUT, width=16)
    d.line([(her_x - 30, SH_Y + 4), (hx + 14, hy - 6)], fill=her["skin"], width=10)

    # clasped hands (two overlapping fists + finger lines) ------------
    d.ellipse([hx - 30, hy - 15, hx + 2, hy + 19], fill=cj["skin"], outline=OUT, width=4)
    d.ellipse([hx - 4, hy - 15, hx + 30, hy + 19], fill=her["skin"], outline=OUT, width=4)
    for i, yy in enumerate((hy - 6, hy + 2, hy + 10)):
        d.line([(hx - 8, yy), (hx + 10, yy + 2)], fill=OUT, width=2)
    d.arc([hx - 26, hy - 12, hx + 26, hy + 22], 200, 340, fill=OUT, width=2)

    heart(d, hx, hy - 46, 15, (255, 96, 150), outline=OUT, width=2)


def panel(year, old):
    img = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    if old:
        vgrad(img, 0, 224, (255, 198, 148), (255, 238, 214))
        ImageDraw.Draw(img).ellipse([760, 96, 866, 202], fill=(255, 236, 176),
                                    outline=(246, 176, 96), width=5)
        ground = (122, 132, 96)
        fg = (104, 114, 82)
    else:
        vgrad(img, 0, 224, (118, 190, 232), (214, 238, 248))
        pd0 = ImageDraw.Draw(img)
        pd0.ellipse([790, 34, 882, 126], fill=(255, 232, 138))
        for cx, cy, r in ((180, 56, 26), (232, 62, 34), (286, 52, 24)):
            pd0.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(252, 254, 255))
        ground = (118, 176, 96)
        fg = (100, 154, 80)

    d = ImageDraw.Draw(img)
    d.rectangle([0, 224, PW, PH], fill=ground)
    d.rectangle([0, 224, PW, 232], fill=fg)

    if old:
        # the ghost reaper stands BEHIND the couple -> drawn first
        ghost(d, 478, 91, 75)

    draw_couple(d, old)

    # year badge ------------------------------------------------------
    d.rounded_rectangle([18, 14, 176, 84], radius=14, fill=NAVY_D, outline=YELLOW, width=4)
    text(d, (97, 50), year, 50, YELLOW, stroke_width=1, stroke_fill=NAVY_D)
    return img


# ------------------------------------------------------------------ ghost ----
def bez(p0, p1, p2, t):
    u = 1.0 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def scythe(d, sx, ytop, ybot):
    """Grim-reaper scythe: long upright shaft + sharp curved blade at the top."""
    # shaft ------------------------------------------------------------
    d.line([(sx, ybot), (sx, ytop - 2)], fill=OUT, width=17)
    d.line([(sx, ybot), (sx, ytop - 2)], fill=(116, 78, 48), width=10)
    d.line([(sx - 3, ybot - 8), (sx - 3, ytop + 8)], fill=(160, 114, 72), width=3)
    for yy in (ytop + 16, ytop + 30):                      # binding rings
        d.line([(sx - 9, yy), (sx + 9, yy)], fill=(74, 58, 46), width=5)

    # blade: crescent, outer edge sweeps right and up, tip hooks down ---
    a = (sx + 4, ytop - 2)
    tip = (sx + 190, ytop + 66)
    outer = [bez(a, (sx + 120, ytop - 46), tip, i / 24.0) for i in range(25)]
    inner = [bez(tip, (sx + 108, ytop + 16), a, i / 24.0) for i in range(25)]
    d.polygon(outer + inner, fill=(184, 196, 212), outline=OUT, width=5)
    d.line(outer, fill=(240, 246, 255), width=4)           # cutting edge
    d.line(inner[2:-2], fill=(104, 116, 136), width=3)     # shadowed spine
    d.line([(sx - 2, ytop + 4), (sx + 26, ytop + 14)], fill=OUT, width=6)


def ghost(d, cx, cy, r=75):
    """make.fun ghost (white, black outline, 4-point star eyes, smile) as the
    Grim Reaper: standing behind the couple, gripping a scythe."""
    yb = cy + 103
    rb, n = 19, 3

    def shell(fill, g):
        d.ellipse([cx - r - g, cy - r - g, cx + r + g, cy + r + g], fill=fill)
        d.rectangle([cx - r - g, cy, cx + r + g, yb + g], fill=fill)
        step = (2 * r - 2 * rb) / (n - 1)
        for i in range(n):
            bx = cx - r + rb + i * step
            d.ellipse([bx - rb - g, yb - rb - g, bx + rb + g, yb + rb + g], fill=fill)

    shell(OUT, 9)
    shell(WHITE, 0)

    # face -------------------------------------------------------------
    sparkle4(d, cx - 26, cy - 12, 20, OUT)
    sparkle4(d, cx + 26, cy - 12, 20, OUT)
    d.arc([cx - 27, cy + 14, cx + 27, cy + 58], 15, 165, fill=OUT, width=8)

    # scythe held at the ghost's right side ----------------------------
    sx = cx + 62
    scythe(d, sx, cy - 61, cy + 163)

    # round hand gripping the shaft ------------------------------------
    d.ellipse([sx - 27, cy + 30, sx + 19, cy + 76], fill=WHITE, outline=OUT, width=8)
    for yy in (cy + 42, cy + 56):
        d.line([(sx - 15, yy), (sx + 9, yy)], fill=OUT, width=3)


# ------------------------------------------------------------------- main ----
def main():
    img = Image.new("RGB", (W, H), NAVY)
    vgrad(img, 0, H, (26, 30, 66), (12, 14, 32))
    d = ImageDraw.Draw(img)

    # headline ---------------------------------------------------------
    l1 = "Finally... after 13 years of waiting..."
    l2 = "GTA VI IS FINALLY OUT!"
    s1 = fit_size(d, l1, 952, 44)
    s2 = fit_size(d, l2, 952, 82)
    text(d, (W // 2, 46), l1, s1, CREAM, stroke_width=5, stroke_fill=BLACK)
    text(d, (W // 2, 118), l2, s2, YELLOW, stroke_width=6, stroke_fill=BLACK)

    # panels -----------------------------------------------------------
    for (label, old), y in zip((("2013", False), ("2026", True)), PANEL_Y):
        p = panel(label, old)
        mask = Image.new("L", (PW, PH), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=PANEL_R, fill=255)
        img.paste(p, (PX, y), mask)
        d.rounded_rectangle([PX, y, PX + PW - 1, y + PH - 1], radius=PANEL_R,
                            outline=YELLOW, width=5)

    # footer -----------------------------------------------------------
    d.line([(28, 738), (W - 28, 738)], fill=(64, 70, 110), width=3)

    lines = ("While you waited,", "my AI made money", "on make.fun")
    for i, s in enumerate(lines):
        size = fit_size(d, s, 900, 50)
        text(d, (W // 2, 792 + i * 58), s, size, CREAM, stroke_width=4,
             stroke_fill=BLACK, anchor="mm")

    img.save("meme.png")
    print("meme.png written", img.size)


if __name__ == "__main__":
    main()
