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
          fill=darken(skin, .55), width=1)
    outline(layer, m, ow)


def hair_strands(layer, mask, cx, top, span, h, hair, n=11, lean=-0.16):
    """Draw individual hair strands (curved 1 px strokes) inside `mask`.

    A single flat blob is the other half of the sticker look: hair reads as
    hair when you can see strands catching the light and strands falling into
    shadow, so each clump gets alternating light/dark curves.
    """
    s = new_layer(layer.size)
    ds = ImageDraw.Draw(s)
    for i in range(n):
        t = i / max(1, n - 1)
        x0 = cx - span + 2 * span * t
        spread = (x0 - cx)
        p0 = (cx + spread * 0.35, top + 1)
        p1 = (cx + spread * (1.0 + lean), top + h * 0.5)
        p2 = (cx + spread * (1.05 + lean * 1.6), top + h * (0.86 + 0.14 * (i % 2)))
        pts = [bez(p0, p1, p2, k / 10.0) for k in range(11)]
        if i % 4 == 1:
            col = lighten(hair, .5)
        elif i % 4 == 3:
            col = darken(hair, .28)
        else:
            col = darken(hair, .5)
        ds.line(pts, fill=col, width=1)
    s.putalpha(ImageChops.multiply(s.split()[3], mask))
    layer.alpha_composite(s)


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
                    fill=darken(shirt, .38), width=1)
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
                             fill=(58, 44, 38), outline=EDGE_SOFT, width=1)
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
        soft_blob(layer, [cx - 8, hcy + 40, cx + 26, hcy + 74], hair, 90, 8)
        hair_strands(layer, mh, cx, hcy - 2, hrx + 7, 68, hair, n=13, lean=-0.05)
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

    # hair on top: strands, not a blob
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
    hair_strands(layer, mh, cx, top + 1, hrx + 1, 36, hair, n=15, lean=-0.2)
    rim_light(layer, mh, 3, 2, 1.6, amount=190)
    outline(layer, mh, 3)

    # ---- face ----------------------------------------------------------
    # Realistic proportions: eye sockets sit a hair above mid-skull, the eye
    # opening is a narrow almond (not a dot, not an anime saucer), and every
    # feature is placed with a soft shadow instead of a hard stroke.
    ey = hcy - 2
    iris = (92, 62, 40) if not old else (126, 116, 104)
    brow_col = mix(hair, darken(skin, .55), 0.25)
    for ex in (-9, 9):
        # socket recess + upper-lid shadow give the eye a real head around it
        soft_blob(layer, [cx + ex - 9, ey - 8, cx + ex + 9, ey + 5], darken(skin, .58), 55, 5)
        # sclera: almond, slightly narrower than tall
        me = Image.new("L", layer.size, 0)
        ImageDraw.Draw(me).ellipse([cx + ex - 6, ey - 4, cx + ex + 6, ey + 4], fill=255)
        layer.paste(mix((246, 242, 236), darken(skin, .1), .25), (0, 0), me)
        di = ImageDraw.Draw(layer)
        # eyeball shading top+bottom so the white is not flat paper
        soft_blob(layer, [cx + ex - 6, ey - 5, cx + ex + 6, ey - 1], darken(skin, .5), 60, 2)
        di.ellipse([cx + ex - 3, ey - 3, cx + ex + 2, ey + 3], fill=iris)
        di.ellipse([cx + ex - 2, ey - 2, cx + ex + 1, ey + 1], fill=darken(iris, .7))
        di.point((cx + ex - 1, ey - 2), fill=(252, 250, 246))
        # upper lid line (1 px) + lower lash line, both tapered
        di.arc([cx + ex - 6, ey - 5, cx + ex + 6, ey + 4], 186, 354,
               fill=darken(skin, .62), width=1)
        di.arc([cx + ex - 6, ey - 3, cx + ex + 6, ey + 5], 8, 172,
               fill=darken(skin, .28), width=1)
        # crease above the lid
        di.arc([cx + ex - 6, ey - 8, cx + ex + 6, ey + 1], 200, 340,
               fill=darken(skin, .3), width=1)
    d = ImageDraw.Draw(layer)
    # brows: natural arch, thin at the outer end
    for sgn in (-1, 1):
        x0, x1 = cx + sgn * 15, cx + sgn * 4
        d.line([(x0, ey - 11), (cx + sgn * 10, ey - 14), (x1, ey - 13)],
               fill=brow_col, width=2 if not old else 1)
        d.line([(x0, ey - 10), (cx + sgn * 9, ey - 13)],
               fill=lighten(brow_col, .18), width=1)

    # nose: small bridge highlight, nostril shadow, gentle tip
    soft_blob(layer, [cx - 2, hcy + 2, cx + 5, hcy + 11], darken(skin, .42), 62, 3)
    d.line([(cx + 1, hcy + 1), (cx + 2, hcy + 8)], fill=lighten(skin, .3), width=1)
    d.arc([cx - 4, hcy + 6, cx + 5, hcy + 13], 15, 145, fill=darken(skin, .46), width=1)
    d.point((cx - 2, hcy + 11), fill=darken(skin, .55))
    d.point((cx + 3, hcy + 11), fill=darken(skin, .5))

    # mouth: cupid's bow upper lip, lit lower lip, soft corner shadows
    my = hcy + 18
    lip = mix((150, 88, 82), darken(skin, .25), .45) if not old else darken(skin, .35)
    d.line([(cx - 9, my - 1), (cx - 4, my - 3), (cx, my - 1),
            (cx + 4, my - 3), (cx + 9, my - 1)], fill=lip, width=2 if not old else 1)
    if old:
        d.arc([cx - 9, my - 3, cx + 9, my + 7], 20, 160, fill=darken(skin, .5), width=1)
    else:
        d.arc([cx - 9, my - 2, cx + 9, my + 9], 22, 158, fill=darken(lip, .3), width=1)
        soft_blob(layer, [cx - 6, my + 2, cx + 6, my + 8], lighten(skin, .45), 70, 3)
    d.point((cx - 9, my - 1), fill=darken(skin, .45))
    d.point((cx + 9, my - 1), fill=darken(skin, .45))

    # cheeks / specular: lit cheekbone, soft blush, jaw shadow
    soft_blob(layer, [cx + 4, hcy + 4, cx + 20, hcy + 18], lighten(skin, .5), 55, 7)
    soft_blob(layer, [cx - 19, hcy + 5, cx - 5, hcy + 18], (168, 76, 74), 34, 7)
    soft_blob(layer, [cx + 5, hcy + 6, cx + 17, hcy + 17], (176, 92, 84), 24, 6)
    soft_blob(layer, [cx - 14, hcy + 20, cx + 16, hcy + 30], darken(skin, .5), 40, 6)

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
        hair_strands(layer, mb, cx, hcy + 16, 20, 18, hair, n=11, lean=-0.02)
        outline(layer, mb, 2)

    if cfg.get("glasses"):
        d.ellipse([cx - 19, ey - 10, cx - 3, ey + 6], outline=(52, 48, 52), width=1)
        d.ellipse([cx + 3, ey - 10, cx + 19, ey + 6], outline=(52, 48, 52), width=1)
        d.line([(cx - 3, ey - 3), (cx + 3, ey - 3)], fill=(52, 48, 52), width=1)
        d.line([(cx - 19, ey - 4), (cx - hrx, ey - 6)], fill=(52, 48, 52), width=1)
        d.line([(cx + 19, ey - 4), (cx + hrx, ey - 6)], fill=(52, 48, 52), width=1)
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


