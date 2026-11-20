#!/usr/bin/env python3
"""GTA VI meme (make.fun bounty gta6-meme-x-01) - 3D shaded edition, pure PIL.

Two-panel "13 years of waiting" meme:

  panel 1 ("2013") - young CJ (green tee) holding hands with his young
                     girlfriend, pink heart, blue sky, sun.
  panel 2 ("2026") - the same couple as grandpa & grandma (white hair/beard,
                     glasses, bun), still holding hands, with the make.fun
                     ghost standing BEHIND them gripping a grim-reaper scythe,
                     sunset sky.

Every bit of "3D" here is built with PIL only: no numpy, no other libs.
Volume comes from
  * per-pixel gradient paints (paint_vgrad / paint_hgrad / paint_sphere),
  * masks + ImageChops for directional shade & rim light inside a shape,
  * ImageFilter.GaussianBlur for soft shadows, glow and contact shadows,
  * projected silhouette shadows (AFFINE transform of the alpha channel).

Canvas: 1024x1024, all copy readable when scaled down to 480x480.
"""

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W = H = 1024

PW, PH = 960, 280                  # panel size
PX = (W - PW) // 2                 # panel left edge (32)
PANEL_Y = (168, 456)               # top edge of panel 1 / panel 2
PANEL_R = 26                       # panel corner radius

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ---------------------------------------------------------------- palette ----
BLACK = (10, 10, 14)
OUT = (26, 22, 28)                 # outline colour for artwork
WHITE = (255, 255, 255)
CREAM = (255, 247, 230)
NAVY_D = (10, 12, 28)
YELLOW = (255, 214, 0)

GREEN = (52, 158, 86)              # CJ's t-shirt
DRESS = (226, 92, 110)             # her dress
DRESS_OLD = (208, 112, 130)
PANTS = (52, 60, 82)
SKIN_CJ = (134, 86, 56)
SKIN_HER = (238, 192, 158)
HAIR_BLACK = (34, 28, 28)
HAIR_WHITE = (232, 232, 236)


def font(sz):
    return ImageFont.truetype(FONT_PATH, sz)


# ------------------------------------------------------------ colour maths ---
def mix(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def lighten(c, t):
    return mix(c, (255, 255, 255), t)


def darken(c, t):
    return mix(c, (0, 0, 0), t)


def grad_stops(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= t <= p1:
            k = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return mix(c0, c1, k)
    return stops[-1][1]


# ------------------------------------------------------------ paint engines --
def paint_vgrad(stops):
    """Vertical multi-stop gradient, one loop over scanlines."""
    def f(size):
        w, h = size
        img = Image.new("RGB", size)
        rows = []
        for y in range(h):
            c = grad_stops(stops, y / max(1, h - 1))
            rows.extend([c] * w)
        img.putdata(rows)
        return img
    return f


def paint_hgrad(stops):
    def f(size):
        w, h = size
        img = Image.new("RGB", size)
        line = [grad_stops(stops, x / max(1, w - 1)) for x in range(w)]
        rows = line * h
        img.putdata(rows)
        return img
    return f


def paint_sphere(hi, mid, lo, lx=0.45, ly=0.30, power=1.0):
    """Radial 'lit sphere' gradient; (lx, ly) is the highlight, in -1..1."""
    def f(size):
        w, h = size
        out = []
        sx = max(1, w - 1)
        sy = max(1, h - 1)
        for y in range(h):
            ny = (y / sy) * 2.0 - 1.0
            for x in range(w):
                nx = (x / sx) * 2.0 - 1.0
                d = math.hypot(nx - lx, ny - ly) / 1.85
                t = min(1.0, max(0.0, d)) ** power
                if t < 0.55:
                    out.append(mix(hi, mid, t / 0.55))
                else:
                    out.append(mix(mid, lo, (t - 0.55) / 0.45))
        img = Image.new("RGB", size)
        img.putdata(out)
        return img
    return f


# ---------------------------------------------------------------- compositing -
def new_layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def paste_paint(layer, mask, painter):
    """Composite `painter(mask size)` RGB through `mask` onto `layer`."""
    bb = mask.getbbox()
    if not bb:
        return
    crop = mask.crop(bb).filter(ImageFilter.GaussianBlur(0.6))
    rgb = painter((crop.width, crop.height)).convert("RGBA")
    rgb.putalpha(crop)
    layer.alpha_composite(rgb, (bb[0], bb[1]))


def ring(mask, ow):
    """Outline band of width ow around a mask."""
    k = 2 * ow + 1
    dil = mask.filter(ImageFilter.MaxFilter(k if k % 2 else k + 1))
    return ImageChops.subtract(dil, mask).filter(ImageFilter.GaussianBlur(0.7))


OUTLINE_MAX = 1                    # hairline only: thick strokes read as a sticker
EDGE_SOFT = (60, 50, 46)           # warm dark used for 1 px rims


def outline(layer, mask, ow=1, colour=EDGE_SOFT):
    """Hairline edge around a mask.

    Every shape used to get a 3-6 px near-black stroke, which is what made the
    whole panel look like a die-cut sticker.  Nothing wider than OUTLINE_MAX is
    drawn now, and the stroke colour is a warm dark that sits *with* the local
    colour instead of cutting it out.
    """
    layer.paste(colour, (0, 0), ring(mask, min(ow, OUTLINE_MAX)))


def edge_grad(mask, strength, side, softness=6):
    """Alpha gradient across a mask, opaque at `side` ('l','r','t','b')."""
    w, h = mask.size
    if side in ("l", "r"):
        small = Image.new("L", (48, 1))
        for i in range(48):
            t = i / 47.0
            v = strength * (1 - t) ** 1.5 if side == "l" else strength * t ** 1.5
            small.putpixel((i, 0), int(max(0, min(255, v))))
        g = small.resize((w, h), Image.BILINEAR)
    else:
        small = Image.new("L", (1, 48))
        for i in range(48):
            t = i / 47.0
            v = strength * (1 - t) ** 1.5 if side == "t" else strength * t ** 1.5
            small.putpixel((0, i), int(max(0, min(255, v))))
        g = small.resize((w, h), Image.BILINEAR)
    if softness:
        g = g.filter(ImageFilter.GaussianBlur(softness))
    return ImageChops.multiply(g, mask)


def shade_side(layer, mask, side, strength=120, softness=7, colour=(0, 0, 0)):
    layer.paste(colour, (0, 0), edge_grad(mask, strength, side, softness))


def rim_light(layer, mask, dx=3, dy=3, blur=1.6, colour=(255, 245, 225), amount=150):
    """Thin lit edge on the +dx/+dy opposite side of a shape."""
    band = ImageChops.multiply(ImageChops.subtract(mask, ImageChops.offset(mask, dx, dy)), mask)
    band = band.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * amount / 255))
    layer.paste(colour, (0, 0), band)


