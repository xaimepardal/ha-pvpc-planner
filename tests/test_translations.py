"""Los idiomas del backend y del panel tienen las mismas claves."""

import json
from pathlib import Path
import re

from custom_components.pvpc_planner.render import TEXTS

COMPONENT = Path(__file__).parents[1] / "custom_components" / "pvpc_planner"
LANGS = ("en", "es", "gl")


def _keys(tree: dict, prefix: str = "") -> set[str]:
    out = set()
    for key, value in tree.items():
        path = f"{prefix}{key}"
        out |= _keys(value, f"{path}.") if isinstance(value, dict) else {path}
    return out


def test_backend_translations() -> None:
    folder = COMPONENT / "translations"
    keys = {
        lang: _keys(json.loads((folder / f"{lang}.json").read_text())) for lang in LANGS
    }
    assert keys["es"] == keys["en"]
    assert keys["gl"] == keys["en"]


def test_panel_translations() -> None:
    src = (COMPONENT / "frontend" / "pvpc-planner-panel.js").read_text()
    blocks = dict(re.findall(r"^  (\w+): \{\n(.*?)^  \},", src, re.M | re.S))
    keys = {lang: set(re.findall(r"^    (\w+):", blocks[lang], re.M)) for lang in LANGS}
    assert keys["en"]
    assert keys["es"] == keys["en"]
    assert keys["gl"] == keys["en"]


def test_image_texts() -> None:
    assert set(TEXTS) == set(LANGS)
    for lang in LANGS:
        assert TEXTS[lang].keys() == TEXTS["en"].keys()
        assert len(TEXTS[lang]["weekdays"].split()) == 7