def wall_poster(img, x0, y0, x1, y1):
    """Framed picture on the back wall: matt board, sunset art, glass sheen."""
    drop = new_layer(img.size)
    ImageDraw.Draw(drop).rectangle([x0 + 4, y0 + 6, x1 + 4, y1 + 6], fill=(30, 22, 18, 120))
    img.alpha_composite(drop.filter(ImageFilter.GaussianBlur(6)))
    # wood frame
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rectangle([x0, y0, x1, y1], fill=255)
    paste_paint(img, m, paint_hgrad([(0, (96, 62, 40)), (0.42, (156, 112, 66)),
                                     (1, (104, 68, 44))]))
    rim_light(img, m, -2, -2, 1.4, (255, 226, 176), 110)
    # matt + art
    inner = [x0 + 7, y0 + 7, x1 - 7, y1 - 7]
    m2 = Image.new("L", img.size, 0)
    ImageDraw.Draw(m2).rectangle(inner, fill=255)
    img.paste((238, 232, 218), (0, 0), m2)
    art = [inner[0] + 6, inner[1] + 6, inner[2] - 6, inner[3] - 6]
    m3 = Image.new("L", img.size, 0)
    ImageDraw.Draw(m3).rectangle(art, fill=255)
    paste_paint(img, m3, paint_vgrad([(0.0, (86, 60, 132)), (0.4, (214, 106, 104)),
                                      (0.72, (252, 170, 112)), (1.0, (255, 214, 154))]))
    a = ImageDraw.Draw(img)
    a.ellipse([art[2] - 26, art[1] + 10, art[2] - 6, art[1] + 30], fill=(255, 246, 206))
    a.polygon([(art[0], art[3] - 14), (art[0] + 16, art[3] - 26), (art[0] + 30, art[3] - 14)],
              fill=(88, 54, 78))
    a.polygon([(art[2] - 26, art[3] - 14), (art[2] - 12, art[3] - 22),
               (art[2], art[3] - 12)], fill=(96, 58, 84))
    # glass sheen across the matt + art
    sheen = new_layer(img.size)
    ImageDraw.Draw(sheen).polygon([(x0 + 10, y1 - 10), (x0 + 34, y0 + 10),
                                   (x0 + 46, y0 + 10), (x0 + 22, y1 - 10)],
                                  fill=(255, 255, 255, 42))
    sheen.putalpha(ImageChops.multiply(sheen.split()[3], m))
    img.alpha_composite(sheen)
    rim_light(img, m, 1, 1, 1.0, (255, 240, 214), 120)
    outline(img, m, 1)