def soft_blob(layer, box, colour, alpha=90, blur=8):
    b = new_layer(layer.size)
    bb = [int(box[0]), int(box[1]), int(box[2]), int(box[3])]
    ImageDraw.Draw(b).ellipse(bb, fill=colour + (alpha,))
    layer.alpha_composite(b.filter(ImageFilter.GaussianBlur(blur)))


def limb_mask(size, pts, w0, w1):
    """Tapered capsule along a polyline."""
    m = Image.new("L", size, 0)
    p = ImageDraw.Draw(m)
    n = max(1, len(pts) - 1)
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        wa = w0 + (w1 - w0) * (i / n)
        wb = w0 + (w1 - w0) * ((i + 1) / n)
        p.line([a, b], fill=255, width=int(round(wa)))
        for pt, ww in ((a, wa), (b, wb)):
            r = ww / 2.0
            p.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=255)
    return m


def limb(layer, pts, w0, w1, hi, lo, ow=3, light_up=True):
    m = limb_mask(layer.size, pts, w0, w1)
    stops = [(0.0, hi), (0.45, mix(hi, lo, 0.45)), (1.0, lo)] if light_up else [(0.0, lo), (1.0, hi)]
    paste_paint(layer, m, paint_vgrad(stops))
    shade_side(layer, m, "l", 90, 4)
    rim_light(layer, m, 2, 2, 1.2, amount=110)
    outline(layer, m, ow)
    return m


# ------------------------------------------------------------------ people ---
def fist(layer, x, y, r, skin, ow=3):
    m = Image.new("L", layer.size, 0)
    ImageDraw.Draw(m).ellipse([x - r, y - r, x + r, y + r], fill=255)
    paste_paint(layer, m, paint_sphere(lighten(skin, .34), skin, darken(skin, .4),
                                       lx=0.3, ly=-0.35))
    f = ImageDraw.Draw(layer)
    f.arc([x - r * .8, y - r * .6, x + r * .8, y + r * .5], 200, 340,
          fill=darken(skin, .55), width=2)
    outline(layer, m, ow)


