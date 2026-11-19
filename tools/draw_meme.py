#!/usr/bin/env python3
"""Draw the gta6-meme-x-01 meme: "13 TAHUN" — 2013 kid playing GTA V vs
2026 the same guy (older, bearded) finally playing GTA VI, with the
make.fun ghost beside him holding its magenta coin. Deterministic, PIL only."""
import math
from PIL import Image, ImageDraw, ImageFont

W = H = 1024
SPLIT = 500          # top/bottom half boundary
BAND_Y0, BAND_Y1 = 468, 560   # middle "13 TAHUN" band

MAGENTA = (230, 0, 126)
MAGENTA_LT = (255, 77, 168)
BLACK = (10, 10, 15)
WHITE = (255, 255, 255)
YELLOW = (255, 230, 0)
SKIN_Y = (242, 193, 133)
SKIN_O = (232, 176, 126)
GREY = (158, 158, 158)
SHIRT = (30, 136, 229)
NAVY = (16, 20, 40)

F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(sz):
    return ImageFont.truetype(F, sz)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def text(d, xy, s, f, fill, stroke=0, sc=None, anchor="la"):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke,
           stroke_fill=sc or BLACK, anchor=anchor)


def vgrad(img, y0, y1, c0, c1):
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        d.line([(0, y), (W, y)], fill=lerp(c0, c1, (y - y0) / max(1, y1 - y0 - 1)))


def sparkle4(d, cx, cy, r, fill):
    k = r * 0.26
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
               (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=fill)


def star5(cx, cy, R, r, rot=-90):
    pts = []
    for i in range(10):
        a = math.radians(rot + i * 36)
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return pts


def person(d, hx, hy, older, skin):
    """Simple bold person. Head centre (hx,hy), r=62. Holds a phone up-right."""
    r = 62
    # body / shirt
    d.rounded_rectangle([hx - 88, hy + 68, hx + 88, hy + 218], radius=34,
                        fill=SHIRT, outline=BLACK, width=8)
    # head
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=skin, outline=BLACK, width=8)
    # hair cap (grey when older)
    hc = GREY if older else BLACK
    d.pieslice([hx - r - 5, hy - r - 8, hx + r + 5, hy + r - 4], 180, 360, fill=hc)
    d.rectangle([hx - r - 5, hy - 6, hx + r + 5, hy + 2], fill=hc)
    # eyes
    d.ellipse([hx - 28, hy - 12, hx - 12, hy + 4], fill=BLACK)
    d.ellipse([hx + 12, hy - 12, hx + 28, hy + 4], fill=BLACK)
    if older:
        # beard: grey lower half of face
        d.pieslice([hx - 56, hy - 6, hx + 56, hy + 66], 0, 180, fill=GREY)
        d.arc([hx - 56, hy - 6, hx + 56, hy + 66], 0, 180, fill=BLACK, width=6)
        # glasses
        d.ellipse([hx - 40, hy - 16, hx - 6, hy + 12], outline=BLACK, width=6)
        d.ellipse([hx + 6, hy - 16, hx + 40, hy + 12], outline=BLACK, width=6)
        d.line([hx - 6, hy - 2, hx + 6, hy - 2], fill=BLACK, width=6)
        # wrinkle lines
        d.line([hx - 34, hy - 26, hx - 14, hy - 24], fill=BLACK, width=4)
        d.line([hx + 14, hy - 24, hx + 34, hy - 26], fill=BLACK, width=4)
    else:
        # young smile
        d.arc([hx - 24, hy + 8, hx + 24, hy + 40], 20, 160, fill=BLACK, width=7)
    # arm + phone (phone screen shows V or VI)
    d.line([hx + 60, hy + 120, hx + 108, hy + 100], fill=BLACK, width=30)
    d.line([hx + 60, hy + 120, hx + 108, hy + 100], fill=skin, width=18)
    d.rounded_rectangle([hx + 92, hy + 20, hx + 152, hy + 118], radius=10,
                        fill=BLACK, outline=BLACK)
    d.rounded_rectangle([hx + 99, hy + 27, hx + 145, hy + 100], radius=6,
                        fill=(MAGENTA if older else YELLOW))
    text(d, (hx + 122, hy + 40), ("VI" if older else "V"),
         font(46 if older else 52), WHITE if older else BLACK, anchor="mm")
    d.ellipse([hx + 96, hy + 100, hx + 128, hy + 132], fill=skin, outline=BLACK, width=6)


