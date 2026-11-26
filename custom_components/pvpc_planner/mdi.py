"""Iconos MDI rasterizados desde los trazados SVG que trae el frontend de HA.

Funciones bloqueantes (leen disco): llamar desde el executor.
"""

from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
import itertools
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageDraw

# Lado del viewBox de MDI.
_VIEWBOX = 24
_SUPERSAMPLE = 4
_CURVE_STEPS = 12
_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

type Point = tuple[float, float]


@lru_cache(maxsize=1)
def _mdi_dir() -> Path | None:
    try:
        import hass_frontend

        folder = Path(hass_frontend.where()) / "static" / "mdi"
    except ImportError:
        return None
    return folder if (folder / "iconMetadata.json").is_file() else None


@lru_cache(maxsize=1)
def _parts() -> tuple[list[str], list[str]]:
    """Inicio y fichero de cada trozo del índice, ordenados por nombre."""
    folder = _mdi_dir()
    if folder is None:
        return [], []
    parts = json.loads((folder / "iconMetadata.json").read_text())["parts"]
    return [p.get("start", "") for p in parts], [p["file"] for p in parts]


@lru_cache(maxsize=8)
def _chunk(file: str) -> dict[str, str]:
    return json.loads((_mdi_dir() / f"{file}.json").read_text())


def icon_path(icon: str) -> str | None:
    """Trazado SVG de "mdi:<nombre>" o None si no existe."""
    if not icon.startswith("mdi:"):
        return None
    name = icon.removeprefix("mdi:")
    starts, files = _parts()
    if not files:
        return None
    return _chunk(files[bisect_right(starts, name) - 1]).get(name)


@lru_cache(maxsize=128)
def icon_mask(icon: str, size: int) -> Image.Image | None:
    """Máscara "L" de size x size con el icono, o None si no se encuentra."""
    if (path := icon_path(icon)) is None:
        return None
    big = size * _SUPERSAMPLE
    mask = Image.new("L", (big, big))
    _fill_nonzero(ImageDraw.Draw(mask), _subpaths(path), big / _VIEWBOX, big)
    return mask.resize((size, size), Image.Resampling.BOX)


class _Scanner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def _skip(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " ,\t\n\r":
            self.pos += 1

    def command(self) -> str | None:
        self._skip()
        if self.pos < len(self.text) and self.text[self.pos].isalpha():
            self.pos += 1
            return self.text[self.pos - 1]
        return None

    def has_number(self) -> bool:
        self._skip()
        return bool(_NUMBER.match(self.text, self.pos))

    def number(self) -> float:
        self._skip()
        if not (m := _NUMBER.match(self.text, self.pos)):
            raise ValueError(f"Number expected at {self.pos}")
        self.pos = m.end()
        return float(m[0])

    def flag(self) -> bool:
        # Las banderas de los arcos pueden ir pegadas: "a1 1 0 01 2 2".
        self._skip()
        self.pos += 1
        return self.text[self.pos - 1] == "1"


def _subpaths(path: str) -> list[list[Point]]:
    """Polígonos cerrados que aproximan cada subtrazado."""
    s = _Scanner(path)
    out: list[list[Point]] = []
    pts: list[Point] = []
    cur = start = ctrl = (0.0, 0.0)
    cmd = None
    while True:
        cmd = s.command() or (cmd if s.has_number() else None)
        if cmd is None:
            break
        rel = cmd.islower()
        op = cmd.upper()
        if op == "Z":
            cur = ctrl = start
            continue
        base = cur if rel else (0.0, 0.0)

        def pt(b: Point = base) -> Point:
            return (b[0] + s.number(), b[1] + s.number())

        prev_op = ctrl
        if op == "M":
            if len(pts) > 2:
                out.append(pts)
            cur = start = ctrl = pt()
            pts = [cur]
            # Las coordenadas siguientes a un M son líneas.
            cmd = "l" if rel else "L"
            continue
        if op == "L":
            new = pt()
            seg = [new]
        elif op == "H":
            new = ((cur[0] if rel else 0) + s.number(), cur[1])
            seg = [new]
        elif op == "V":
            new = (cur[0], (cur[1] if rel else 0) + s.number())
            seg = [new]
        elif op in "CS":
            c1 = _mirror(prev_op, cur) if op == "S" else pt()
            c2, new = pt(), pt()
            seg = _cubic(cur, c1, c2, new)
            ctrl = c2
        elif op in "QT":
            c1 = _mirror(prev_op, cur) if op == "T" else pt()
            new = pt()
            seg = _quad(cur, c1, new)
            ctrl = c1
        elif op == "A":
            rx, ry, rot = s.number(), s.number(), s.number()
            large, sweep = s.flag(), s.flag()
            new = pt()
            seg = _arc(cur, rx, ry, rot, large, sweep, new)
        else:
            raise ValueError(f"Unsupported command {cmd}")
        if op not in "CSQT":
            ctrl = new
        pts += seg
        cur = new
    if len(pts) > 2:
        out.append(pts)
    return out


def _mirror(ctrl: Point, cur: Point) -> Point:
    return (2 * cur[0] - ctrl[0], 2 * cur[1] - ctrl[1])


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point) -> list[Point]:
    out = []
    for i in range(1, _CURVE_STEPS + 1):
        t = i / _CURVE_STEPS
        u = 1 - t
        a, b, c, d = u**3, 3 * u * u * t, 3 * u * t * t, t**3
        out.append(
            (
                a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
            )
        )
    return out