def person(layer, cx, feet, cfg, hand=None):
    """One 3D-shaded character standing on `feet`; `cx` = body axis."""
    skin = cfg["skin"]
    shirt = cfg["shirt"]
    old = cfg.get("old", False)
    s_hi, s_lo = lighten(skin, .46), darken(skin, .46)
    sh_hi, sh_lo = lighten(shirt, .38), darken(shirt, .5)

    hrx, hry = 23, 27
    hcy = feet - 146
    sh_y = feet - 104
    waist = feet - 60
    hip = feet - 54
    ankle = feet - 8

    # ---- legs ----------------------------------------------------------
    leg_top = waist + 6 if cfg.get("dress") else hip - 8
    for dx in (-11, 11):
        m = limb_mask(layer.size, [(cx + dx, leg_top), (cx + dx * 1.15, ankle)],
                      21 if not cfg.get("dress") else 16, 15 if cfg.get("dress") else 18)
        col = skin if cfg.get("dress") else PANTS
        paste_paint(layer, m, paint_hgrad([(0, darken(col, .42)), (0.55, col),
                                           (1.0, lighten(col, .2))]))
        rim_light(layer, m, 2, 2, 1.2, amount=95)
        shade_side(layer, m, "l", 105, 3)

    # ---- shoes ---------------------------------------------------------
    for dx in (-11, 11):
        sx = cx + dx * 1.15
        m = Image.new("L", layer.size, 0)
        sm = ImageDraw.Draw(m)
        sm.rounded_rectangle([sx - 14, ankle - 4, sx + 15, feet + 2], radius=7, fill=255)
        sm.ellipse([sx + 6, ankle - 2, sx + 16, feet + 2], fill=255)
        dark_shoe = (56, 46, 44) if not cfg.get("dress") else (74, 56, 58)
        paste_paint(layer, m, paint_sphere(lighten(dark_shoe, .42), dark_shoe,
                                           darken(dark_shoe, .55), lx=0.2, ly=-0.5))
        outline(layer, m, 3)

    # ---- torso / dress -------------------------------------------------
    if cfg.get("dress"):
        # bodice
        m = Image.new("L", layer.size, 0)
        p = ImageDraw.Draw(m)
        p.polygon([(cx - 27, sh_y + 6), (cx + 27, sh_y + 6), (cx + 22, waist + 6),
                   (cx - 22, waist + 6)], fill=255)
        p.ellipse([cx - 27, sh_y - 4, cx + 27, sh_y + 26], fill=255)
        p.ellipse([cx - 22, waist - 8, cx + 22, waist + 10], fill=255)
        paste_paint(layer, m, paint_hgrad([(0, darken(shirt, .5)), (0.5, shirt),
                                           (1, lighten(shirt, .3))]))
        shade_side(layer, m, "l", 130, 6)
        rim_light(layer, m, 3, 2, 1.4, amount=150)
        outline(layer, m, 3)
        # skirt: flared, folded
        knee = feet - 52
        m = Image.new("L", layer.size, 0)
        p = ImageDraw.Draw(m)
        p.polygon([(cx - 24, waist + 2), (cx + 24, waist + 2), (cx + 42, knee),
                   (cx - 42, knee)], fill=255)
        p.ellipse([cx - 43, knee - 14, cx + 43, knee + 10], fill=255)
        paste_paint(layer, m, paint_vgrad([(0, lighten(shirt, .26)), (0.5, shirt),
                                           (1, darken(shirt, .38))]))
        d2 = ImageDraw.Draw(layer)
        for fx in (-20, -2, 16):
            d2.line([(cx + fx * 0.6, waist + 6), (cx + fx, knee + 2)],
                    fill=darken(shirt, .42), width=3)
        shade_side(layer, m, "l", 120, 7)
        rim_light(layer, m, 3, 2, 1.5, amount=140)
        outline(layer, m, 3)
    else:
        m = Image.new("L", layer.size, 0)
        p = ImageDraw.Draw(m)
        p.polygon([(cx - 29, sh_y + 8), (cx + 29, sh_y + 8), (cx + 24, waist),
                   (cx - 24, waist)], fill=255)
        p.ellipse([cx - 31, sh_y - 8, cx - 6, sh_y + 24], fill=255)
        p.ellipse([cx + 6, sh_y - 8, cx + 31, sh_y + 24], fill=255)
        p.ellipse([cx - 25, sh_y - 12, cx + 25, sh_y + 26], fill=255)
        p.ellipse([cx - 25, waist - 10, cx + 25, waist + 8], fill=255)
        paste_paint(layer, m, paint_vgrad([(0, sh_hi), (0.5, shirt), (1, sh_lo)]))
        shade_side(layer, m, "l", 135, 7)
        # fabric folds + chest volume
        soft_blob(layer, [cx + 2, sh_y + 14, cx + 26, waist - 2], lighten(shirt, .3), 40, 9)
        rim_light(layer, m, 3, 2, 1.4, amount=150)
        outline(layer, m, 3)
        # belt
        d2 = ImageDraw.Draw(layer)
        d2.rounded_rectangle([cx - 25, waist - 9, cx + 25, waist + 2], radius=4,
                             fill=(58, 44, 38), outline=OUT, width=2)
        d2.rectangle([cx - 6, waist - 9, cx + 6, waist + 2], fill=(196, 160, 70),
                     outline=OUT, width=1)

    # ---- neck ----------------------------------------------------------
    m = Image.new("L", layer.size, 0)
    p = ImageDraw.Draw(m)
    p.rounded_rectangle([cx - 8, hcy + 20, cx + 8, sh_y + 6], radius=5, fill=255)
    paste_paint(layer, m, paint_hgrad([(0, darken(skin, .5)), (0.5, skin),
                                       (1, lighten(skin, .18))]))
    outline(layer, m, 3)
    # chin shadow on the chest
    soft_blob(layer, [cx - 16, sh_y - 6, cx + 16, sh_y + 22], (0, 0, 0), 95, 6)

    # ---- outer arm -----------------------------------------------------
    ox = -1 if cfg.get("light", "r") == "r" else 1
    shoulder = (cx + ox * 27, sh_y + 4)
    elbow = (cx + ox * 40, sh_y + 46)
    wrist = (cx + ox * 40, feet - 76)
    limb(layer, [shoulder, elbow, wrist], 20, 15, lighten(skin, .22), darken(skin, .48))
    fist(layer, wrist[0], wrist[1] + 6, 9, skin)
    # short sleeve over the shoulder
    ms = Image.new("L", layer.size, 0)
    ps = ImageDraw.Draw(ms)
    ps.ellipse([shoulder[0] - 16, shoulder[1] - 14, shoulder[0] + 16, shoulder[1] + 18], fill=255)
    paste_paint(layer, ms, paint_sphere(sh_hi, shirt, sh_lo, lx=ox * 0.4, ly=-0.4))
    shade_side(layer, ms, "l", 110, 5)
    rim_light(layer, ms, 2 * ox, 2, 1.2, amount=120)
    outline(layer, ms, 3)

    # ---- inner arm reaching to the partner ------------------------------
    if hand:
        sh2 = (cx - ox * 27, sh_y + 6)
        elbow2 = (cx - ox * (14), sh_y + 52)
        limb(layer, [sh2, elbow2, hand], 19, 14, lighten(skin, .24), darken(skin, .45))
        ms = Image.new("L", layer.size, 0)
        ps = ImageDraw.Draw(ms)
        ps.ellipse([sh2[0] - 15, sh2[1] - 13, sh2[0] + 15, sh2[1] + 17], fill=255)
        paste_paint(layer, ms, paint_sphere(sh_hi, shirt, sh_lo, lx=-ox * 0.4, ly=-0.4))
        outline(layer, ms, 3)

    # =====================================================================
    # head
    # =====================================================================
    hair = cfg["hair"]
    h_hi, h_lo = lighten(hair, .3), darken(hair, .45)

    if cfg.get("long_hair"):
        mh = Image.new("L", layer.size, 0)
        ph = ImageDraw.Draw(mh)
        ph.ellipse([cx - hrx - 9, hcy - hry - 6, cx + hrx + 9, hcy + 22], fill=255)
        ph.rounded_rectangle([cx - hrx - 9, hcy - 6, cx + hrx + 9, hcy + 74], radius=12, fill=255)
        ph.polygon([(cx - hrx - 9, hcy + 20), (cx - hrx + 6, hcy + 30),
                    (cx - hrx + 4, hcy + 78), (cx - hrx - 9, hcy + 78)], fill=0)
        ph.polygon([(cx + hrx + 9, hcy + 20), (cx + hrx - 6, hcy + 30),
                    (cx + hrx - 4, hcy + 78), (cx + hrx + 9, hcy + 78)], fill=0)
        paste_paint(layer, mh, paint_vgrad([(0, h_hi), (0.4, hair), (1, h_lo)]))
        dl = ImageDraw.Draw(layer)
        for sx in (-18, -6, 8, 19):
            dl.line([(cx + sx, hcy + 34), (cx + sx * 1.1, hcy + 70)],
                    fill=darken(hair, .55), width=2)
        soft_blob(layer, [cx - 8, hcy + 40, cx + 26, hcy + 74], hair, 90, 8)
        outline(layer, mh, 3)

    if cfg.get("bun"):
        mb = Image.new("L", layer.size, 0)
        ImageDraw.Draw(mb).ellipse([cx + 10, hcy - hry - 20, cx + 42, hcy - hry + 12], fill=255)
        paste_paint(layer, mb, paint_sphere(WHITE, hair, darken(hair, .35), lx=0.3, ly=-0.4))
        outline(layer, mb, 3)

    # skull
    m = Image.new("L", layer.size, 0)
    p = ImageDraw.Draw(m)
    p.ellipse([cx - hrx, hcy - hry, cx + hrx, hcy + hry], fill=255)
    p.ellipse([cx - hrx * 0.82, hcy - hry * 0.2, cx + hrx * 0.82, hcy + hry * 1.06], fill=255)
    paste_paint(layer, m, paint_sphere(s_hi, skin, s_lo, lx=0.34, ly=-0.1))
    shade_side(layer, m, "l", 70, 8)

    # ears
    for ex in (-hrx + 1, hrx - 1):
        me = Image.new("L", layer.size, 0)
        ImageDraw.Draw(me).ellipse([cx + ex - 5, hcy + 2, cx + ex + 5, hcy + 14], fill=255)
        paste_paint(layer, me, paint_sphere(s_hi, skin, s_lo, lx=0.3, ly=-0.2))
        outline(layer, me, 2)

    # hair on top
    mh = Image.new("L", layer.size, 0)
    ph = ImageDraw.Draw(mh)
    top = hcy - hry
    ph.ellipse([cx - hrx - 2, top - 4, cx + hrx + 2, top + 40], fill=255)
    ph.polygon([(cx - hrx - 2, top + 22), (cx - hrx - 2, top + 40),
                (cx - hrx + 4, top + 38), (cx - hrx + 6, top + 20)], fill=255)
    ph.polygon([(cx + hrx + 2, top + 22), (cx + hrx + 2, top + 40),
                (cx + hrx - 4, top + 38), (cx + hrx - 6, top + 20)], fill=255)
    paste_paint(layer, mh, paint_vgrad([(0, lighten(hair, .4)), (0.35, hair),
                                        (1, darken(hair, .5))]))
    dl = ImageDraw.Draw(layer)
    for i, sx in enumerate((-16, -8, 0, 8, 16)):
        dl.line([(cx + sx * .5, top + 4), (cx + sx, top + 26)],
                fill=darken(hair, .45), width=2)
    rim_light(layer, mh, 3, 2, 1.6, amount=190)
    outline(layer, mh, 3)

    # ---- face ----------------------------------------------------------
    ey = hcy - 3
    for ex in (-9, 9):
        soft_blob(layer, [cx + ex - 8, ey - 9, cx + ex + 8, ey + 4], (0, 0, 0), 70, 5)
        me = Image.new("L", layer.size, 0)
        ImageDraw.Draw(me).ellipse([cx + ex - 6, ey - 5, cx + ex + 6, ey + 4], fill=255)
        layer.paste((250, 246, 240), (0, 0), me)
        di = ImageDraw.Draw(layer)
        iris = (86, 56, 36) if not cfg.get("old") else (120, 110, 100)
        di.ellipse([cx + ex - 3, ey - 4, cx + ex + 3, ey + 3], fill=iris)
        di.ellipse([cx + ex - 1, ey - 3, cx + ex + 1, ey + 1], fill=BLACK)
        di.ellipse([cx + ex + 0.5, ey - 3, cx + ex + 2, ey - 1], fill=WHITE)
        di.line([(cx + ex - 6, ey - 6), (cx + ex + 6, ey - 6)], fill=darken(skin, .6), width=2)
    d = ImageDraw.Draw(layer)
    # brows
    bw = 3 if not old else 4
    d.line([(cx - 16, ey - 12), (cx - 4, ey - 14)], fill=darken(hair, .2), width=bw)
    d.line([(cx + 4, ey - 14), (cx + 16, ey - 12)], fill=darken(hair, .2), width=bw)

    # nose: shadowed side + lit bridge
    soft_blob(layer, [cx - 3, hcy + 4, cx + 6, hcy + 14], darken(skin, .55), 95, 3)
    d.line([(cx + 1, hcy + 3), (cx + 3, hcy + 12)], fill=lighten(skin, .35), width=3)
    d.arc([cx - 4, hcy + 8, cx + 5, hcy + 16], 20, 150, fill=darken(skin, .5), width=2)

    # mouth
    my = hcy + 19
    if old:
        d.arc([cx - 9, my - 4, cx + 9, my + 9], 20, 160, fill=darken(skin, .5), width=3)
    else:
        d.arc([cx - 10, my - 5, cx + 10, my + 10], 25, 155, fill=(118, 62, 58), width=3)
        d.line([(cx - 6, my + 8), (cx + 6, my + 8)], fill=lighten(skin, .25), width=2)

    # cheeks / specular
    soft_blob(layer, [cx + 4, hcy + 6, cx + 20, hcy + 20], lighten(skin, .5), 55, 7)
    soft_blob(layer, [cx - 20, hcy + 6, cx - 6, hcy + 20], (150, 60, 60), 40, 7)

    if old:
        # wrinkles + bags
        for i, ww in enumerate((16, 21)):
            d.arc([cx - ww, hcy - 12 + i * 3, cx + ww, hcy + 8 + i * 3], 200, 340,
                  fill=darken(skin, .3), width=1)
        for ex in (-9, 9):
            d.arc([cx + ex - 7, ey + 2, cx + ex + 7, ey + 9], 10, 170,
                  fill=darken(skin, .35), width=1)
        d.line([(cx - 14, hcy + 12), (cx - 9, hcy + 18)], fill=darken(skin, .35), width=1)
        d.line([(cx + 14, hcy + 12), (cx + 9, hcy + 18)], fill=darken(skin, .35), width=1)
        d.line([(cx - 8, hcy - 20), (cx + 8, hcy - 20)], fill=darken(skin, .28), width=1)
        d.line([(cx - 6, hcy - 24), (cx + 6, hcy - 24)], fill=darken(skin, .28), width=1)

    if cfg.get("beard"):
        mb = Image.new("L", layer.size, 0)
        pb = ImageDraw.Draw(mb)
        pb.ellipse([cx - 22, hcy + 6, cx + 22, hcy + 34], fill=255)
        pb.ellipse([cx - 12, hcy + 12, cx + 12, hcy + 26], fill=0)
        paste_paint(layer, mb, paint_vgrad([(0, lighten(hair, .18)), (1, darken(hair, .3))]))
        for sx in (-16, -8, 8, 16):
            d.line([(cx + sx, hcy + 20), (cx + sx, hcy + 30)], fill=darken(hair, .3), width=1)
        outline(layer, mb, 2)

    if cfg.get("glasses"):
        d.ellipse([cx - 19, ey - 10, cx - 3, ey + 6], outline=(52, 48, 52), width=3)
        d.ellipse([cx + 3, ey - 10, cx + 19, ey + 6], outline=(52, 48, 52), width=3)
        d.line([(cx - 3, ey - 3), (cx + 3, ey - 3)], fill=(52, 48, 52), width=3)
        d.line([(cx - 19, ey - 4), (cx - hrx, ey - 6)], fill=(52, 48, 52), width=2)
        d.line([(cx + 19, ey - 4), (cx + hrx, ey - 6)], fill=(52, 48, 52), width=2)
        d.line([(cx - 16, ey - 7), (cx - 9, ey + 2)], fill=(226, 236, 248), width=2)
        d.line([(cx + 6, ey - 7), (cx + 13, ey + 2)], fill=(226, 236, 248), width=2)

    outline(layer, m, 3)
    rim_light(layer, m, 3, 3, 2.2, amount=120)