def ghost(d, cx, cyh):
    """make.fun ghost: white body, thick black outline, sparkle eyes,
    round hand, holding magenta coin with white star."""
    R, o = 82, 11          # head radius, outline
    yb = cyh + 132         # bottom of straight body
    rb = 27                # bump radius
    # black silhouette (expanded) then white on top
    d.ellipse([cx - R - o, cyh - R - o, cx + R + o, cyh + R + o], fill=BLACK)
    d.rectangle([cx - R - o, cyh, cx + R + o, yb + o], fill=BLACK)
    for i in range(3):
        bx = cx - R + rb + i * (2 * R // 3) + (R // 3 - rb)
        d.ellipse([bx - rb - o, yb - rb - o, bx + rb + o, yb + rb + o], fill=BLACK)
    d.ellipse([cx - R, cyh - R, cx + R, cyh + R], fill=WHITE)
    d.rectangle([cx - R, cyh, cx + R, yb], fill=WHITE)
    for i in range(3):
        bx = cx - R + rb + i * (2 * R // 3) + (R // 3 - rb)
        d.ellipse([bx - rb, yb - rb, bx + rb, yb + rb], fill=WHITE)
    # face: black four-pointed sparkle eyes + smile
    sparkle4(d, cx - 28, cyh - 8, 15, BLACK)
    sparkle4(d, cx + 28, cyh - 8, 15, BLACK)
    d.arc([cx - 18, cyh + 16, cx + 18, cyh + 48], 15, 165, fill=BLACK, width=6)
    # left round hand
    d.line([cx - R + 8, cyh + 60, cx - R - 26, cyh + 88], fill=BLACK, width=20)
    d.line([cx - R + 8, cyh + 60, cx - R - 26, cyh + 88], fill=WHITE, width=10)
    d.ellipse([cx - R - 44, cyh + 70, cx - R - 8, cyh + 106], fill=WHITE, outline=BLACK, width=7)
    # right arm holding coin
    kx, ky = cx + R + 58, cyh + 92
    d.line([cx + R - 8, cyh + 58, kx - 26, ky - 6], fill=BLACK, width=22)
    d.line([cx + R - 8, cyh + 58, kx - 26, ky - 6], fill=WHITE, width=12)
    # magenta coin with white star, on magenta disc
    d.ellipse([kx - 52, ky - 52, kx + 52, ky + 52], fill=MAGENTA, outline=BLACK, width=8)
    d.ellipse([kx - 42, ky - 42, kx + 42, ky + 42], fill=MAGENTA_LT, outline=BLACK, width=4)
    d.polygon(star5(kx, ky, 26, 11), fill=WHITE, outline=BLACK)
    d.line([kx - 52, ky - 18, kx - 30, ky - 34], fill=WHITE, width=6)
    # round little hand over the coin edge
    d.ellipse([kx - 40, ky - 6, kx - 6, ky + 28], fill=WHITE, outline=BLACK, width=7)


def main():
    img = Image.new("RGB", (W, H))
    vgrad(img, 0, SPLIT, (255, 179, 0), (255, 94, 32))       # 2013 sunset
    vgrad(img, SPLIT, H, NAVY, (38, 52, 100))                # 2026 night

    d = ImageDraw.Draw(img)

    # --- top half: 2013 ---
    text(d, (40, 18), "2013", font(124), WHITE, stroke=9)
    text(d, (44, 158), "GTA V", font(66), YELLOW, stroke=7)
    person(d, 770, 250, older=False, skin=SKIN_Y)

    # --- middle band: 13 TAHUN ---
    d.rectangle([0, BAND_Y0, W, BAND_Y1], fill=BLACK)
    text(d, (W // 2, (BAND_Y0 + BAND_Y1) // 2 + 4), "13 TAHUN",
         font(92), WHITE, stroke=6, sc=MAGENTA, anchor="mm")

    # --- bottom half: 2026 ---
    text(d, (40, 588), "2026", font(124), WHITE, stroke=9)
    text(d, (44, 726), "GTA VI", font(66), MAGENTA_LT, stroke=7)
    person(d, 505, 780, older=True, skin=SKIN_O)

    # speech bubble (ghost's line)
    d.rounded_rectangle([618, 588, 1004, 726], radius=26, fill=WHITE, outline=BLACK, width=7)
    d.polygon([(846, 724), (906, 724), (862, 786)], fill=WHITE, outline=BLACK)
    d.line([846, 726, 862, 784], fill=BLACK, width=7)
    d.line([906, 726, 862, 784], fill=BLACK, width=7)
    text(d, (811, 606), "sambil nunggu,", font(40), NAVY, anchor="mm")
    text(d, (811, 652), "aku cari duit", font(40), NAVY, anchor="mm")
    text(d, (811, 698), "di make.fun", font(40), MAGENTA, anchor="mm")

    ghost(d, 858, 812)

    img.save("meme.png")
    print("meme.png written", img.size)


if __name__ == "__main__":
    main()
