"""Thinking Orbs - Dotted Thought-Orb Animation Engine for Handless AI Copilot.

Based on Jakub Antalik's open-source thinking-orbs (https://github.com/Jakubantalik/thinking-orbs).
Faithfully implements the 9 geometric modes, 3D orthographic projection, Fibonacci lattice,
value noise, and dot z-sorting, fully themed in Handless's signature charcoal and emerald UI palette.
"""

from dataclasses import dataclass
import math
import time
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class Dot:
    x: float
    y: float
    z: float
    r: float
    white: float          # Ink value in [0, 1] (0 = dark ink, 1 = light/paper)
    a: float = 1.0        # Alpha in [0, 1]
    is_accent: bool = False   # True if this dot is an active particle/crest/signal
    accent_weight: float = 0.0  # 0.0 to 1.0 intensity of accent glow

@dataclass
class Line:
    x1: float
    y1: float
    x2: float
    y2: float
    white: float
    a: float = 1.0
    w: float = 1.0

@dataclass
class OrbFrame:
    dots: List[Dot]
    lines: List[Line]

# ---------------------------------------------------------------------------
# Core Math & Geometry Primitives
# ---------------------------------------------------------------------------

GOLDEN = math.pi * (3.0 - math.sqrt(5.0))

def lerp(a: float, b: float, f: float) -> float:
    return a + (b - a) * f

def frac(x: float) -> float:
    return x - math.floor(x)

def smooth_e(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)

def angle_delta(a: float, b: float) -> float:
    return math.atan2(math.sin(a - b), math.cos(a - b))

def hash_d(a: float, b: float) -> float:
    h = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return h - math.floor(h)

def vnoise(x: float, y: float) -> float:
    xi = math.floor(x)
    yi = math.floor(y)
    fx = x - xi
    fy = y - yi
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    a = hash_d(xi, yi)
    b = hash_d(xi + 1.0, yi)
    c = hash_d(xi, yi + 1.0)
    d = hash_d(xi + 1.0, yi + 1.0)
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy

def fib_dir(i: int, n: int) -> Tuple[float, float, float]:
    y = 1.0 - (2.0 * (i + 0.5)) / n
    rad = math.sqrt(max(0.0, 1.0 - y * y))
    a = i * GOLDEN
    return (rad * math.cos(a), y, rad * math.sin(a))

def make_proj(yaw: float, tilt: float, cx: float, cy: float, scale: float):
    st = math.sin(tilt)
    ct = math.cos(tilt)
    sy = math.sin(yaw)
    cyw = math.cos(yaw)
    def proj(x: float, y: float, z: float) -> Tuple[float, float, float]:
        x1 = x * cyw + z * sy
        z1 = -x * sy + z * cyw
        y1 = y * ct - z1 * st
        z2 = y * st + z1 * ct
        return (cx + x1 * scale, cy - y1 * scale, z2)
    return proj

def radius_scale(size: float, pow_val: float = 0.6) -> float:
    return (size / 300.0) ** pow_val

def finalize_frame(dots: List[Dot], lines: List[Line], r_min: float = 0.3) -> OrbFrame:
    visible: List[Dot] = []
    for d in dots:
        if d.a < 0.02:
            continue
        d.r = max(r_min, d.r)
        visible.append(d)
    visible.sort(key=lambda d: d.z)
    visible_lines = [l for l in lines if l.a >= 0.02]
    return OrbFrame(dots=visible, lines=visible_lines)

# ---------------------------------------------------------------------------
# Mode 1: Orbits ("working")
# ---------------------------------------------------------------------------