def bookshelf(img, x0, y0, x1, y1):
    """Filled bookcase: wood carcass, boards, multicoloured spines, shadows."""
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rectangle([x0, y0, x1, y1], fill=255)
    paste_paint(img, m, paint_hgrad([(0, (74, 46, 30)), (0.4, (132, 88, 56)),
                                     (0.72, (156, 108, 68)), (1, (86, 54, 36))]))
    d = ImageDraw.Draw(img)
    # recessed back panel
    back = [x0 + 9, y0 + 9, x1 - 9, y1 - 9]
    img.paste((54, 36, 26), (back[0], back[1], back[2], back[3]))
    rows = 3
    rh = (back[3] - back[1]) // rows
    spines = [(148, 62, 56), (60, 92, 132), (198, 158, 72), (86, 118, 78),
              (128, 74, 116), (196, 108, 62), (72, 84, 96), (166, 96, 88)]
    for r in range(rows):
        by = back[1] + r * rh
        # books on this shelf

        bx = back[0] + 3
        i = 0
        while bx < back[2] - 5:
            bw = 5 + int(4 * abs(math.sin(r * 3.1 + i * 1.7)))
            bh = rh - 14 - int(7 * abs(math.sin(i * 2.3 + r)))
            if bx + bw > back[2] - 4:
                break
            col = spines[int(abs(math.sin(i * 5.3 + r * 2.1)) * len(spines)) % len(spines)]
            d.rectangle([bx, by + rh - 8 - bh, bx + bw, by + rh - 8], fill=col)
            d.line([(bx, by + rh - 8 - bh), (bx + bw - 1, by + rh - 8 - bh)],
                   fill=lighten(col, .3), width=1)
            d.line([(bx + bw - 1, by + rh - 8 - bh), (bx + bw - 1, by + rh - 8)],
                   fill=darken(col, .35), width=1)
            bx += bw + 1
            i += 1
        if r == 0:                                   # a small plant on top shelf
            pot_plant(img, back[2] - 20, by + rh - 9, 13, (74, 126, 74))
        # board
        d.rectangle([back[0] - 2, by + rh - 8, back[2] + 2, by + rh - 2], fill=(146, 100, 62))
        d.line([(back[0] - 2, by + rh - 8), (back[2] + 2, by + rh - 8)],
               fill=(188, 138, 90), width=1)
        # shadow under each board
        sh = new_layer(img.size)
        ImageDraw.Draw(sh).rectangle([back[0], by + rh - 2, back[2], by + rh + 6],
                                     fill=(20, 12, 8, 110))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3)))
    outline(img, m, 1)