def _quad(p0: Point, p1: Point, p2: Point) -> list[Point]:
    out = []
    for i in range(1, _CURVE_STEPS + 1):
        t = i / _CURVE_STEPS
        u = 1 - t
        out.append(
            (
                u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
            )
        )
    return out


def _arc(
    p0: Point, rx: float, ry: float, rot: float, large: bool, sweep: bool, p1: Point
) -> list[Point]:
    """Arco SVG (parametrización por extremos, apéndice F.6 de SVG)."""
    rx, ry = abs(rx), abs(ry)
    if not rx or not ry or p0 == p1:
        return [p1]
    phi = math.radians(rot)
    cos, sin = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1 = cos * dx + sin * dy
    y1 = -sin * dx + cos * dy
    if (scale := x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)) > 1:
        rx, ry = rx * math.sqrt(scale), ry * math.sqrt(scale)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    k = math.sqrt(max(num, 0) / den) * (-1 if large == sweep else 1)
    cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
    cx = cos * cx1 - sin * cy1 + (p0[0] + p1[0]) / 2
    cy = sin * cx1 + cos * cy1 + (p0[1] + p1[1]) / 2
    a0 = math.atan2((y1 - cy1) / ry, (x1 - cx1) / rx)
    a1 = math.atan2((-y1 - cy1) / ry, (-x1 - cx1) / rx)
    delta = a1 - a0
    if sweep and delta < 0:
        delta += 2 * math.pi
    elif not sweep and delta > 0:
        delta -= 2 * math.pi
    steps = max(4, math.ceil(abs(delta) / (math.pi / 16)))
    out = []
    for i in range(1, steps + 1):
        a = a0 + delta * i / steps
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cos * x - sin * y + cx, sin * x + cos * y + cy))
    out[-1] = p1
    return out


def _fill_nonzero(
    draw: ImageDraw.ImageDraw, polys: list[list[Point]], scale: float, size: int
) -> None:
    """Relleno por la regla nonzero de SVG, por líneas de barrido."""
    edges = []
    for poly in polys:
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1], strict=True):
            if y0 != y1:
                edges.append((x0 * scale, y0 * scale, x1 * scale, y1 * scale))
    for row in range(size):
        y = row + 0.5
        hits = []
        for x0, y0, x1, y1 in edges:
            if (y0 <= y < y1) or (y1 <= y < y0):
                x = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                hits.append((x, 1 if y1 > y0 else -1))
        hits.sort()
        winding = 0
        for (x, d), (nx, _) in itertools.pairwise(hits):
            winding += d
            if winding and round(nx) > round(x):
                draw.line(((round(x), row), (round(nx) - 1, row)), fill=255)