def couple(layer, old):
    """CJ + partner, hands clasped in the middle; returns the clasp point."""
    if old:
        cj_x, her_x = 356, 604
        hx, hy = 480, 214
        cj = dict(skin=(124, 84, 60), shirt=GREEN, old=True, dress=False,
                  hair=HAIR_WHITE, beard=True, glasses=True, side="left")
        her = dict(skin=(230, 182, 150), shirt=DRESS_OLD, old=True, dress=True,
                   hair=HAIR_WHITE, bun=True, glasses=True, long_hair=False, side="right")
    else:
        cj_x, her_x = 362, 598
        hx, hy = 480, 196
        cj = dict(skin=SKIN_CJ, shirt=GREEN, old=False, dress=False,
                  hair=HAIR_BLACK, beard=False, glasses=False, side="left")
        her = dict(skin=SKIN_HER, shirt=DRESS, old=False, dress=True,
                   hair=HAIR_BLACK, long_hair=True, bun=False, glasses=False, side="right")

    cj["light"], her["light"] = "r", "r"
    person(layer, cj_x, 252, cj, hand=(hx - 16, hy))
    person(layer, her_x, 252, her, hand=(hx + 16, hy))

    # clasped hands
    m = Image.new("L", layer.size, 0)
    p = ImageDraw.Draw(m)
    p.ellipse([hx - 26, hy - 14, hx + 2, hy + 16], fill=255)
    p.ellipse([hx - 2, hy - 14, hx + 26, hy + 16], fill=255)
    paste_paint(layer, m, paint_sphere(lighten(cj["skin"], .4), cj["skin"],
                                       darken(cj["skin"], .45), lx=0.2, ly=-0.4))
    d = ImageDraw.Draw(layer)
    for yy in (hy - 6, hy + 1, hy + 8):
        d.line([(hx - 8, yy), (hx + 10, yy + 1)], fill=darken(cj["skin"], .55), width=2)
    d.arc([hx - 24, hy - 12, hx + 24, hy + 18], 200, 340, fill=lighten(cj["skin"], .4), width=2)
    outline(layer, m, 3)
    return (hx, hy)