def pot_plant(img, cx, base_y, s, leaf, pot=(150, 92, 74)):
    """Small potted plant: tapered pot, rim, layered leaves."""
    m = Image.new("L", img.size, 0)
    p = ImageDraw.Draw(m)
    p.polygon([(cx - s * 0.62, base_y - s * 0.9), (cx + s * 0.62, base_y - s * 0.9),
               (cx + s * 0.42, base_y), (cx - s * 0.42, base_y)], fill=255)
    paste_paint(img, m, paint_hgrad([(0, darken(pot, .35)), (0.45, pot),
                                     (1, lighten(pot, .3))]))
    p2 = ImageDraw.Draw(img)
    p2.rectangle([cx - s * 0.66, base_y - s * 1.04, cx + s * 0.66, base_y - s * 0.86],
                 fill=lighten(pot, .12))
    # leaves: lens shapes fanning out of the pot
    for i in range(7):
        ang = math.radians(-150 + i * 20)
        length = s * (1.15 + 0.45 * math.sin(i * 1.9))
        tipx = cx + math.cos(ang) * length * 0.85
        tipy = base_y - s * 0.95 + math.sin(ang) * length
        mx = (cx + tipx) / 2 + math.cos(ang + 1.4) * s * 0.28
        my = (base_y - s * 0.95 + tipy) / 2 + math.sin(ang + 1.4) * s * 0.28
        pts = [bez((cx, base_y - s * 0.95), (mx, my), (tipx, tipy), k / 8.0) for k in range(9)]
        up = [(px + 2, py - 2) for px, py in pts]
        poly = pts + up[::-1]
        col = mix(leaf, (255, 240, 170), 0.22 if i % 3 == 0 else 0.0)
        col = darken(col, .28 if i % 2 else 0.0)
        ImageDraw.Draw(img).polygon(poly, fill=col)
    rim_light(img, m, 2, 2, 1.2, (255, 240, 210), 90)