def frame_orbits(size: float, t: float, o: dict) -> OrbFrame:
    cx = size / 2.0
    cy = size / 2.0
    r_sphere = (size / 2.0) * 0.82
    pt = make_proj(t * 0.12, 0.3, cx, cy, 1.0)
    rs = radius_scale(size, o.get("rsPow", 0.6))

    dots: List[Dot] = []
    orbit_n = int(o.get("orbitN", 12))
    ghost_n = int(o.get("ghostN", 40))
    particles = int(o.get("particles", 3))

    for orb in range(orbit_n):
        h1 = hash_d(orb, 1.7)
        h2 = hash_d(orb, 5.2)
        h3 = hash_d(orb, 8.9)
        ro = r_sphere * (0.45 + 0.52 * h1)
        th = h1 * 2.0 * math.pi
        phi = math.acos(2.0 * h2 - 1.0)
        nx = math.sin(phi) * math.cos(th)
        ny = math.cos(phi)
        nz = math.sin(phi) * math.sin(th)
        ux = -ny
        uy = nx
        uz = 0.0
        ul = max(1e-6, math.sqrt(ux * ux + uy * uy))
        ux /= ul
        uy /= ul
        vx = ny * uz - nz * uy
        vy = nz * ux - nx * uz
        vz = nx * uy - ny * ux
        speed = (0.25 + 0.55 * h3) * (1.0 if h3 > 0.5 else -1.0)

        # Ghost path dots (faint orbit traces)
        for k in range(ghost_n):
            a = (k / ghost_n) * 2.0 * math.pi
            px, py, z = pt(
                (ux * math.cos(a) + vx * math.sin(a)) * ro,
                (uy * math.cos(a) + vy * math.sin(a)) * ro,
                (uz * math.cos(a) + vz * math.sin(a)) * ro,
            )
            depth = (z / ro + 1.0) / 2.0
            dots.append(Dot(
                x=px, y=py, z=z,
                r=o.get("ghostR", 0.9) * rs,
                white=0.72,
                a=o.get("ghostA", 0.5) * (0.4 + 0.6 * depth),
                is_accent=False,
                accent_weight=0.0,
            ))

        # Active particles doing the work
        for m in range(particles):
            a = t * speed + (m / particles) * 2.0 * math.pi + h2 * 6.0
            px, py, z = pt(
                (ux * math.cos(a) + vx * math.sin(a)) * ro,
                (uy * math.cos(a) + vy * math.sin(a)) * ro,
                (uz * math.cos(a) + vz * math.sin(a)) * ro,
            )
            depth = (z / ro + 1.0) / 2.0
            dots.append(Dot(
                x=px, y=py, z=z,
                r=((o.get("partR", 1.2) + o.get("partRDepth", 1.6) * depth) * rs),
                white=0.3 - 0.22 * depth,
                a=1.0,
                is_accent=True,
                accent_weight=0.85 + 0.15 * depth,
            ))

    return finalize_frame(dots, [], o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 2: Globe ("searching")
# ---------------------------------------------------------------------------

def frame_globe(size: float, t: float, o: dict) -> OrbFrame:
    spin = 0.5
    cx = size / 2.0
    cy = size / 2.0
    radius = (size / 2.0) * 0.82
    tilt = 0.4 + 0.06 * math.sin(t * 0.35)
    pt = make_proj(t * spin, tilt, cx, cy, radius)
    scan = t * (spin + (1.7 - spin) * o.get("scanMul", 1.0))
    rs = radius_scale(size, o.get("rsPow", 0.6))
    dim_base = o.get("dimBase", 1.0)

    dots: List[Dot] = []
    lat_rings = int(o.get("latRings", 17))
    lon_density = int(o.get("lonDensity", 44))

    for li in range(lat_rings + 1):
        lat = -math.pi / 2.0 + (li / lat_rings) * math.pi
        cos_lat = math.cos(lat)
        sin_lat = math.sin(lat)
        lon_count = max(1, round(abs(cos_lat) * lon_density))
        for lj in range(lon_count):
            lon = (lj / lon_count) * 2.0 * math.pi
            px, py, z = pt(cos_lat * math.cos(lon), sin_lat, cos_lat * math.sin(lon))
            depth = (z + 1.0) / 2.0
            d = angle_delta(lon + t * spin, scan)
            boost = math.exp(-(d * d) / 0.18) * max(0.0, z)
            r = ((o.get("rBase", 0.6) + o.get("rDepth", 1.7) * depth + o.get("rBoost", 1.0) * boost) * rs)
            white = o.get("inkFar", 0.62) - o.get("inkSpan", 0.54) * depth
            alpha = dim_base + (1.0 - dim_base) * min(1.0, boost)

            is_scan = boost > 0.25
            dots.append(Dot(
                x=px, y=py, z=z, r=r, white=white, a=alpha,
                is_accent=is_scan,
                accent_weight=min(1.0, boost * 1.3),
            ))

    return finalize_frame(dots, [], o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 3: Rubik ("solving")
# ---------------------------------------------------------------------------

@dataclass
class Move:
    axis: int
    lo: float
    hi: float
    ang: float

def make_moves(count: int) -> List[Move]:
    moves: List[Move] = []
    for i in range(count):
        axis = min(2, math.floor(hash_d(i, 2.3) * 3))
        lo = -1.0 + 0.5 * min(3, math.floor(hash_d(i, 5.9) * 4))
        dir_val = 1.0 if hash_d(i, 7.7) < 0.5 else -1.0
        moves.append(Move(axis=axis, lo=lo, hi=lo + 0.5, ang=(dir_val * math.pi) / 2.0))
    return moves

def solve_cycle(time_val: float, count: int, slot_dur: float, rest: float) -> Tuple[List[float], int]:
    cyc = 2.0 * count * slot_dur + rest
    tc = time_val % cyc
    amount = [0.0] * count
    active = -1
    if tc < 2.0 * count * slot_dur:
        slot = math.floor(tc / slot_dur)
        p = (tc - slot * slot_dur) / slot_dur
        cl = min(1.0, p / 0.7)
        ep = 1.0 - (1.0 - cl) ** 3.0
        if slot < count:
            for i in range(slot):
                amount[i] = 1.0
            amount[slot] = ep
            active = slot
        else:
            u = 2 * count - 1 - slot
            for i in range(u):
                amount[i] = 1.0
            amount[u] = 1.0 - ep
            active = u
    return amount, active

def apply_moves(pt3: Tuple[float, float, float], moves: List[Move], amount: List[float], active: int) -> Tuple[float, float, float, bool]:
    x, y, z = pt3
    in_active = False
    for i in range(len(moves)):
        if amount[i] <= 0:
            continue
        mv = moves[i]
        coord = x if mv.axis == 0 else (y if mv.axis == 1 else z)
        if coord < mv.lo or coord >= mv.hi:
            continue
        if i == active:
            in_active = True
        a = mv.ang * amount[i]
        ca = math.cos(a)
        sa = math.sin(a)
        if mv.axis == 0:
            y2 = y * ca - z * sa
            z = y * sa + z * ca
            y = y2
        elif mv.axis == 1:
            x2 = x * ca + z * sa
            z = -x * sa + z * ca
            x = x2
        else:
            x2 = x * ca - y * sa
            y = x * sa + y * ca
            x = x2
    return x, y, z, in_active

def frame_rubik(size: float, t: float, o: dict) -> OrbFrame:
    cx = size / 2.0
    cy = size / 2.0
    r_sphere = (size / 2.0) * 0.82
    pt = make_proj(t * 0.55, 0.35 + 0.1 * math.sin(t * 0.9), cx, cy, r_sphere)
    rs = radius_scale(size, o.get("rsPow", 0.6))
    move_count = int(o.get("moveCount", 14))
    moves = make_moves(move_count)
    amount, active = solve_cycle(t, move_count, 0.42, 1.2)

    dots: List[Dot] = []
    lat_rings = int(o.get("latRings", 15))
    lon_density = int(o.get("lonDensity", 40))

    for li in range(lat_rings + 1):
        lat = -math.pi / 2.0 + (li / lat_rings) * math.pi
        cos_lat = math.cos(lat)
        sin_lat = math.sin(lat)
        lon_count = max(1, round(abs(cos_lat) * lon_density))
        for lj in range(lon_count):
            lon = (lj / lon_count) * 2.0 * math.pi
            x, y, z, in_active = apply_moves(
                (cos_lat * math.cos(lon), sin_lat, cos_lat * math.sin(lon)),
                moves, amount, active
            )
            px, py, zr = pt(x, y, z)
            depth = (zr + 1.0) / 2.0
            r = ((o.get("rBase", 0.6) + o.get("rDepth", 1.7) * depth + (o.get("rActive", 0.3) if in_active else 0.0)) * rs)
            white = (o.get("inkFar", 0.62) - o.get("inkSpan", 0.54) * depth - (0.14 if in_active else 0.0))
            dots.append(Dot(
                x=px, y=py, z=zr, r=r, white=white, a=1.0,
                is_accent=in_active,
                accent_weight=1.0 if in_active else 0.0,
            ))

    return finalize_frame(dots, [], o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 4: Wave ("listening")
# ---------------------------------------------------------------------------

def frame_wave(size: float, t: float, o: dict, audio_boost: float = 0.0) -> OrbFrame:
    cx = size / 2.0
    cy = size / 2.0
    r_sphere = (size / 2.0) * 0.874
    pt = make_proj(t * 0.18, 0.38, cx, cy, 1.0)
    rs = radius_scale(size, o.get("rsPow", 0.6))

    dots: List[Dot] = []
    rings = int(o.get("rings", 15))
    lon_density = int(o.get("lonDensity", 40))

    # Incorporate microphone audio level seamlessly into wave dynamics
    wave_amp = 1.0 + (audio_boost * 1.5)

    for ri in range(rings + 1):
        lat = -math.pi / 2.0 + (ri / rings) * math.pi
        cos_lat = math.cos(lat)
        sin_lat = math.sin(lat)
        w = (0.62 * math.sin(t * 2.1 - ri * 0.52) + 0.38 * math.sin(t * 1.27 + ri * 0.83)) * wave_amp
        rr = r_sphere * (0.88 + 0.105 * w)
        lon_count = max(1, round(abs(cos_lat) * lon_density))
        for lj in range(lon_count):
            lon = (lj / lon_count) * 2.0 * math.pi
            px, py, z = pt(cos_lat * math.cos(lon) * rr, sin_lat * rr, cos_lat * math.sin(lon) * rr)
            depth = (z / r_sphere + 1.0) / 2.0
            crest = max(0.0, w)
            r = ((o.get("rBase", 0.6) + o.get("rDepth", 1.7) * depth) * (1.0 + 0.4 * crest) * rs)
            white = 0.66 - 0.56 * depth - 0.1 * crest

            # Emerald accent illuminates on wave crests and voice activity
            is_crest = crest > 0.35 or audio_boost > 0.2
            accent_w = min(1.0, crest * 0.9 + audio_boost * 0.6)
            dots.append(Dot(
                x=px, y=py, z=z, r=r, white=white, a=1.0,
                is_accent=is_crest,
                accent_weight=accent_w,
            ))

    return finalize_frame(dots, [], o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 5: Web ("connecting")
# ---------------------------------------------------------------------------

def frame_web(size: float, t: float, o: dict) -> OrbFrame:
    cx = size / 2.0
    cy = size / 2.0
    r_sphere = (size / 2.0) * 0.8 * o.get("spread", 1.0)
    pt = make_proj(t * 0.12, 0.32, cx, cy, r_sphere)
    rs = radius_scale(size, o.get("rsPow", 0.6))

    node_n = int(o.get("nodeN", 30))
    thr = o.get("thr", 0.72)
    node_r = o.get("nodeR", 1.4)
    node_r_depth = o.get("nodeRDepth", 1.8)

    nodes: List[Tuple[float, float, float]] = []
    for i in range(node_n):
        d = fib_dir(i, node_n)
        x = d[0] + 0.3 * (vnoise(i * 0.31 + 9.0, t * 0.24) - 0.5) * 2.0
        y = d[1] + 0.3 * (vnoise(i * 0.53 + 27.0, t * 0.21) - 0.5) * 2.0
        z = d[2] + 0.3 * (vnoise(i * 0.77 + 55.0, t * 0.27) - 0.5) * 2.0
        l = math.sqrt(x * x + y * y + z * z)
        nodes.append((x / l, y / l, z / l))

    lines: List[Line] = []
    dots: List[Dot] = []

    # Proximity edges
    for i in range(node_n):
        for j in range(i + 1, node_n):
            dx = nodes[i][0] - nodes[j][0]
            dy = nodes[i][1] - nodes[j][1]
            dz = nodes[i][2] - nodes[j][2]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist >= thr:
                continue
            x1, y1, z1 = pt(nodes[i][0], nodes[i][1], nodes[i][2])
            x2, y2, z2 = pt(nodes[j][0], nodes[j][1], nodes[j][2])
            depth = ((z1 + z2) / 2.0 + 1.0) / 2.0
            lines.append(Line(
                x1=x1, y1=y1, x2=x2, y2=y2,
                white=0.42,
                a=(1.0 - dist / thr) * (0.3 + 0.55 * depth),
                w=max(0.6, o.get("lineW", 0.8) * rs),
            ))

    # Constellation node dots
    for i in range(node_n):
        px, py, z = pt(nodes[i][0], nodes[i][1], nodes[i][2])
        depth = (z + 1.0) / 2.0
        pulse = 1.0 + 0.25 * math.sin(t * 1.4 + i * 2.7)
        dots.append(Dot(
            x=px, y=py, z=z,
            r=(node_r + node_r_depth * depth) * pulse * rs,
            white=0.55 - 0.45 * depth,
            a=1.0,
            is_accent=False,
            accent_weight=0.0,
        ))

    # Travelling signal packets
    signals = int(o.get("signals", 5))
    for s in range(signals):
        seg = math.floor(t * 0.55 + s * 7.31)
        a_idx = math.floor(hash_d(seg, s * 3.1 + 1.7) * node_n)
        b_idx = math.floor(hash_d(seg, s * 5.7 + 4.2) * node_n)
        if a_idx == b_idx:
            continue
        f = frac(t * 0.55 + s * 7.31)
        x = lerp(nodes[a_idx][0], nodes[b_idx][0], f)
        y = lerp(nodes[a_idx][1], nodes[b_idx][1], f)
        z = lerp(nodes[a_idx][2], nodes[b_idx][2], f)
        l = max(1e-6, math.sqrt(x * x + y * y + z * z))
        px, py, zr = pt(x / l, y / l, z / l)
        depth = (zr + 1.0) / 2.0
        dots.append(Dot(
            x=px, y=py, z=zr,
            r=(node_r * 1.5 + node_r_depth * depth) * rs,
            white=0.05,
            a=0.5 + 0.5 * depth,
            is_accent=True,
            accent_weight=1.0,
        ))

    return finalize_frame(dots, lines, o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 6: Braid ("weaving")
# ---------------------------------------------------------------------------

def frame_braid(size: float, t: float, o: dict) -> OrbFrame:
    cx = size / 2.0
    cy = size / 2.0
    r_sphere = (size / 2.0) * 0.76
    pt = make_proj(t * 0.4, 0.3, cx, cy, 1.0)
    rs = radius_scale(size, o.get("rsPow", 0.6))

    dots: List[Dot] = []
    ghost_n = int(o.get("ghostN", 150))
    for i in range(ghost_n):
        d = fib_dir(i, ghost_n)
        px, py, z = pt(d[0] * r_sphere, d[1] * r_sphere, d[2] * r_sphere)
        depth = (z / r_sphere + 1.0) / 2.0
        dots.append(Dot(x=px, y=py, z=z, r=0.8 * rs, white=0.78, a=0.1 + 0.22 * depth, is_accent=False, accent_weight=0.0))

    strand_n = int(o.get("strandN", 52))
    turns = o.get("turns", 3.0)
    for s in range(3):
        phase = (s / 3.0) * 2.0 * math.pi
        is_highlight_strand = (s == 0)
        for i in range(strand_n):
            u = (frac(i / strand_n + t * 0.045) * 2.0 - 1.0) * 0.96
            surf = math.sqrt(max(0.0, 1.0 - u * u))
            end_fade = min(1.0, (1.0 - abs(u)) / 0.1)
            a = u * math.pi * turns + phase
            weave = 1.0 + 0.075 * math.sin(u * math.pi * turns * 2.0 + phase * 2.0 + t * 0.8)
            rr = surf * r_sphere * weave
            px, py, zr = pt(math.cos(a) * rr, u * r_sphere * weave, math.sin(a) * rr)
            depth = (zr / r_sphere + 1.0) / 2.0
            dots.append(Dot(
                x=px, y=py, z=zr,
                r=((o.get("rBase", 1.2) + o.get("rDepth", 1.8) * depth) * rs),
                white=0.55 - 0.45 * depth,
                a=end_fade * (0.45 + 0.55 * depth),
                is_accent=is_highlight_strand,
                accent_weight=0.9 if is_highlight_strand else 0.0,
            ))

    return finalize_frame(dots, [], o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 7 & 8: Ribbon ("composing") & Ring ("breathing")
# ---------------------------------------------------------------------------

def frame_ribbon(size: float, t: float, o: dict) -> OrbFrame:
    cx = size / 2.0
    cy = size / 2.0
    r_sphere = (size / 2.0) * 0.78
    spin = o.get("spin", 1.0)
    cam_tilt = 0.3
    pt = make_proj(t * 0.1 * spin, cam_tilt, cx, cy, 1.0)
    rs = radius_scale(size, o.get("rsPow", 0.6))
    face_on = bool(o.get("faceOn", 0))

    dots: List[Dot] = []
    ghost_n = int(o.get("ghostN", 150))
    for i in range(ghost_n):
        d = fib_dir(i, ghost_n)
        px, py, z = pt(d[0] * r_sphere, d[1] * r_sphere, d[2] * r_sphere)
        depth = (z / r_sphere + 1.0) / 2.0
        dots.append(Dot(x=px, y=py, z=z, r=0.8 * rs, white=0.78, a=0.1 + 0.22 * depth, is_accent=False, accent_weight=0.0))

    ya = t * 0.24 * spin
    ta = -cam_tilt if face_on else 0.55 + 0.3 * math.sin(t * 0.18) * spin
    ux = math.cos(ya)
    uy = 0.0
    uz = math.sin(ya)
    vx = -uz * math.sin(ta)
    vy = math.cos(ta)
    vz = ux * math.sin(ta)
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx

    wob_amp = 0.23 * o.get("wobMul", 1.0)
    base_r = r_sphere / (1.0 + 0.85 * wob_amp) if face_on else r_sphere

    base_lanes = int(o.get("lanes", 5))
    segs = int(o.get("segs", 88))
    lanes = max(1, round(base_lanes * o.get("bandMul", 1.0)))

    for w_idx in range(lanes):
        lane_off = (w_idx - (lanes - 1) / 2.0) * 0.075
        edge = abs(w_idx - (lanes - 1) / 2.0) / max(1.0, (lanes - 1) / 2.0)
        for k in range(segs):
            a = (k / segs) * 2.0 * math.pi
            wob = (0.16 * math.sin(a * 3.0 - t * 1.7 + w_idx * 0.22) + 0.07 * math.sin(a * 5.0 + t * 1.1)) * o.get("wobMul", 1.0)
            radial = (1.0 + wob) if face_on else 1.0
            off = lane_off if face_on else (lane_off + wob)
            x = ux * math.cos(a) + vx * math.sin(a) + nx * off
            y = uy * math.cos(a) + vy * math.sin(a) + ny * off
            z = uz * math.cos(a) + vz * math.sin(a) + nz * off
            l = math.sqrt(x * x + y * y + z * z)
            rr = base_r * radial
            px, py, zr = pt((x / l) * rr, (y / l) * rr, (z / l) * rr)
            depth = (zr / r_sphere + 1.0) / 2.0
            is_accent = (edge < 0.25) and (depth > 0.6)
            dots.append(Dot(
                x=px, y=py, z=zr,
                r=((o.get("rBase", 1.1) + o.get("rDepth", 1.7) * depth) * (1.0 - 0.25 * edge) * rs),
                white=0.52 - 0.44 * depth + 0.18 * edge,
                a=0.4 + 0.6 * depth,
                is_accent=is_accent,
                accent_weight=0.75 * depth if is_accent else 0.0,
            ))

    return finalize_frame(dots, [], o.get("rMin", 0.3))

# ---------------------------------------------------------------------------
# Mode 9: Morph ("shaping")
# ---------------------------------------------------------------------------

def poly_path(verts: List[Tuple[float, float]]) -> Callable[[float], Tuple[float, float]]:
    v_len = len(verts)
    l_list: List[float] = []
    total = 0.0
    for i in range(v_len):
        a = verts[i]
        b = verts[(i + 1) % v_len]
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        l_list.append(l)
        total += l
    def path_fn(f: float) -> Tuple[float, float]:
        target = f * total
        i = 0
        while target > l_list[i] and i < v_len - 1:
            target -= l_list[i]
            i += 1
        a = verts[i]
        b = verts[(i + 1) % v_len]
        ff = min(1.0, target / l_list[i]) if l_list[i] else 0.0
        return (a[0] + (b[0] - a[0]) * ff, a[1] + (b[1] - a[1]) * ff)
    return path_fn

def circle_path(f: float) -> Tuple[float, float]:
    a = -math.pi / 2.0 + f * 2.0 * math.pi
    return (math.cos(a) * 0.24, math.sin(a) * 0.24)

TRIANGLE_PATH = poly_path([(0.0, -0.26), (0.24, 0.16), (-0.24, 0.16)])
SQUARE_PATH = poly_path([(0.0, -0.2), (0.2, -0.2), (0.2, 0.2), (-0.2, 0.2), (-0.2, -0.2)])
MORPH_CYCLE = [circle_path, TRIANGLE_PATH, SQUARE_PATH]

HOLD_TIME = 1.4
MORPH_TIME = 0.9
SEG_TIME = HOLD_TIME + MORPH_TIME

def frame_morph(size: float, t: float, o: dict) -> OrbFrame:
    k_len = len(MORPH_CYCLE)
    tc = t % (SEG_TIME * k_len)
    k = math.floor(tc / SEG_TIME)
    local = tc - k * SEG_TIME
    m = smooth_e((local - HOLD_TIME) / MORPH_TIME) if local > HOLD_TIME else 0.0
    sprd = o.get("spread", 1.0)

    p_a = MORPH_CYCLE[k]
    p_b = MORPH_CYCLE[(k + 1) % k_len]
    m_pts = 160
    pts: List[Tuple[float, float]] = []
    for i in range(m_pts):
        f = i / m_pts
        a = p_a(f)
        b = p_b(f)
        pts.append(((a[0] + (b[0] - a[0]) * m) * sprd, (a[1] + (b[1] - a[1]) * m) * sprd))

    l_list: List[float] = []
    total = 0.0
    for i in range(m_pts):
        a = pts[i]
        b = pts[(i + 1) % m_pts]
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        l_list.append(l)
        total += l

    n = max(6, round(34.0 * o.get("iconD", 1.0)))
    re = o.get("rDot", 0.021) * 1.35 * sprd
    pulse = 1.0 + 0.02 * math.sin(local * 3.1)

    dots: List[Dot] = []
    c2 = size / 2.0
    seg = 0
    acc = 0.0
    for k2 in range(n):
        target = (k2 / n) * total
        while acc + l_list[seg] < target and seg < m_pts - 1:
            acc += l_list[seg]
            seg += 1
        a = pts[seg]
        b = pts[(seg + 1) % m_pts]
        f = min(1.0, (target - acc) / l_list[seg]) if l_list[seg] else 0.0
        x = (a[0] + (b[0] - a[0]) * f) * pulse
        y = (a[1] + (b[1] - a[1]) * f) * pulse
        is_transition = m > 0.05
        dots.append(Dot(
            x=c2 + x * size,
            y=c2 + y * size,
            z=0.0,
            r=max(0.35, re * size),
            white=0.1,
            a=1.0,
            is_accent=is_transition,
            accent_weight=m,
        ))

    return finalize_frame(dots, [], o.get("rMin", 0.25))

# ---------------------------------------------------------------------------
# Profiles, Presets & Scalers
# ---------------------------------------------------------------------------

STATE_TO_MODE = {
    "working": "orbits",
    "searching": "globe",
    "solving": "rubik",
    "listening": "wave",
    "connecting": "web",
    "weaving": "braid",
    "composing": "ribbon",
    "breathing": "ring",
    "shaping": "morph",
}

BASE_PROFILES = {
    "globe": {"latRings": 17, "lonDensity": 44, "rBase": 0.6, "rDepth": 1.7, "rBoost": 1.0, "inkFar": 0.62, "inkSpan": 0.54, "rsPow": 0.6, "rMin": 0.3},
    "orbits": {"orbitN": 12, "ghostN": 40, "ghostR": 0.9, "ghostA": 0.5, "particles": 3, "partR": 1.2, "partRDepth": 1.6, "rsPow": 0.6, "rMin": 0.3},
    "rubik": {"latRings": 15, "lonDensity": 40, "moveCount": 14, "rBase": 0.6, "rDepth": 1.7, "rActive": 0.3, "inkFar": 0.62, "inkSpan": 0.54, "rsPow": 0.6, "rMin": 0.3},
    "wave": {"rings": 15, "lonDensity": 40, "rBase": 0.6, "rDepth": 1.7, "rsPow": 0.6, "rMin": 0.3},
    "web": {"nodeN": 30, "thr": 0.72, "signals": 5, "nodeR": 1.4, "nodeRDepth": 1.8, "lineW": 0.8, "rsPow": 0.6, "rMin": 0.3},
    "braid": {"strandN": 52, "turns": 3.0, "ghostN": 150, "rBase": 1.2, "rDepth": 1.8, "rsPow": 0.6, "rMin": 0.3},
    "ribbon": {"lanes": 5, "segs": 88, "ghostN": 150, "rBase": 1.1, "rDepth": 1.7, "rsPow": 0.6, "rMin": 0.3},
    "ring": {"lanes": 5, "segs": 88, "ghostN": 0, "faceOn": 1, "rBase": 1.1, "rDepth": 1.7, "rsPow": 0.6, "rMin": 0.3},
    "morph": {"rDot": 0.021, "iconD": 1.0, "rMin": 0.25},
}

PRESETS = {
    "orbits": {64: {"speed": 1.885, "count": 1.0, "size": 1.0}, 20: {"speed": 3.9, "count": 0.238, "size": 2.4}},
    "globe": {64: {"speed": 2.015, "count": 0.42, "size": 1.15, "extra": {"scanMul": 4.08, "dimBase": 0.45}}, 20: {"speed": 2.665, "count": 0.105, "size": 1.75, "extra": {"scanMul": 4.335, "dimBase": 0.45}}},
    "rubik": {64: {"speed": 1.82, "count": 0.35, "size": 1.05}, 20: {"speed": 1.95, "count": 0.088, "size": 1.9}},
    "wave": {64: {"speed": 4.388, "count": 0.341, "size": 1.0}, 20: {"speed": 3.998, "count": 0.105, "size": 1.6}},
    "web": {64: {"speed": 3.315, "count": 1.35, "size": 0.95}, 20: {"speed": 6.63, "count": 0.25, "size": 1.52}},
    "braid": {64: {"speed": 1.625, "count": 0.5, "size": 1.0}, 20: {"speed": 2.75, "count": 0.1125, "size": 1.36}},
    "ribbon": {64: {"speed": 2.34, "count": 0.25, "size": 0.85, "extra": {"spin": 0, "bandMul": 3.9, "wobMul": 1}}, 20: {"speed": 3.12, "count": 0.051, "size": 1.073, "extra": {"spin": 0, "bandMul": 4.94, "wobMul": 1}}},
    "ring": {64: {"speed": 3.24, "count": 0.25, "size": 0.956, "extra": {"spin": 0, "bandMul": 3.627, "wobMul": 0.368}}, 20: {"speed": 3.78, "count": 0.028, "size": 1.622, "extra": {"spin": 0, "bandMul": 3.968, "wobMul": 0.565}}},
    "morph": {64: {"speed": 2.405, "count": 0.702, "size": 0.395, "extra": {"spread": 1.45}}, 20: {"speed": 2.08, "count": 0.53, "size": 1.011, "extra": {"spread": 1.45}}},
}

def scale_counts(opts: dict, scale: float) -> dict:
    out = dict(opts)
    done = set()
    rt = math.sqrt(scale)
    pairs = [("latRings", "lonDensity"), ("rings", "lonDensity"), ("lanes", "segs")]
    for a, b in pairs:
        if a in out and b in out and a not in done and b not in done:
            out[a] = max(2, round(out[a] * rt))
            out[b] = max(2, round(out[b] * rt))
            done.add(a)
            done.add(b)
    for k in ["orbitN", "ghostN", "nodeN", "strandN", "signals"]:
        if k in out and out[k] != 0 and k not in done:
            out[k] = max(1, round(out[k] * scale))
    if "iconD" in out:
        out["iconD"] = max(0.02, out["iconD"] * scale)
    return out

def scale_radii(opts: dict, scale: float) -> dict:
    out = dict(opts)
    radius_keys = ["rBase", "rDepth", "rActive", "rDot", "ghostR", "partR", "partRDepth", "nodeR", "nodeRDepth"]
    for k in radius_keys:
        if k in out and out[k] is not None:
            out[k] = out[k] * scale
    out["rSizeMul"] = out.get("rSizeMul", 1.0) * scale
    return out

def resolve_preset(state: str, size: float) -> Tuple[str, float, dict]:
    mode = STATE_TO_MODE.get(state, "orbits")
    preset_size = 20 if size <= 32 else 64
    pr = PRESETS[mode][preset_size]
    opts = dict(BASE_PROFILES[mode])
    if pr["count"] != 1:
        opts = scale_counts(opts, pr["count"])
    if pr["size"] != 1:
        opts = scale_radii(opts, pr["size"])
    if "extra" in pr:
        opts.update(pr["extra"])
    return mode, pr["speed"], opts

# ---------------------------------------------------------------------------
# Handless Theme Palette Mapper
# ---------------------------------------------------------------------------

# Signature Handless Brand Colors
COLOR_CHARCOAL_DARK = QColor(24, 24, 27)    # #18181B - Primary ink
COLOR_CHARCOAL_MID = QColor(113, 113, 122)   # #71717A - Depth falloff
COLOR_CHARCOAL_LIGHT = QColor(228, 228, 231) # #E4E4E7 - Distant dots

COLOR_EMERALD_BASE = QColor(16, 185, 129)    # #10B981 - Handless signature emerald
COLOR_EMERALD_BRIGHT = QColor(52, 211, 153)  # #34D399 - Luminous crest highlight
COLOR_EMERALD_DEEP = QColor(5, 150, 105)     # #059669 - Rich deep emerald

def get_dot_color(dot: Dot, theme: str, dark_mode: bool = False, audio_level: float = 0.0) -> QColor:
    """Map pure ink value + 3D z-depth + accent state to the Handless UI color palette."""
    alpha_int = max(0, min(255, int(dot.a * 255)))

    if theme == "monochrome":
        w = max(0.0, min(1.0, dot.white))
        g = round((1.0 - w if dark_mode else w) * 255)
        return QColor(g, g, g, alpha_int)

    if theme == "emerald":
        # Pure radiant emerald spectrum
        w = max(0.0, min(1.0, dot.white))
        r = int(lerp(16, 52, 1.0 - w))
        g = int(lerp(185, 211, 1.0 - w))
        b = int(lerp(129, 153, 1.0 - w))
        return QColor(r, g, b, alpha_int)

    # Default: "handless" theme
    # Active accent (wave crest, orbiting particle, rubik band, signal packet)
    if dot.is_accent:
        intensity = max(0.0, min(1.0, dot.accent_weight + audio_level * 0.4))
        # Interpolate between deep emerald and brilliant emerald
        r = int(lerp(COLOR_EMERALD_DEEP.red(), COLOR_EMERALD_BRIGHT.red(), intensity))
        g = int(lerp(COLOR_EMERALD_DEEP.green(), COLOR_EMERALD_BRIGHT.green(), intensity))
        b = int(lerp(COLOR_EMERALD_DEEP.blue(), COLOR_EMERALD_BRIGHT.blue(), intensity))
        return QColor(r, g, b, alpha_int)

    # Base dots: charcoal with depth-shading
    if dark_mode:
        # Dark substrate: near dots are bright platinum (#F4F4F5), far dots are dark slate
        w = max(0.0, min(1.0, dot.white))
        val = int(lerp(244, 113, w))
        return QColor(val, val, val, alpha_int)
    else:
        # Light warm substrate: near dots are deep charcoal (#18181B), far dots are soft zinc (#71717A / #A1A1AA)
        w = max(0.0, min(1.0, dot.white))
        r = int(lerp(24, 161, w))
        g = int(lerp(24, 161, w))
        b = int(lerp(27, 170, w))
        return QColor(r, g, b, alpha_int)

def get_line_color(line: Line, theme: str, dark_mode: bool = False) -> QColor:
    alpha_int = max(0, min(255, int(line.a * 255)))
    if theme == "handless" or theme == "emerald":
        # Subtle emerald tinted connection line
        return QColor(16, 185, 129, max(20, int(alpha_int * 0.75)))
    w = max(0.0, min(1.0, line.white))
    g = round((1.0 - w if dark_mode else w) * 255)
    return QColor(g, g, g, alpha_int)

# ---------------------------------------------------------------------------
# Qt Widget: ThinkingOrbWidget
# ---------------------------------------------------------------------------

class ThinkingOrbWidget(QWidget):
    """Modern Dotted AI Thinking Orb component based on Jakub Antalik's thinking-orbs.

    Renders lightweight 2D canvas/QPainter dot lattices with 9 hand-tuned states,
    3D z-depth sorting, silky 33 FPS timer loop, live audio reactivity, and Handless
    monochrome + emerald brand styling.
    """

    def __init__(
        self,
        size: int = 64,
        state: str = "working",
        theme: str = "handless",
        speed: float = 1.0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self._state = state
        self._theme = theme
        self._speed_multiplier = speed
        self._dark_mode = False

        self._audio_level = 0.0
        self._target_audio_level = 0.0
        self._is_paused = False
        self._is_speaking = False
        self._is_thinking = False
        self._is_active = False

        self._start_time = time.monotonic()
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)  # ~30 FPS

    def minimumSizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    def sizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        """Switch agent state ("working", "searching", "solving", "listening", etc.)."""
        if state not in STATE_TO_MODE:
            return
        if self._state != state:
            self._state = state
            self.update()

    def set_theme(self, theme: str) -> None:
        """Set palette theme ("handless", "monochrome", "dark", "emerald")."""
        self._theme = theme
        self.update()

    def set_dark_mode(self, dark: bool) -> None:
        self._dark_mode = dark
        self.update()

    def set_speed(self, speed: float) -> None:
        self._speed_multiplier = max(0.1, speed)

    def set_paused(self, paused: bool) -> None:
        self._is_paused = paused
        if not paused:
            self.update()

    def set_level(self, level: float) -> None:
        """Update live audio level (0.0 to 1.0) for microphone reactivity."""
        self._target_audio_level = max(0.0, min(1.0, level))

    def set_active(self, active: bool) -> None:
        """Backwards compatibility for GradientOrbWidget."""
        self._is_active = active
        if active:
            self.set_state("working")
        else:
            self.set_state("breathing")

    def set_speaking(self, speaking: bool) -> None:
        """Configure live call speaking state."""
        self._is_speaking = speaking
        if speaking:
            self.set_state("composing")
        else:
            if not self._is_thinking:
                self.set_state("listening")

    def set_thinking(self, thinking: bool) -> None:
        """Configure extended thinking state."""
        self._is_thinking = thinking
        if thinking:
            self.set_state("solving")
        else:
            if not self._is_speaking:
                self.set_state("listening")

    def _on_tick(self) -> None:
        if self._is_paused:
            return
        # Smooth lerp audio amplitude towards target
        self._audio_level += (self._target_audio_level - self._audio_level) * 0.32
        self.update()

    def _compute_frame(self) -> OrbFrame:
        now = time.monotonic()
        mode, base_speed, opts = resolve_preset(self._state, self._size)
        eff_speed = base_speed * self._speed_multiplier
        t = (now - self._start_time) * eff_speed

        if mode == "orbits":
            return frame_orbits(self._size, t, opts)
        elif mode == "globe":
            return frame_globe(self._size, t, opts)
        elif mode == "rubik":
            return frame_rubik(self._size, t, opts)
        elif mode == "wave":
            return frame_wave(self._size, t, opts, audio_boost=self._audio_level)
        elif mode == "web":
            return frame_web(self._size, t, opts)
        elif mode == "braid":
            return frame_braid(self._size, t, opts)
        elif mode == "ribbon":
            return frame_ribbon(self._size, t, opts)
        elif mode == "ring":
            return frame_ribbon(self._size, t, opts)
        elif mode == "morph":
            return frame_morph(self._size, t, opts)
        else:
            return frame_orbits(self._size, t, opts)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        frame = self._compute_frame()

        # 1. Stroke Pass: lines first so node dots render cleanly on top
        for line in frame.lines:
            pen = QPen(get_line_color(line, self._theme, self._dark_mode))
            pen.setWidthF(line.w)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(line.x1, line.y1), QPointF(line.x2, line.y2))

        # 2. Dot Pass: z-sorted far to near
        painter.setPen(Qt.PenStyle.NoPen)
        for dot in frame.dots:
            color = get_dot_color(dot, self._theme, self._dark_mode, self._audio_level)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(dot.x, dot.y), dot.r, dot.r)

        painter.end()
