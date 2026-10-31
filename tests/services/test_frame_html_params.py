"""Template parameters are coerced to their declared types.

A placeholder such as ``{{title_font_size:number=72}}`` sits inside a
``<style>`` block, where HTML escaping changes nothing. ``coerce_param``
accepts only values of the declared type there (number, color, bool) and puts
the template default in place of anything else. Text parameters keep the
escaping of ``fill_value``.
"""

import math
from pathlib import Path

import pytest

from pixelle_video.services.frame_html import HTMLFrameGenerator, coerce_param

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"

CSS_VALUE = '72px; background-image: url("https://example.com/x.png")'


# ---------------------------------------------------------------- number


@pytest.mark.parametrize(
    "value, expected",
    [
        (64, "64"),
        (0, "0"),
        (-5, "-5"),
        (72.5, "72.5"),
        ("64", "64"),
        (" 64 ", "64"),
        ("72.5", "72.5"),
        ("-1.25", "-1.25"),
        (".5", ".5"),
    ],
)
def test_number_accepts_numbers(value, expected):
    assert coerce_param("number", value, "72") == expected


@pytest.mark.parametrize(
    "value",
    [
        CSS_VALUE,
        "72px",
        "72;",
        "1e3",
        "0x10",
        "",
        "72 72",
        "calc(1px + 2px)",
        True,
        False,
        None,
        math.nan,
        math.inf,
        [72],
        {"v": 72},
    ],
)
def test_number_rejects_other_values(value):
    assert coerce_param("number", value, "72") == "72"


# ---------------------------------------------------------------- color


@pytest.mark.parametrize(
    "value",
    [
        "#fff",
        "#FFFA",
        "#764ba2",
        "#764ba2cc",
        "rgb(1, 2, 3)",
        "rgba(255,0,0,0.5)",
        "rgb(10% 20% 30% / 50%)",
        "hsl(120deg, 50%, 25%)",
        "hsla(120, 50%, 25%, .3)",
        "red",
        "RebeccaPurple",
        "transparent",
    ],
)
def test_color_accepts_colors(value):
    assert coerce_param("color", value, "#764ba2") == value


@pytest.mark.parametrize(
    "value",
    [
        "red; background-image: url(x)",
        CSS_VALUE,
        "#12345",
        "#ggg",
        "764ba2",
        "rgb(1, 2)",
        "rgb(1, 2, var(--x))",
        "rgb(1, 2, 3); color: red",
        "url(x)",
        "notacolor",
        "</style><b>",
        "",
        None,
        0x764BA2,
        True,
    ],
)
def test_color_rejects_other_values(value):
    assert coerce_param("color", value, "#764ba2") == "#764ba2"


# ---------------------------------------------------------------- bool


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "true"),
        (False, "false"),
        ("true", "true"),
        ("FALSE", "false"),
        ("yes", "true"),
        ("off", "false"),
        ("1", "true"),
        ("0", "false"),
    ],
)
def test_bool_accepts_booleans(value, expected):
    assert coerce_param("bool", value, "false") == expected


@pytest.mark.parametrize("value", ["maybe", "true; x", 1, 0, None, ""])
def test_bool_rejects_other_values(value):
    assert coerce_param("bool", value, "false") == "false"


# ---------------------------------------------------------------- text


@pytest.mark.parametrize("declared_type", ["text", "unknown"])
def test_text_keeps_the_escaped_path(declared_type):
    assert coerce_param(declared_type, "<b>a & b</b>", "x", param_name="author") == (
        "&lt;b&gt;a &amp; b&lt;/b&gt;"
    )
    assert coerce_param(declared_type, CSS_VALUE, "x", param_name="author") == (
        "72px; background-image: url(&quot;https://example.com/x.png&quot;)"
    )


def test_rejected_value_is_logged_at_debug(caplog):
    from loguru import logger

    handler_id = logger.add(caplog.handler, level="DEBUG", format="{level} {message}")
    try:
        assert coerce_param("number", CSS_VALUE, "72", param_name="title_font_size") == "72"
    finally:
        logger.remove(handler_id)

    [record] = [r for r in caplog.records if "title_font_size" in r.getMessage()]
    assert record.levelname == "DEBUG"
    assert "not a valid number" in record.getMessage()


# ---------------------------------------------------------------- fill point


def _generator(tmp_path, body: str) -> HTMLFrameGenerator:
    template = tmp_path / "1080x1920" / "image_test.html"
    template.parent.mkdir(exist_ok=True)
    template.write_text(body, encoding="utf-8")
    return HTMLFrameGenerator(str(template))


def test_declared_type_applies_to_every_placeholder_of_that_name(tmp_path):
    generator = _generator(
        tmp_path,
        "<style>h1{font-size:{{size:number=72}}px} h2{font-size:{{size}}px}"
        " h3{color:{{tint:color=#000}}}</style><p>{{size}} {{note}}</p>",
    )

    filled = generator._replace_parameters(
        generator.template, {"size": CSS_VALUE, "tint": "#abcdef", "note": "<i>"}
    )

    assert filled == (
        "<style>h1{font-size:72px} h2{font-size:px} h3{color:#abcdef}</style>"
        "<p> &lt;i&gt;</p>"
    )


def test_valid_typed_values_are_inserted(tmp_path):
    generator = _generator(
        tmp_path,
        "<style>h1{font-size:{{size:number=72}}px;color:{{tint:color=#000}}}</style>"
        "<script>const on = {{flag:bool=false}};</script>",
    )

    filled = generator._replace_parameters(
        generator.template, {"size": 64.5, "tint": "rgb(1, 2, 3)", "flag": True}
    )

    assert filled == (
        "<style>h1{font-size:64.5px;color:rgb(1, 2, 3)}</style>"
        "<script>const on = true;</script>"
    )


async def test_render_puts_only_the_default_into_css(browser, tmp_path):
    generator = HTMLFrameGenerator(str(TEMPLATES / "1080x1920" / "image_modern.html"))

    await generator.generate_frame(
        title="Title",
        text="Text",
        image="https://example.com/a.png",
        ext={
            "index": 1,
            "title_font_size": CSS_VALUE,
            "accent_color": 'red; background-image: url("https://example.com/y.png")',
        },
        output_path=str(tmp_path / "frame.png"),
    )

    [page] = browser.pages
    style = page[page.index("<style>"): page.index("</style>")]
    assert "font-size: 72px;" in style
    assert "background: #764ba2;" in style
    assert "example.com" not in style
    assert "background-image: url(" not in style