# ------------------------------------------------------------------- ghost ---
def bez(p0, p1, p2, t):
    u = 1.0 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def scythe(layer, sx, ytop, ybot):
    """Grim-reaper scythe with wood grain, steel gradient and specular edge."""
    # shaft ------------------------------------------------------------
    m = limb_mask(layer.size, [(sx, ybot), (sx, ytop - 2)], 16, 13)
    paste_paint(layer, m, paint_hgrad([(0, (78, 50, 32)), (0.4, (150, 104, 62)),
                                       (0.62, (196, 148, 96)), (1, (96, 62, 40))]))
    d = ImageDraw.Draw(layer)
    for i in range(6):
        yy = ytop + 16 + i * 26
        d.line([(sx - 5, yy), (sx + 4, yy + 2)], fill=(108, 70, 44), width=1)
    outline(layer, m, 3)
    for yy in (ytop + 4, ybot - 34):                       # metal collars
        m = limb_mask(layer.size, [(sx, yy - 6), (sx, yy + 6)], 22, 22)
        paste_paint(layer, m, paint_hgrad([(0, (86, 92, 104)), (0.45, (206, 214, 226)),
                                           (1, (74, 80, 92))]))
        outline(layer, m, 2)

    # blade: crescent sweeping right and up, tip hooking down -----------
    a = (sx + 3, ytop - 4)
    tip = (sx + 178, ytop + 58)
    outer = [bez(a, (sx + 118, ytop - 52), tip, i / 26.0) for i in range(27)]
    inner = [bez(tip, (sx + 104, ytop + 14), a, i / 26.0) for i in range(27)]
    m = Image.new("L", layer.size, 0)
    ImageDraw.Draw(m).polygon(outer + inner, fill=255)
    paste_paint(layer, m, paint_vgrad([(0, (250, 252, 255)), (0.30, (176, 188, 206)),
                                       (0.58, (86, 96, 116)), (1.0, (196, 206, 222))]))
    paste_paint(layer, m, paint_hgrad([(0, (255, 255, 255)), (0.35, (128, 138, 158)),
                                       (1, (150, 160, 180))]))
    d = ImageDraw.Draw(layer)
    d.line(outer, fill=(248, 252, 255), width=4)          # cutting edge
    d.line(inner[1:-1], fill=(46, 50, 62), width=3)       # spine shadow
    spec = [bez(a, (sx + 118, ytop - 46), tip, i / 26.0) for i in range(27)]
    d.line([(p[0], p[1] + 6) for p in spec], fill=(255, 255, 255), width=2)
    outline(layer, m, 3)
    rim_light(layer, m, 3, 3, 1.6, amount=200)


