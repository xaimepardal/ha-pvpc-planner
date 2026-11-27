"""Dibujo de la tabla y rasterizado de iconos MDI."""

from datetime import date
from io import BytesIO
import math
import sys
from unittest.mock import patch

from PIL import Image, ImageFont
import pytest

from custom_components.pvpc_planner import mdi, render
from custom_components.pvpc_planner.render import (
    Cell,
    Device,
    Table,
    layout,
    render_png,
    texts,
)

CAR = Device("Coche", "mdi:car-electric")
ODD = Device("Raro", "custom:odd")
LONG = Device("Calentador de agua del baño", "mdi:water-boiler")
DEVICES = {1: (CAR,), 2: (CAR, ODD), 3: (CAR, CAR, CAR, ODD), 20: (ODD,), 21: (LONG,)}
LEVELS = {0: "cheap", 1: "cheap", 20: "expensive", 21: "expensive"}


def _table(lang: str = "es", hours: int = 24, size=(800, 480)) -> Table:
    cells = tuple(
        Cell(
            hour=h % 24,
            price=0.1 + h / 100,
            level=LEVELS.get(h),
            past=h < 10,
            now=h == 10,
            auto=h in (2, 20),
            devices=DEVICES.get(h, ()),
        )
        for h in range(hours)
    )
    return Table(date(2026, 11, 26), True, lang, cells, *size)


def _open(png: bytes, size=(800, 480)) -> Image.Image:
    img = Image.open(BytesIO(png))
    assert img.size == size
    assert img.mode == "P"
    return img


def _box(index: int) -> tuple[int, int, int, int]:
    return layout(800, 480, 24)[1][index]


@pytest.mark.parametrize("lang", ["es", "en", "gl", "en-GB", "fr"])
def test_render_languages(lang: str) -> None:
    _open(render_png(_table(lang)))


def test_texts_fallback() -> None:
    assert texts("en-GB") is texts("en")
    assert texts("fr") is texts("en")
    assert texts("gl")["today"] == "Hoxe"


def test_one_bit() -> None:
    """Recuadros y flechas de tendencia siguen ahí al pasar a blanco y negro."""
    bw = (
        _open(render_png(_table()))
        .convert("RGB")
        .convert("1", dither=Image.Dither.NONE)
    )

    def black(box: tuple[int, int, int, int]) -> int:
        return sum(1 for v in bw.crop(box).get_flattened_data() if not v)

    for i in range(24):
        x0, y0, x1, _ = _box(i)
        assert black((x0 + 20, y0, x1 - 20, y0 + 2)) == (x1 - x0 - 40) * 2

    # Zona a la derecha del precio: flecha solo en horas caras o baratas.
    def trend(i: int) -> int:
        _, y0, x1, _ = _box(i)
        return black((x1 - 30, y0 + 40, x1 - 4, y0 + 72))

    assert trend(0) > 40
    assert trend(20) > 40
    assert trend(23) == 0


def test_render_variants() -> None:
    # Día de 25 horas: una fila más.
    _open(render_png(_table(hours=25)))
    # Sin precios.
    _open(render_png(Table(date(2026, 11, 27), False, "gl", (), 800, 480)))


@pytest.mark.parametrize(
    ("size", "cols"),
    [((800, 480), 6), ((480, 800), 4), ((296, 128), 8), ((100, 100), 5)],
)
def test_sizes(size: tuple[int, int], cols: int) -> None:
    _open(render_png(_table(size=size)), size)
    header, boxes = layout(*size, 24)
    assert len({b[0] for b in boxes}) == cols
    width, height = size
    assert all(b[1] >= header and b[2] <= width and b[3] <= height for b in boxes)


def test_fit() -> None:
    font = render._font(15)
    assert render._fit("Coche", font, 200) == "Coche"
    short = render._fit(LONG.name, font, 60)
    assert short.endswith("…")
    assert font.getlength(short) <= 60
    assert render._fit("abc", font, 1) == "…"


def test_font_fallback() -> None:
    render._font.cache_clear()
    try:
        truetype = ImageFont.truetype

        def no_woff2(font, *args, **kwargs):
            if str(font).endswith(".woff2"):
                raise OSError
            return truetype(font, *args, **kwargs)

        with patch.object(ImageFont, "truetype", no_woff2):
            assert render._font(12) is not None
            _open(render_png(_table()))
        render._font.cache_clear()
        with patch.dict(sys.modules, {"hass_frontend": None}):
            assert render._font(13) is not None
    finally:
        render._font.cache_clear()


def test_icon_mask() -> None:
    mask = mdi.icon_mask("mdi:robot", 24)
    assert mask.size == (24, 24)
    assert 0 < sum(mask.get_flattened_data()) < 24 * 24 * 255
    assert mdi.icon_mask("mdi:does-not-exist", 24) is None
    assert mdi.icon_mask("hass:robot", 24) is None


@pytest.fixture
def no_cache():
    for fn in (mdi._mdi_dir, mdi._parts, mdi._chunk, mdi.icon_mask):
        fn.cache_clear()
    yield
    for fn in (mdi._mdi_dir, mdi._parts, mdi._chunk, mdi.icon_mask):
        fn.cache_clear()


@pytest.mark.usefixtures("no_cache")
def test_icons_without_frontend(tmp_path) -> None:
    with patch.dict(sys.modules, {"hass_frontend": None}):
        assert mdi.icon_path("mdi:robot") is None
    mdi._mdi_dir.cache_clear()
    mdi._parts.cache_clear()
    with patch("hass_frontend.where", return_value=tmp_path):
        assert mdi.icon_path("mdi:robot") is None


def test_path_commands() -> None:
    polys = mdi._subpaths(
        "M1 1h4v4H1zm6 0l2 0 0 2-2 0z"
        "M10 10c1 0 2 1 2 2s-1 2-2 2S8 13 8 12q0-1 1-1t1 0Q11 9 12 10T14 10z"
        "M15 15a2 2 0 01 4 0A2 2 0 0 0 15 15z"
        "M1 20L1 20 2 21 3 20V22"
    )
    assert len(polys) == 5
    assert polys[0][:4] == [(1, 1), (5, 1), (5, 5), (1, 5)]
    assert polys[1][0] == (7, 1)
    # Un arco de media vuelta pasa por el punto más alejado.
    assert any(math.isclose(y, 13, abs_tol=0.01) for _, y in polys[3])
    # Coordenadas implícitas tras M como líneas.
    assert polys[4][-2:] == [(3, 20), (3, 22)]


def test_path_errors() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        mdi._subpaths("M0 0X1")
    with pytest.raises(ValueError, match="Number expected"):
        mdi._subpaths("M0 0C1")


def test_arc_edge_cases() -> None:
    assert mdi._arc((0, 0), 0, 1, 0, False, True, (2, 2)) == [(2, 2)]
    assert mdi._arc((1, 1), 1, 1, 0, False, True, (1, 1)) == [(1, 1)]
    # Radio demasiado pequeño: se amplía hasta unir los extremos.
    pts = mdi._arc((0, 0), 1, 1, 0, False, False, (10, 0))
    assert pts[-1] == (10, 0)
    assert any(math.isclose(abs(y), 5, abs_tol=0.01) for _, y in pts)