def room_2013(img):
    """Indoor back wall + wooden floor, poster left, bookcase right."""
    wall = new_layer(img.size)
    band = Image.new("L", img.size, 0)
    ImageDraw.Draw(band).rectangle([0, 0, PW, 250], fill=255)
    paste_paint(wall, band, paint_vgrad([(0.0, (232, 212, 184)), (0.55, (214, 190, 162)),
                                         (1.0, (188, 162, 134))]))
    img.alpha_composite(wall)
    # warm daylight falling from the top right + faint wallpaper stripes
    warm = new_layer(img.size)
    ImageDraw.Draw(warm).ellipse([520, -220, 1180, 300], fill=(255, 244, 212, 90))
    img.alpha_composite(warm.filter(ImageFilter.GaussianBlur(70)))
    st = ImageDraw.Draw(img)
    for x in range(0, PW, 34):
        st.line([(x, 0), (x, 246)], fill=(204, 182, 156), width=1)
    # corner shadow where wall meets floor
    sh = new_layer(img.size)
    ImageDraw.Draw(sh).rectangle([0, 214, PW, 252], fill=(60, 40, 30, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    # baseboard + wooden floor
    d = ImageDraw.Draw(img)
    d.rectangle([0, 244, PW, 254], fill=(226, 214, 196))
    d.line([(0, 244), (PW, 244)], fill=(150, 130, 108), width=1)
    fl = new_layer(img.size)
    fband = Image.new("L", img.size, 0)
    ImageDraw.Draw(fband).rectangle([0, 252, PW, PH], fill=255)
    paste_paint(fl, fband, paint_vgrad([(0, (152, 100, 62)), (1, (104, 64, 40))]))
    img.alpha_composite(fl)
    for i in range(9):                                  # plank seams
        y = 256 + i * 9
        d.line([(0, y), (PW, y)], fill=darken((132, 86, 54), .3), width=1)
    for i in range(14):
        x = 8 + i * 72
        d.line([(x, 252), (x - 10, PH)], fill=(120, 78, 48), width=1)
    wall_poster(img, 196, 26, 314, 122)
    bookshelf(img, 786, 30, 930, 246)


def skyline(img, base_y):
    """Three depth layers of buildings with lit windows, antennas, haze."""
    far = new_layer(img.size)
    df = ImageDraw.Draw(far)
    for i in range(16):
        bx = -20 + i * 62
        bh = 26 + int(30 * abs(math.sin(i * 2.7)))
        df.rectangle([bx, base_y - bh, bx + 46, base_y], fill=(150, 108, 138, 255))
        df.rectangle([bx + 20, base_y - bh - 18, bx + 24, base_y - bh],
                     fill=(150, 108, 138, 255))
    img.alpha_composite(far.filter(ImageFilter.GaussianBlur(2.4)))
    mid = new_layer(img.size)
    dm = ImageDraw.Draw(mid)
    for i in range(11):
        bx = -10 + i * 92
        bh = 40 + int(46 * abs(math.sin(i * 1.7 + 1)))
        dm.rectangle([bx, base_y - bh, bx + 62, base_y], fill=(104, 76, 112, 255))
        dm.polygon([(bx, base_y - bh), (bx + 31, base_y - bh - 16),
                    (bx + 62, base_y - bh)], fill=(104, 76, 112, 255))
        for r in range(bh // 12):
            for c in range(4):
                wx = bx + 6 + c * 14
                wy = base_y - bh + 8 + r * 12
                if 0.55 < abs(math.sin(i * 3.1 + r * 1.3 + c * 2.2)):
                    dm.rectangle([wx, wy, wx + 6, wy + 6], fill=(255, 214, 138, 255))
    img.alpha_composite(mid.filter(ImageFilter.GaussianBlur(0.8)))
    haze = new_layer(img.size)
    ImageDraw.Draw(haze).rectangle([0, base_y - 70, PW, base_y + 6],
                                   fill=(238, 150, 130, 60))
    img.alpha_composite(haze.filter(ImageFilter.GaussianBlur(20)))


def foreground_plants(img):
    """Foreground dressing for 2026: street planter, tall pot, two shrubs."""
    pot_plant(img, 74, 268, 30, (70, 104, 78), (120, 74, 60))
    pot_plant(img, 902, 272, 26, (84, 118, 86), (134, 86, 66))
    for cx, s, col in ((164, 20, (66, 98, 70)), (828, 16, (78, 110, 78))):
        m = Image.new("L", img.size, 0)
        p = ImageDraw.Draw(m)
        for i in range(5):
            p.ellipse([cx - s + i * s * 0.42, 250 - s * (0.7 + 0.3 * (i % 2)),
                       cx - s * 0.2 + i * s * 0.42, 264], fill=255)
        paste_paint(img, m, paint_sphere(lighten(col, .4), col, darken(col, .45),
                                         lx=0.3, ly=-0.5))
        rim_light(img, m, 2, 2, 1.4, (255, 226, 180), 110)


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
        # far city skyline: layered, lit windows, hazy at the base
        skyline(img, 202)
        ground_strip(img, 204, PH - 204, (128, 96, 104), (56, 42, 60), (255, 176, 120))
        # sun path on the grass
        b = new_layer((PW, PH))
        ImageDraw.Draw(b).ellipse([520, 196, 900, 240], fill=(255, 196, 130, 90))
        img.alpha_composite(b.filter(ImageFilter.GaussianBlur(16)))
        foreground_plants(img)
    else:
        # ---------------- 2013: living room, daylight ------------------
        room_2013(img)

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



