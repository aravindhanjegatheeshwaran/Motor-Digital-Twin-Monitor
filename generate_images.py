"""
generate_images.py
Creates all PNG assets required by the Motor Digital Twin Monitor dashboard.
Run once before launching main.py:
    python generate_images.py
"""

import os
import math
import random
from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = "images"
SCALE      = 3   # draw at 3x, then downscale for crisp edges

os.makedirs(IMAGES_DIR, exist_ok=True)

def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "arialbd.ttf", "ariblk.ttf", "Arial Bold.ttf",
        "calibrib.ttf", "verdanab.ttf",
        "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def _rgba(h: str, a: int = 255) -> tuple:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a

def _lerp(c1: str, c2: str, t: float) -> tuple:
    r1, g1, b1, _ = _rgba(c1)
    r2, g2, b2, _ = _rgba(c2)
    return (int(r1 + (r2 - r1) * t), int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t), 255)

def _gradient(w: int, h: int, top: str, bot: str) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    px  = img.load()
    for y in range(h):
        c = _lerp(top, bot, y / h)
        for x in range(w):
            px[x, y] = c
    return img

def _border(draw, w, h, colour, bw, radius):
    half = bw // 2
    draw.rounded_rectangle([half, half, w - half, h - half],
                            radius=radius, outline=colour, width=bw)

def _center_text(draw, text, y, w, font, colour="#ffffff"):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (w - (bbox[2] - bbox[0])) // 2
    draw.text((x, y - bbox[1]), text, fill=colour, font=font)

def _save(img, filename, target):
    final = img.resize(target, Image.LANCZOS)
    path  = os.path.join(IMAGES_DIR, filename)
    final.save(path)
    print(f"  OK  {filename:<30}  ({target[0]}x{target[1]} px)")