def ghost(layer, cx, cy, r=78):
    """make.fun ghost as the reaper: volume-shaded dome, star eyes, smile."""
    yb = cy + 104
    rb, n = 20, 3

    base = Image.new("L", layer.size, 0)
    p = ImageDraw.Draw(base)
    p.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    p.rectangle([cx - r, cy, cx + r, yb], fill=255)
    step = (2 * r - 2 * rb) / (n - 1)
    for i in range(n):
        bx = cx - r + rb + i * step
        p.ellipse([bx - rb, yb - rb, bx + rb, yb + rb], fill=255)

    # soft spirit glow behind the body
    glow = base.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.55))
    layer.paste((236, 246, 255), (0, 0), glow)

    paste_paint(layer, base, paint_sphere((255, 255, 255), (238, 242, 250),
                                          (176, 186, 206), lx=0.35, ly=-0.55))
    shade_side(layer, base, "l", 80, 9, (120, 132, 168))
    shade_side(layer, base, "b", 60, 10, (150, 160, 190))
    rim_light(layer, base, 4, 4, 2.0, (255, 255, 255), 210)

    # inner shadow under the arms gives the sheet depth
    soft_blob(layer, [cx - r + 10, cy + 34, cx + r - 10, cy + 86], (150, 160, 190), 55, 14)

    # star eyes with specular glints
    for ex in (-26, 26):
        star = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            rr = 19 if i % 2 == 0 else 5.5
            star.append((cx + ex + rr * math.cos(ang), cy - 26 + rr * math.sin(ang)))
        ms = Image.new("L", layer.size, 0)
        ImageDraw.Draw(ms).polygon(star, fill=255)
        paste_paint(layer, ms, paint_sphere((90, 86, 96), OUT, BLACK, lx=0.2, ly=-0.3))
        dg = ImageDraw.Draw(layer)
        dg.ellipse([cx + ex - 3, cy - 30, cx + ex + 2, cy - 25], fill=(226, 230, 240))

    # smile: dark mouth, lit lower lip, soft corners
    d = ImageDraw.Draw(layer)
    d.arc([cx - 30, cy - 6, cx + 30, cy + 36], 18, 162, fill=OUT, width=9)
    d.arc([cx - 26, cy + 2, cx + 26, cy + 36], 22, 158, fill=(252, 252, 255), width=3)
    soft_blob(layer, [cx - 26, cy + 18, cx + 26, cy + 46], (150, 160, 190), 45, 9)

    # arm + fist gripping the scythe shaft -------------------------------
    sx = cx + 66
    limb(layer, [(cx + r - 16, cy + 44), (sx - 6, cy + 62)], 26, 20,
         (255, 255, 255), (196, 204, 220), ow=3)
    scythe(layer, sx, cy - 66, cy + 168)

    mf = Image.new("L", layer.size, 0)
    pf = ImageDraw.Draw(mf)
    pf.ellipse([sx - 22, cy + 48, sx + 20, cy + 92], fill=255)
    paste_paint(layer, mf, paint_sphere((255, 255, 255), (236, 240, 248),
                                        (168, 178, 200), lx=0.35, ly=-0.5))
    for yy in (cy + 60, cy + 71, cy + 82):
        d.line([(sx + 1, yy), (sx + 17, yy + 1)], fill=(120, 128, 150), width=3)
    outline(layer, mf, 3)


# -------------------------------------------------------------- backgrounds --
def sun(img, cx, cy, r, core, mid, glow, layers=5):
    """Layered translucent discs = bloom around a lit sun."""
    for i in range(layers, 0, -1):
        b = new_layer(img.size)
        rr = r * (1 + 1.5 * i / layers)
        ImageDraw.Draw(b).ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                                  fill=glow + (int(34 * (1 - i / (layers + 1)) + 8),))
        img.alpha_composite(b.filter(ImageFilter.GaussianBlur(r * 0.55)))
    disc = new_layer(img.size)
    ImageDraw.Draw(disc).ellipse([cx - r, cy - r, cx + r, cy + r], fill=core + (255,))
    img.alpha_composite(disc.filter(ImageFilter.GaussianBlur(1.2)))
    disc = new_layer(img.size)
    ImageDraw.Draw(disc).ellipse([cx - r * 0.72, cy - r * 0.78, cx + r * 0.72, cy + r * 0.6],
                                 fill=mid + (200,))
    img.alpha_composite(disc.filter(ImageFilter.GaussianBlur(r * 0.22)))


def cloud(img, cx, cy, w, h, body, lit, shade, alpha=235):
    m = Image.new("L", img.size, 0)
    p = ImageDraw.Draw(m)
    p.ellipse([cx - w, cy - h * 0.55, cx - w * 0.15, cy + h * 0.55], fill=255)
    p.ellipse([cx - w * 0.55, cy - h, cx + w * 0.15, cy + h * 0.6], fill=255)
    p.ellipse([cx + w * 0.05, cy - h * 0.7, cx + w * 0.8, cy + h * 0.55], fill=255)
    p.ellipse([cx - w * 0.7, cy - h * 0.2, cx + w * 0.9, cy + h * 0.7], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2.2))
    tmp = new_layer(img.size)
    paste_paint(tmp, m, paint_vgrad([(0, lit), (0.45, body), (1, shade)]))
    shade_side(tmp, m, "b", 90, 10, darken(shade, .2))
    rim_light(tmp, m, 2, -3, 2.4, lighten(lit, .5), 120)
    if alpha < 255:
        a = tmp.split()[3].point(lambda v: int(v * alpha / 255))
        tmp.putalpha(a)
    img.alpha_composite(tmp)


