"""Tabla del día como PNG de 800x480 para pantallas (e-ink, ESPHome).

Las horas caras van rayadas y las baratas con borde punteado, con colores que
se separan bien del blanco: la imagen se sigue entendiendo pasada a 1 bit.
Bloqueante (Pillow y disco): llamar desde el executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from io import BytesIO
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .mdi import icon_mask

WIDTH, HEIGHT = 800, 480
COLUMNS = 6
HEADER = 40
PAD = 6
MAX_ICONS = 3
ROBOT = "mdi:robot"

# Tema claro del panel, oscureciendo lo que debe quedar negro a 1 bit
# (luminancia < 128) y aclarando los fondos (> 200).
INK = (33, 33, 33)
PAST = (117, 117, 117)
LINE = (189, 189, 189)
PAPER = (250, 250, 250)
CARD = (255, 255, 255)
PRIMARY = (1, 87, 155)
WHITE = (255, 255, 255)
# Nivel: (marca, fondo).
LEVELS = {
    "cheap": ((46, 125, 50), (234, 246, 235)),
    "expensive": ((211, 47, 47), (253, 236, 234)),
}
RADIUS = 10
PALETTE_COLORS = 32

TEXTS = {
    "en": {
        "today": "Today",
        "tomorrow": "Tomorrow",
        "no_prices": "No prices for this day.",
        "auto": "By template",
        "date": "{weekday} {month}/{day}",
        "weekdays": "Mon Tue Wed Thu Fri Sat Sun",
        "decimal": ".",
    },
    "es": {
        "today": "Hoy",
        "tomorrow": "Mañana",
        "no_prices": "Sin precios para este día.",
        "auto": "Por plantilla",
        "date": "{weekday} {day}/{month}",
        "weekdays": "lun mar mié jue vie sáb dom",
        "decimal": ",",
    },
    "gl": {
        "today": "Hoxe",
        "tomorrow": "Mañá",
        "no_prices": "Sen prezos para este día.",
        "auto": "Por modelo",
        "date": "{weekday} {day}/{month}",
        "weekdays": "lun mar mér xov ven sáb dom",
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
    unit: str
    templates: bool
    cells: tuple[Cell, ...]


def texts(lang: str) -> dict[str, str]:
    return TEXTS.get(lang) or TEXTS.get(lang.split("-")[0]) or TEXTS["en"]


def render_png(table: Table) -> bytes:
    """PNG con paleta reducida."""
    img = _Painter(table).paint().quantize(PALETTE_COLORS, dither=Image.Dither.NONE)
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
        self.header()
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
        date_text = self.t["date"].format(
            weekday=self.t["weekdays"].split()[day.weekday()],
            day=day.day,
            month=day.month,
        )
        return f"{self.t['today' if self.table.today else 'tomorrow']} · {date_text}"

    def header(self) -> None:
        self.draw.rectangle((0, 0, WIDTH, HEADER), PRIMARY)
        y = HEADER / 2
        self.draw.text((PAD + 4, y), self.title(), WHITE, _font(20, True), "lm")
        # Leyenda, de derecha a izquierda.
        font = _font(15)
        items: list[tuple[str, str | None]] = [
            ("$", "cheap"),
            ("$$$", "expensive"),
            (self.t["auto"], ROBOT),
            (self.table.unit, None),
        ]
        if not self.table.templates:
            del items[2]
        x = WIDTH - PAD - 4
        for label, mark in reversed(items):
            x -= font.getlength(label)
            self.draw.text((x, y), label, WHITE, font, "lm")
            if mark == ROBOT:
                x -= 22
                self.icon(ROBOT, "", (x, y - 9), 18, WHITE, PRIMARY)
            elif mark:
                x -= 24
                self.marker((round(x), round(y) - 9, round(x) + 18, round(y) + 9), mark)
            x -= 16

    def marker(self, box: Box, level: str) -> None:
        """Muestra de la leyenda: mismo marcado que las celdas."""
        accent, tint = LEVELS[level]
        self.draw.rectangle(box, tint)
        if level == "expensive":
            self.stripes(box, accent)
            self.draw.rectangle(box, outline=accent, width=2)
        else:
            self.dots(box, accent, 0, 3, 5)

    def cell(self, cell: Cell, box: Box) -> None:
        bg = CARD
        if cell.level:
            accent, bg = LEVELS[cell.level]
            self.draw.rounded_rectangle(box, RADIUS, bg)
            if cell.level == "expensive":
                self.stripes(box, accent)
                self.draw.rounded_rectangle(box, RADIUS, outline=accent, width=2)
            else:
                self.dots(box, accent, RADIUS)
        else:
            self.draw.rounded_rectangle(box, RADIUS, CARD, LINE)
        if cell.now:
            self.draw.rounded_rectangle(box, RADIUS, outline=PRIMARY, width=4)

        # Sobre las rayas, el texto y los iconos llevan una placa del color de fondo.
        plate = bg if cell.level == "expensive" else None
        ink = PAST if cell.past else INK
        x0, y0, x1, _y1 = box
        self.text((x0 + 9, y0 + 7), f"{cell.hour:02d}:00", _font(19, True), ink, plate)
        price = f"{cell.price:.4f}".replace(".", self.t["decimal"])
        self.text((x0 + 9, y0 + 30), price, _font(29, True), ink, plate)
        if cell.auto:
            self.icon(ROBOT, "", (x1 - 25, y0 + 7), 18, ink, plate)
        if cell.devices:
            self.devices(cell.devices, box, PAST if cell.past else PRIMARY, ink, plate)

    def stripes(self, box: Box, color: Color) -> None:
        x0, y0, x1, y1 = box
        w, h = x1 - x0 + 1, y1 - y0 + 1
        mask = Image.new("1", (w, h))
        draw = ImageDraw.Draw(mask)
        for k in range(-h, w, 10):
            draw.line((k, h, k + h, 0), 1, 3)
        # Recorte a las esquinas redondeadas.
        clip = Image.new("1", (w, h))
        ImageDraw.Draw(clip).rounded_rectangle((0, 0, w - 1, h - 1), RADIUS, 1)
        self.img.paste(color, (x0, y0), ImageChops.logical_and(mask, clip))

    def dots(
        self, box: Box, color: Color, radius: int, dot: int = 4, step: int = 8
    ) -> None:
        x0, y0, x1, y1 = box
        for x in range(x0 + radius, x1 - radius - dot + 2, step):
            self.draw.rectangle((x, y0, x + dot - 1, y0 + dot - 1), color)
            self.draw.rectangle((x, y1 - dot + 1, x + dot - 1, y1), color)
        for y in range(y0 + radius, y1 - radius - dot + 2, step):
            self.draw.rectangle((x0, y, x0 + dot - 1, y + dot - 1), color)
            self.draw.rectangle((x1 - dot + 1, y, x1, y + dot - 1), color)

    def text(
        self, xy, text: str, font, fill: Color, plate: Color | None, anchor="la"
    ) -> None:
        if plate:
            x0, y0, x1, y1 = self.draw.textbbox(xy, text, font, anchor)
            self.draw.rectangle((x0 - 3, y0 - 3, x1 + 3, y1 + 3), plate)
        self.draw.text(xy, text, fill, font, anchor)

    def icon(
        self, icon: str, name: str, xy, size: int, fill: Color, plate: Color | None
    ) -> None:
        """Icono MDI o, si no se encuentra, la inicial del nombre en un círculo."""
        x, y = round(xy[0]), round(xy[1])
        area = (x, y, x + size, y + size)
        if (mask := icon_mask(icon, size)) is not None:
            if plate:
                self.img.paste(plate, area, mask.filter(ImageFilter.MaxFilter(7)))
            self.img.paste(fill, area, mask)
            return
        circle = (x + 1, y + 1, x + size - 2, y + size - 2)
        self.draw.ellipse(circle, plate, fill, 2)
        initial = (name[:1] or "?").upper()
        font = _font(round(size * 0.55), True)
        self.draw.text((x + size / 2, y + size / 2), initial, fill, font, "mm")

    def devices(
        self,
        items: tuple[Device, ...],
        box: Box,
        fill: Color,
        ink: Color,
        plate: Color | None,
    ) -> None:
        """Uno: icono y nombre. Varios: iconos, y desde MAX_ICONS el resto como "+N"."""
        x0, _, x1, y1 = box
        size = 26
        x, y = x0 + 9, y1 - size - 8
        if len(items) == 1:
            dev = items[0]
            self.icon(dev.icon, dev.name, (x, y), size, fill, plate)
            font = _font(15)
            name = _fit(dev.name, font, x1 - x - size - 16)
            self.text((x + size + 6, y + size / 2), name, font, ink, plate, "lm")
            return
        shown = items[: MAX_ICONS - 1] if len(items) > MAX_ICONS else items
        for dev in shown:
            self.icon(dev.icon, dev.name, (x, y), size, fill, plate)
            x += size + 6
        if rest := len(items) - len(shown):
            self.text((x, y + size / 2), f"+{rest}", _font(17, True), ink, plate, "lm")