def _warning_badge(draw, cx, cy, r):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 fill="#c0392b", outline="#ffffff", width=3)
    bw = max(4, r // 4)
    bh = int(r * 1.0)
    draw.rectangle([cx - bw, cy - bh, cx + bw, cy - bh // 5], fill="#ffffff")
    dot = max(3, r // 5)
    draw.ellipse([cx - dot, cy + bh // 4, cx + dot, cy + bh + dot], fill="#ffffff")

def _checkmark(draw, cx, cy, size, colour, lw):
    pts = [
        (cx - size, cy),
        (cx - size // 3, cy + int(size * 0.7)),
        (cx + size, cy - int(size * 0.7)),
    ]
    draw.line(pts, fill=colour, width=lw)

def _gear(draw, cx, cy, r_out, r_mid, r_hole, teeth, fill, stroke, sw):
    pts = []
    for i in range(teeth * 4):
        angle = math.radians(i * 360 / (teeth * 4) - 90)
        r     = r_out if i % 4 in (1, 2) else r_mid
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill=fill, outline=stroke)
    draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
                 outline=stroke, width=sw)
    draw.ellipse([cx - r_hole, cy - r_hole, cx + r_hole, cy + r_hole],
                 fill=stroke, outline=stroke)
    inner_hole = max(4, r_hole // 2)
    draw.ellipse([cx - inner_hole, cy - inner_hole, cx + inner_hole, cy + inner_hole],
                 fill="#0d1117")

def _thermometer(draw, cx, top, tube_h, tube_w, fill_frac, merc):
    bulb_r   = tube_w + 7
    tube_bot = top + tube_h
    bulb_cy  = tube_bot + bulb_r - 5
    draw.rounded_rectangle([cx - tube_w, top, cx + tube_w, tube_bot + tube_w],
                            radius=tube_w, outline="#cce5ff", width=4)
    fill_top = tube_bot - int(tube_h * fill_frac)
    if fill_top < tube_bot:
        draw.rounded_rectangle([cx - tube_w + 5, fill_top,
                                cx + tube_w - 5, tube_bot + tube_w - 5],
                               radius=tube_w - 5, fill=merc)
    draw.ellipse([cx - bulb_r, bulb_cy - bulb_r, cx + bulb_r, bulb_cy + bulb_r],
                 fill=merc, outline="#cce5ff", width=4)

def _lightning(draw, cx, cy, size, fill, stroke):
    s   = size
    pts = [
        (cx + s * 0.15, cy - s),
        (cx - s * 0.25, cy - s * 0.05),
        (cx + s * 0.08, cy - s * 0.05),
        (cx - s * 0.15, cy + s),
        (cx + s * 0.25, cy + s * 0.05),
        (cx - s * 0.08, cy + s * 0.05),
    ]
    draw.polygon([(int(x), int(y)) for x, y in pts], fill=fill, outline=stroke)

def _spark(draw, cx, cy, length, angle_deg, colour):
    a  = math.radians(angle_deg)
    x1 = cx + int(length * 0.35 * math.cos(a))
    y1 = cy + int(length * 0.35 * math.sin(a))
    x2 = cx + int(length * math.cos(a))
    y2 = cy + int(length * math.sin(a))
    draw.line([(x1, y1), (x2, y2)], fill=colour, width=4)

def _sine_wave(draw, cx, cy, width, amplitude, cycles, colour, lw):
    steps = 80
    pts = [(cx - width // 2 + int(i / steps * width),
            cy + int(amplitude * math.sin(i / steps * cycles * 2 * math.pi)))
           for i in range(steps + 1)]
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=colour, width=lw)

_T_SYS = (160, 160)

def make_sys_normal():
    W, H = _T_SYS[0] * SCALE, _T_SYS[1] * SCALE
    img  = _gradient(W, H, "#145a32", "#239b56")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 20
    _gear(draw, cx, cy, r_out=120, r_mid=84, r_hole=34, teeth=8,
          fill="#d5f5e3", stroke="#1e8449", sw=6)
    _checkmark(draw, cx + 72, cy + 68, 22, "#27ae60", lw=11)
    _border(draw, W, H, "#52be80", bw=10, radius=44)
    fnt = _font(52)
    _center_text(draw, "NORMAL", H - 110, W, fnt, "#d5f5e3")
    _save(img, "normal.png", _T_SYS)

def make_sys_fault():
    W, H = _T_SYS[0] * SCALE, _T_SYS[1] * SCALE
    img  = _gradient(W, H, "#7b241c", "#c0392b")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 18
    s = 110
    tri = [(cx, cy - s), (cx - s, cy + s // 2), (cx + s, cy + s // 2)]
    draw.polygon(tri, fill="#f1c40f", outline="#ffffff", width=7)
    bw = 17
    draw.rectangle([cx - bw, cy - s // 2 + 10, cx + bw, cy + s // 5], fill="#1a1a1a")
    dot = 19
    draw.ellipse([cx - dot, cy + s // 5 + 14, cx + dot, cy + s // 5 + 14 + dot * 2], fill="#1a1a1a")
    _border(draw, W, H, "#e74c3c", bw=10, radius=44)
    fnt = _font(52)
    _center_text(draw, "FAULT", H - 110, W, fnt, "#fdfefe")
    _save(img, "fault.png", _T_SYS)

_T_SENSOR = (100, 100)

def make_temp_normal():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#0a2e3f", "#1a5276")
    draw = ImageDraw.Draw(img, "RGBA")
    cx = W // 2 - 18
    _thermometer(draw, cx, top=26, tube_h=140, tube_w=15, fill_frac=0.42, merc="#5dade2")
    draw.text((cx + 34, 44), "deg", fill="#aed6f1", font=_font(44))
    _border(draw, W, H, "#2e86c1", bw=8, radius=32)
    _center_text(draw, "NORMAL", H - 70, W, _font(38), "#aed6f1")
    _save(img, "temp_normal.png", _T_SENSOR)

def make_temp_high():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#7b0000", "#c0392b")
    draw = ImageDraw.Draw(img, "RGBA")
    cx = W // 2 - 18
    _thermometer(draw, cx, top=26, tube_h=140, tube_w=15, fill_frac=0.94, merc="#e74c3c")
    draw.text((cx + 34, 44), "deg", fill="#fadbd8", font=_font(44))
    _warning_badge(draw, W - 44, 44, 28)
    _border(draw, W, H, "#e74c3c", bw=8, radius=32)
    _center_text(draw, "HIGH", H - 70, W, _font(38), "#fadbd8")
    _save(img, "temp_high.png", _T_SENSOR)

def make_hum_normal():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#0a3a4f", "#0e6655")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 10
    drop_pts = []
    for i in range(60):
        a = math.radians(i * 6)
        r = 58 + 20 * math.sin(a * 1.5)
        drop_pts.append((cx + int(r * math.sin(a)), cy + int(r * (-math.cos(a)))))
    draw.polygon(drop_pts, fill="#76d7c4", outline="#1abc9c", width=4)
    _center_text(draw, "%", cy + 14, W, _font(52), "#0e5038")
    _border(draw, W, H, "#1abc9c", bw=8, radius=32)
    _center_text(draw, "NORMAL", H - 70, W, _font(38), "#d1f2eb")
    _save(img, "humidity_normal.png", _T_SENSOR)

def make_hum_low():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#4a235a", "#8e44ad")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 10
    drop_pts = []
    for i in range(60):
        a = math.radians(i * 6)
        r = 58 + 20 * math.sin(a * 1.5)
        drop_pts.append((cx + int(r * math.sin(a)), cy + int(r * (-math.cos(a)))))
    draw.polygon(drop_pts, fill="#d7bde2", outline="#9b59b6", width=4)
    _center_text(draw, "%", cy + 14, W, _font(52), "#6c3483")
    _warning_badge(draw, W - 44, 44, 28)
    _border(draw, W, H, "#e74c3c", bw=8, radius=32)
    _center_text(draw, "LOW", H - 70, W, _font(38), "#f5eef8")
    _save(img, "humidity_low.png", _T_SENSOR)

def make_current_normal():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#0b3d0b", "#1e8449")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 18
    _lightning(draw, cx, cy, size=80, fill="#f9e79f", stroke="#f39c12")
    draw.text((cx + 58, cy - 24), "A", fill="#f9e79f", font=_font(44))
    _border(draw, W, H, "#27ae60", bw=8, radius=32)
    _center_text(draw, "NORMAL", H - 70, W, _font(38), "#d5f5e3")
    _save(img, "current_normal.png", _T_SENSOR)

def make_current_high():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#7d3c00", "#e67e22")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 18
    _lightning(draw, cx, cy, size=80, fill="#fff176", stroke="#ffcc02")
    for angle in (25, 60, 120, 155, 205, 330):
        _spark(draw, cx, cy, 56, angle, "#ffcc02")
    _warning_badge(draw, W - 44, 44, 28)
    _border(draw, W, H, "#e67e22", bw=8, radius=32)
    _center_text(draw, "HIGH", H - 70, W, _font(38), "#fef9e7")
    _save(img, "current_high.png", _T_SENSOR)

def make_voltage_normal():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#1a0533", "#2e4057")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 14
    bw, bh = 110, 68
    draw.rounded_rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
                            radius=12, outline="#85c1e9", width=6)
    draw.rectangle([cx + bw // 2, cy - 14, cx + bw // 2 + 16, cy + 14], fill="#85c1e9")
    for i in range(3):
        x0 = cx - bw // 2 + 12 + i * 30
        draw.rounded_rectangle([x0, cy - bh // 2 + 10, x0 + 22, cy + bh // 2 - 10],
                                radius=4, fill="#85c1e9")
    _border(draw, W, H, "#2e86c1", bw=8, radius=32)
    _center_text(draw, "NORMAL", H - 70, W, _font(38), "#aed6f1")
    _save(img, "voltage_normal.png", _T_SENSOR)

def make_voltage_fault():
    W, H = _T_SENSOR[0] * SCALE, _T_SENSOR[1] * SCALE
    img  = _gradient(W, H, "#4d0000", "#922b21")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 14
    bw, bh = 110, 68
    draw.rounded_rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
                            radius=12, outline="#f1948a", width=6)
    draw.rectangle([cx + bw // 2, cy - 14, cx + bw // 2 + 16, cy + 14], fill="#f1948a")
    x0 = cx - bw // 2 + 12
    draw.rounded_rectangle([x0, cy - bh // 2 + 10, x0 + 22, cy + bh // 2 - 10],
                            radius=4, fill="#f1948a")
    _warning_badge(draw, W - 44, 44, 28)
    _border(draw, W, H, "#e74c3c", bw=8, radius=32)
    _center_text(draw, "FAULT", H - 70, W, _font(38), "#fadbd8")
    _save(img, "voltage_fault.png", _T_SENSOR)

_T_MOTOR = (90, 90)

def make_motor_on():
    W, H = _T_MOTOR[0] * SCALE, _T_MOTOR[1] * SCALE
    img  = _gradient(W, H, "#145a32", "#239b56")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 18
    _gear(draw, cx, cy, r_out=100, r_mid=72, r_hole=28, teeth=8,
          fill="#d5f5e3", stroke="#1e8449", sw=5)
    _border(draw, W, H, "#52be80", bw=8, radius=32)
    _center_text(draw, "ON", H - 80, W, _font(56), "#d5f5e3")
    _save(img, "motor_on.png", _T_MOTOR)

def make_motor_off():
    W, H = _T_MOTOR[0] * SCALE, _T_MOTOR[1] * SCALE
    img  = _gradient(W, H, "#263238", "#455a64")
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = W // 2, H // 2 - 18
    _gear(draw, cx, cy, r_out=100, r_mid=72, r_hole=28, teeth=8,
          fill="#90a4ae", stroke="#546e7a", sw=5)
    _border(draw, W, H, "#607d8b", bw=8, radius=32)
    _center_text(draw, "OFF", H - 80, W, _font(56), "#cfd8dc")
    _save(img, "motor_off.png", _T_MOTOR)

def main():
    print(f"\nGenerating dashboard images → '{IMAGES_DIR}/'\n")
    make_sys_normal()
    make_sys_fault()
    make_temp_normal()
    make_temp_high()
    make_hum_normal()
    make_hum_low()
    make_current_normal()
    make_current_high()
    make_voltage_normal()
    make_voltage_fault()
    make_motor_on()
    make_motor_off()
    print(f"\n  All 12 images saved to '{IMAGES_DIR}/'.\n")

if __name__ == "__main__":
    main()