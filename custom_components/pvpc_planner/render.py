"""Tabla del día como PNG para pantallas (e-ink, ESPHome), del tamaño que se pida.

Fondo blanco, celdas con recuadro negro y el precio en verde o rojo con una
flecha de tendencia en las horas baratas y caras: se lee igual pasada a 1 bit
(umbral 128). La rejilla elige las columnas según la orientación y todo escala
con el tamaño de la celda. Bloqueante (Pillow y disco): llamar desde el executor.
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

# Medidas de referencia: las de 800x480, una celda de 126x102 (6x4).
REF_AREA = 800 * 480
REF_CELL = (126, 102)
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
    width: int
    height: int


def texts(lang: str) -> dict[str, str]:
    return TEXTS.get(lang) or TEXTS.get(lang.split("-")[0]) or TEXTS["en"]


type Box = tuple[int, int, int, int]
type Color = tuple[int, int, int]


def layout(width: int, height: int, count: int) -> tuple[int, list[Box]]:
    """Alto de la cabecera y recuadro de cada celda.

    Columnas: las que dejan la celda más parecida a la de referencia, sin
    columnas de más (24 horas: 6x4 o 4x6, pero no 7x4).
    """
    scale = math.sqrt(width * height / REF_AREA)
    header = round(HEADER * scale)
    pad = max(2, round(PAD * scale))
    if not count:
        return header, []
    target = REF_CELL[0] / REF_CELL[1]

    def cell(cols: int) -> tuple[float, float]:
        rows = math.ceil(count / cols)
        return (
            (width - pad * (cols + 1)) / cols,
            (height - header - pad * (rows + 1)) / rows,
        )

    cols = min(
        (
            c
            for c in range(1, count + 1)
            if math.ceil(count / math.ceil(count / c)) == c
        ),
        key=lambda c: abs(math.log(max(cell(c)[0], 1) / max(cell(c)[1], 1) / target)),
    )
    w, h = cell(cols)
    boxes = []
    for i in range(count):
        row, col = divmod(i, cols)
        x = pad + col * (w + pad)
        y = header + pad + row * (h + pad)
        boxes.append((round(x), round(y), round(x + w), round(y + h)))
    return header, boxes


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


class _Painter:
    def __init__(self, table: Table) -> None:
        self.table = table
        self.t = texts(table.lang)
        self.size = (table.width, table.height)
        self.img = Image.new("RGB", self.size, PAPER)
        self.draw = ImageDraw.Draw(self.img)
        # Escala de la celda respecto a la de referencia.
        self.k = 1.0

    def px(self, value: float) -> int:
        return max(1, round(value * self.k))

    def paint(self) -> Image.Image:
        width, height = self.size
        header, boxes = layout(width, height, len(self.table.cells))
        title = _font(max(6, round(header * 0.65)), True)
        self.draw.text((width / 2, header / 2), self.title(), INK, title, "mm")
        if not boxes:
            center = (width / 2, (height + header) / 2)
            self.draw.text(center, self.t["no_prices"], INK, title, "mm")
            return self.img
        x0, y0, x1, y1 = boxes[0]
        self.k = min((x1 - x0) / REF_CELL[0], (y1 - y0) / REF_CELL[1])
        for cell, box in zip(self.table.cells, boxes, strict=True):
            self.cell(cell, box)
        return self.img

    def title(self) -> str:
        day = self.table.day
        return self.t["title"].format(
            label=self.t["today" if self.table.today else "tomorrow"],
            weekday=self.t["weekdays"].split()[day.weekday()],
            day=day.day,
        )

    def cell(self, cell: Cell, box: Box) -> None:
        px = self.px
        border = px(5) if cell.now else px(2)
        self.draw.rounded_rectangle(box, px(6), PAPER, INK, border)
        ink = PAST if cell.past else INK
        x0, y0, x1, y1 = box
        x = x0 + px(10)
        self.draw.text((x, y0 + px(4)), f"{cell.hour:02d}:00", ink, _font(px(38), True))
        price = f"{cell.price:.4f}".replace(".", self.t["decimal"])
        font = _font(px(24), True)
        icon, color = LEVELS.get(cell.level, (None, ink))
        self.draw.text((x, y0 + px(44)), price, color, font)
        if icon:
            xy = (x + font.getlength(price) + px(3), y0 + px(41))
            self.icon(icon, "", xy, px(30), color, bold=True)
        if cell.auto:
            self.icon(ROBOT, "", (x1 - px(30), y1 - px(29)), px(22), ink)
        if cell.devices:
            fill = PAST if cell.past else PRIMARY
            reserve = px(32) if cell.auto else 0
            self.devices(cell.devices, box, fill, ink, reserve)

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
        font = _font(max(1, round(size * 0.55)), True)
        self.draw.text((x + size / 2, y + size / 2), initial, fill, font, "mm")

    def devices(
        self, items: tuple[Device, ...], box: Box, fill: Color, ink: Color, reserve: int
    ) -> None:
        """Uno: icono y nombre. Varios: iconos, y desde MAX_ICONS el resto como "+N"."""
        px = self.px
        x0, _, x1, y1 = box
        size = px(22)
        x, y = x0 + px(10), y1 - size - px(7)
        if len(items) == 1:
            dev = items[0]
            self.icon(dev.icon, dev.name, (x, y), size, fill)
            font = _font(px(15))
            # `reserve`: hueco para el robot de la esquina.
            name = _fit(dev.name, font, x1 - x - size - px(14) - reserve)
            self.draw.text((x + size + px(5), y + size / 2), name, ink, font, "lm")
            return
        shown = items[: MAX_ICONS - 1] if len(items) > MAX_ICONS else items
        for dev in shown:
            self.icon(dev.icon, dev.name, (x, y), size, fill)
            x += size + px(4)
        if rest := len(items) - len(shown):
            font = _font(px(17), True)
            self.draw.text((x, y + size / 2), f"+{rest}", ink, font, "lm")
