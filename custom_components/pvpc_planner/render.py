"""Tabla del día como PNG de 800x480 para pantallas (e-ink, ESPHome).

Fondo blanco, celdas con recuadro negro y una flecha de tendencia junto al
precio en las horas caras y baratas: se lee igual pasada a 1 bit (umbral 128).
Bloqueante (Pillow y disco): llamar desde el executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from io import BytesIO
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .mdi import icon_mask

WIDTH, HEIGHT = 800, 480
COLUMNS = 6
HEADER = 40
PAD = 6
MAX_ICONS = 3
ROBOT = "mdi:robot"

# Todo lo que no es fondo queda negro a 1 bit (luminancia < 128).
INK = (0, 0, 0)
PAST = (117, 117, 117)
PAPER = (255, 255, 255)
PRIMARY = (1, 87, 155)
# Nivel: (icono, color).
LEVELS = {
    "cheap": ("mdi:trending-down", (46, 125, 50)),
    "expensive": ("mdi:trending-up", (211, 47, 47)),
}
RADIUS = 6
BORDER = 2
NOW_BORDER = 5
PALETTE_COLORS = 32

TEXTS = {
    "en": {
        "today": "Today",
        "tomorrow": "Tomorrow",
        "no_prices": "No prices for this day.",
        "title": "{label}, {weekday} {day}",
        "weekdays": "Monday Tuesday Wednesday Thursday Friday Saturday Sunday",
        "decimal": ".",
    },
    "es": {
        "today": "Hoy",
        "tomorrow": "Mañana",
        "no_prices": "Sin precios para este día.",
        "title": "{label}, {weekday} {day}",
        "weekdays": "lunes martes miércoles jueves viernes sábado domingo",
        "decimal": ",",
    },
    "gl": {
        "today": "Hoxe",
        "tomorrow": "Mañá",
        "no_prices": "Sen prezos para este día.",
        "title": "{label}, {weekday} {day}",
        "weekdays": "luns martes mércores xoves venres sábado domingo",
        "decimal": ",",
    },
}


@dataclass(frozen=True, slots=True)
class Device:
    name: str
    icon: str


@dataclass(frozen=True, slots=True)
class Cell:
    hour: int
    price: float
    # "cheap", "expensive" o None.
    level: str | None
    past: bool
    now: bool
    auto: bool
    devices: tuple[Device, ...]


@dataclass(frozen=True, slots=True)
class Table:
    """Todo lo que se dibuja: dos tablas iguales dan la misma imagen."""

    day: date
    today: bool
    lang: str
    cells: tuple[Cell, ...]


def texts(lang: str) -> dict[str, str]:
    return TEXTS.get(lang) or TEXTS.get(lang.split("-")[0]) or TEXTS["en"]


def render(table: Table) -> Image.Image:
    return _Painter(table).paint()


def render_png(table: Table) -> bytes:
    """PNG con paleta reducida."""
    img = render(table).quantize(PALETTE_COLORS, dither=Image.Dither.NONE)
    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


@lru_cache(maxsize=16)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    try:
        import hass_frontend

        name = "Roboto-Bold.woff2" if bold else "Roboto-Medium.woff2"
        path = Path(hass_frontend.where()) / "static" / "fonts" / "roboto" / name
        return ImageFont.truetype(str(path), size)
    except (ImportError, OSError):
        # Sin la fuente del frontend o sin soporte WOFF2 en FreeType.
        return ImageFont.load_default(size)


def _fit(text: str, font: ImageFont.FreeTypeFont, width: float) -> str:
    """Recorta con "…" para que quepa en `width`."""
    if font.getlength(text) <= width:
        return text
    while text and font.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


type Box = tuple[int, int, int, int]
type Color = tuple[int, int, int]


class _Painter:
    def __init__(self, table: Table) -> None:
        self.table = table
        self.t = texts(table.lang)
        self.img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
        self.draw = ImageDraw.Draw(self.img)

    def paint(self) -> Image.Image:
        title = _font(26, True)
        self.draw.text((WIDTH / 2, HEADER / 2), self.title(), INK, title, "mm")
        cells = self.table.cells
        if not cells:
            center = (WIDTH / 2, (HEIGHT + HEADER) / 2)
            self.draw.text(center, self.t["no_prices"], INK, _font(24), "mm")
            return self.img
        rows = math.ceil(len(cells) / COLUMNS)
        w = (WIDTH - PAD * (COLUMNS + 1)) / COLUMNS
        h = (HEIGHT - HEADER - PAD * (rows + 1)) / rows
        for i, cell in enumerate(cells):
            row, col = divmod(i, COLUMNS)
            x = PAD + col * (w + PAD)
            y = HEADER + PAD + row * (h + PAD)
            self.cell(cell, (round(x), round(y), round(x + w), round(y + h)))
        return self.img

    def title(self) -> str:
        day = self.table.day
        return self.t["title"].format(
            label=self.t["today" if self.table.today else "tomorrow"],
            weekday=self.t["weekdays"].split()[day.weekday()],
            day=day.day,
        )

    def cell(self, cell: Cell, box: Box) -> None:
        width = NOW_BORDER if cell.now else BORDER
        self.draw.rounded_rectangle(box, RADIUS, PAPER, INK, width)
        ink = PAST if cell.past else INK
        x0, y0, x1, y1 = box
        x = x0 + 10
        self.draw.text((x, y0 + 4), f"{cell.hour:02d}:00", ink, _font(38, True))
        price = f"{cell.price:.4f}".replace(".", self.t["decimal"])
        font = _font(24, True)
        self.draw.text((x, y0 + 44), price, ink, font)
        if cell.level:
            icon, color = LEVELS[cell.level]
            xy = (x + font.getlength(price) + 3, y0 + 41)
            self.icon(icon, "", xy, 30, color, bold=True)
        if cell.auto:
            self.icon(ROBOT, "", (x1 - 30, y1 - 29), 22, ink)
        if cell.devices:
            fill = PAST if cell.past else PRIMARY
            self.devices(cell.devices, box, fill, ink, reserve=32 if cell.auto else 0)

    def icon(
        self, icon: str, name: str, xy, size: int, fill: Color, bold: bool = False
    ) -> None:
        """Icono MDI o, si no se encuentra, la inicial del nombre en un círculo.

        `bold` engrosa el trazo para que no se pierda en e-ink.
        """
        x, y = round(xy[0]), round(xy[1])
        if (mask := icon_mask(icon, size)) is not None:
            if bold:
                mask = mask.filter(ImageFilter.MaxFilter(3))
            self.img.paste(fill, (x, y, x + size, y + size), mask)
            return
        circle = (x + 1, y + 1, x + size - 2, y + size - 2)
        self.draw.ellipse(circle, None, fill, 2)
        initial = (name[:1] or "?").upper()
        font = _font(round(size * 0.55), True)
        self.draw.text((x + size / 2, y + size / 2), initial, fill, font, "mm")

    def devices(
        self, items: tuple[Device, ...], box: Box, fill: Color, ink: Color, reserve: int
    ) -> None:
        """Uno: icono y nombre. Varios: iconos, y desde MAX_ICONS el resto como "+N"."""
        x0, _, x1, y1 = box
        size = 22
        x, y = x0 + 10, y1 - size - 7
        if len(items) == 1:
            dev = items[0]
            self.icon(dev.icon, dev.name, (x, y), size, fill)
            font = _font(15)
            # `reserve`: hueco para el robot de la esquina.
            name = _fit(dev.name, font, x1 - x - size - 14 - reserve)
            self.draw.text((x + size + 5, y + size / 2), name, ink, font, "lm")
            return
        shown = items[: MAX_ICONS - 1] if len(items) > MAX_ICONS else items
        for dev in shown:
            self.icon(dev.icon, dev.name, (x, y), size, fill)
            x += size + 4
        if rest := len(items) - len(shown):
            self.draw.text((x, y + size / 2), f"+{rest}", ink, _font(17, True), "lm")