def ground_strip(img, y, h, far, near, warm=None):
    strip = new_layer(img.size)
    layer_band = Image.new("L", img.size, 0)
    ImageDraw.Draw(layer_band).rectangle([0, y, img.width, y + h], fill=255)
    paste_paint(strip, layer_band, paint_vgrad([(0, far), (0.35, mix(far, near, .5)), (1, near)]))
    img.alpha_composite(strip)
    if warm:
        b = new_layer(img.size)
        ImageDraw.Draw(b).rectangle([0, y, img.width, y + 40], fill=warm + (60,))
        img.alpha_composite(b.filter(ImageFilter.GaussianBlur(14)))


def cast_shadow(panel, ppl, feet, light_right=True):
    """Project the people silhouette onto the ground: sheared + squashed."""
    alpha = ppl.split()[3]
    shear = -0.38 if light_right else 0.38
    inv = alpha.transform((PW, PH), Image.AFFINE,
                          (1, shear, -shear * feet,
                           0, -1.55, feet + 1.55 * feet),
                          resample=Image.BICUBIC)
    inv = inv.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.62))
    shadow = new_layer((PW, PH))
    shadow.paste((26, 22, 34), (0, 0), inv)
    panel.alpha_composite(shadow)
    # contact shadow right under the feet
    b = new_layer((PW, PH))
    ImageDraw.Draw(b).ellipse([120, feet - 12, PW - 120, feet + 26], fill=(30, 24, 34, 120))
    panel.alpha_composite(b.filter(ImageFilter.GaussianBlur(9)))


def vignette(img, strength=120):
    w, h = img.size
    v = Image.new("L", (64, 64), 0)
    pv = ImageDraw.Draw(v)
    pv.ellipse([-6, -10, 70, 70], fill=255)
    v = v.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(26))
    dark = new_layer(img.size)
    dark.paste((8, 6, 16), (0, 0), ImageChops.invert(v).point(lambda x: int(x * strength / 255)))
    img.alpha_composite(dark)


def panel(year, old):
    img = new_layer((PW, PH))
    if old:
        # ---------------- 2026: sunset ---------------------------------
        sky = paint_vgrad([(0.0, (46, 34, 84)), (0.28, (96, 54, 108)),
                           (0.55, (198, 96, 96)), (0.75, (252, 162, 108)),
                           (0.88, (255, 214, 150))])((PW, PH))
        img.paste(sky, (0, 0))
        sun(img, 700, 176, 54, (255, 246, 214), (255, 226, 168), (255, 186, 120), 6)
        for cx, cy, w, h in ((180, 56, 120, 18), (430, 40, 150, 14), (760, 74, 130, 16)):
            cloud(img, cx, cy, w, h, (232, 152, 150), (255, 206, 176), (150, 92, 128), 210)
        # far city / hills silhouette, hazy
        far = new_layer((PW, PH))
        d = ImageDraw.Draw(far)
        hill = [(0, 210)]
        for i in range(0, 21):
            x = i * PW / 20.0
            hill.append((x, 196 + 10 * math.sin(i * 0.9)))
        hill += [(PW, 210)]
        d.polygon(hill, fill=(120, 78, 116, 255))
        for i in range(9):
            bx = 60 + i * 96
            bh = 16 + 12 * abs(math.sin(i * 1.7))
            d.rectangle([bx, 200 - bh, bx + 26, 212], fill=(112, 72, 110, 255))
        far = far.filter(ImageFilter.GaussianBlur(1.6))
        img.alpha_composite(far)
        ground_strip(img, 204, PH - 204, (128, 96, 104), (58, 44, 62), (255, 176, 120))
        # sun path on the grass
        b = new_layer((PW, PH))
        ImageDraw.Draw(b).ellipse([520, 196, 900, 240], fill=(255, 196, 130, 90))
        img.alpha_composite(b.filter(ImageFilter.GaussianBlur(16)))
    else:
        # ---------------- 2013: bright day -----------------------------
        sky = paint_vgrad([(0.0, (52, 116, 196)), (0.35, (110, 172, 226)),
                           (0.72, (176, 212, 238)), (1.0, (222, 238, 246))])((PW, PH))
        img.paste(sky, (0, 0))
        sun(img, 806, 66, 42, (255, 252, 226), (255, 236, 160), (255, 240, 190), 5)
        for cx, cy, w, h in ((150, 62, 118, 22), (330, 44, 96, 17), (560, 74, 104, 15)):
            cloud(img, cx, cy, w, h, (250, 252, 255), (255, 255, 255), (190, 208, 228), 240)
        # distant hills
        far = new_layer((PW, PH))
        d = ImageDraw.Draw(far)
        d.polygon([(0, 208), (140, 182), (300, 204), (470, 186), (620, 206),
                   (800, 190), (PW, 204), (PW, 216), (0, 216)], fill=(126, 172, 150, 255))
        far = far.filter(ImageFilter.GaussianBlur(1.4))
        img.alpha_composite(far)
        ground_strip(img, 202, PH - 202, (138, 190, 108), (86, 142, 74), (255, 246, 200))
        # grass tufts with volume
        dk = ImageDraw.Draw(img)
        for i in range(26):
            gx = 20 + i * 36 + (i % 3) * 5
            gy = 216 + (i * 7) % 52
            dk.line([(gx, gy), (gx - 3, gy - 7)], fill=(70, 118, 62), width=2)
            dk.line([(gx, gy), (gx + 4, gy - 9)], fill=(158, 206, 118), width=2)

    ppl = new_layer((PW, PH))
    if old:
        ghost(ppl, 470, 86, 80)          # behind the couple
    hands = couple(ppl, old)
    if not old:
        # heart glow + shaded heart
        b = new_layer((PW, PH))
        ImageDraw.Draw(b).ellipse([hands[0] - 44, hands[1] - 108, hands[0] + 44, hands[1] - 24],
                                  fill=(255, 120, 180, 120))
        ppl.alpha_composite(b.filter(ImageFilter.GaussianBlur(12)))
        heart(ppl, hands[0], hands[1] - 62, 17, (255, 96, 150), (188, 24, 78))
    cast_shadow(img, ppl, 252, light_right=True)
    img.alpha_composite(ppl)

    d = ImageDraw.Draw(img)
    # year badge with bevel + shadow
    b = new_layer((PW, PH))
    ImageDraw.Draw(b).rounded_rectangle([20, 18, 180, 86], radius=14, fill=(0, 0, 0, 130))
    img.alpha_composite(b.filter(ImageFilter.GaussianBlur(7)))
    b = new_layer((PW, PH))
    db = ImageDraw.Draw(b)
    db.rounded_rectangle([18, 14, 178, 82], radius=14, fill=(22, 24, 52, 245),
                         outline=(255, 214, 0), width=3)
    db.line([(26, 22), (170, 22)], fill=(90, 96, 150), width=2)
    img.alpha_composite(b)
    tmp = new_layer((PW, PH))
    ImageDraw.Draw(tmp).text((98, 48), year, font=font(48), fill=(255, 236, 150), anchor="mm")
    img.alpha_composite(tmp)

    vignette(img, 110)
    return img.convert("RGB")


# ------------------------------------------------------------- text / heart --
def fit_size(d, s, max_w, start, floor=14):
    size = start
    while size > floor:
        if d.textlength(s, font=font(size)) <= max_w:
            break
        size -= 1
    return size


def heart(img, cx, cy, s, hi, lo, ow=3):
    """Glossy 3D heart: gradient body, rim light, specular blob."""
    pts = []
    for i in range(0, 360, 4):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 16.0, cy - y * s / 16.0))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    paste_paint(img, m, paint_sphere(lighten(hi, .35), hi, lo, lx=0.3, ly=-0.3))
    shade_side(img, m, "r", 110, 6)
    rim_light(img, m, 3, -3, 1.8, (255, 255, 255), 180)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - s * 0.55, cy - s * 0.72, cx - s * 0.05, cy - s * 0.28],
              fill=(255, 255, 255, 200))
    outline(img, m, ow)


def grad_text(img, xy, s, size, stops, anchor="mm", stroke_width=6,
              stroke_fill=BLACK, shadow=True):
    if shadow:
        sh = new_layer(img.size)
        ImageDraw.Draw(sh).text((xy[0] + 3, xy[1] + 5), s, font=font(size), fill=(0, 0, 0, 190),
                                stroke_width=stroke_width, stroke_fill=(0, 0, 0, 190),
                                anchor=anchor)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, s, font=font(size), fill=255,
                              stroke_width=stroke_width, stroke_fill=255, anchor=anchor)
    bb = mask.getbbox()
    if not bb:
        return
    body = mask.crop(bb)
    inner = Image.new("L", img.size, 0)
    ImageDraw.Draw(inner).text(xy, s, font=font(size), fill=255, anchor=anchor)
    inner = inner.crop(bb).filter(ImageFilter.GaussianBlur(0.5))
    paint = paint_vgrad(stops)((bb[2] - bb[0], bb[3] - bb[1])).convert("RGBA")
    paint.putalpha(inner)
    edge = ImageChops.subtract(body, inner).filter(ImageFilter.GaussianBlur(0.6))
    img.paste(stroke_fill, (bb[0], bb[1]), edge)
    img.paste(paint, (bb[0], bb[1]), paint)


# ------------------------------------------------------------------- main ----
def main():
    img = new_layer((W, H))
    img.paste(paint_vgrad([(0.0, (30, 36, 78)), (0.45, (18, 22, 54)),
                           (1.0, (10, 12, 30))])((W, H)), (0, 0))
    glow = new_layer((W, H))
    ImageDraw.Draw(glow).ellipse([-160, -300, W + 160, 260], fill=(70, 96, 170, 70))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))

    # headline ---------------------------------------------------------
    l1 = "Finally... after 13 years of waiting..."
    l2 = "GTA VI IS FINALLY OUT!"
    d = ImageDraw.Draw(img)
    s1 = fit_size(d, l1, 940, 44)
    s2 = fit_size(d, l2, 940, 84)
    grad_text(img, (W // 2, 48), l1, s1,
              [(0, (255, 255, 255)), (0.55, (226, 232, 246)), (1, (170, 184, 214))],
              stroke_width=5)
    grad_text(img, (W // 2, 122), l2, s2,
              [(0, (255, 248, 190)), (0.42, (255, 214, 0)), (1, (232, 146, 0))],
              stroke_width=7)

    # panels -----------------------------------------------------------
    for (label, old), y in zip((("2013", False), ("2026", True)), PANEL_Y):
        p = panel(label, old)
        mask = Image.new("L", (PW, PH), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=PANEL_R, fill=255)
        # drop shadow
        sh = new_layer((W, H))
        sh.paste((0, 0, 0), (PX, y + 6), mask.point(lambda v: int(v * 0.55)))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        img.paste(p, (PX, y), mask)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([PX, y, PX + PW - 1, y + PH - 1], radius=PANEL_R,
                            outline=(196, 148, 34), width=5)
        d.rounded_rectangle([PX + 2, y + 2, PX + PW - 3, y + PH - 3], radius=PANEL_R - 2,
                            outline=(255, 226, 130), width=1)

    # footer -----------------------------------------------------------
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([26, 736, W - 26, 740], radius=2, fill=(72, 80, 126))
    lines = ("While you waited,", "my AI made money", "on make.fun")
    for i, s in enumerate(lines):
        size = fit_size(d, s, 900, 52)
        grad_text(img, (W // 2, 772 + i * 56), s, size,
                  [(0, (255, 255, 255)), (1, (206, 214, 236))], stroke_width=4)

    img = img.convert("RGB")
    vignette(img.convert("RGBA"), 0)          # no-op keeps signature stable
    img.save("meme.png")
    print("meme.png written", img.size)


if __name__ == "__main__":
    main()



