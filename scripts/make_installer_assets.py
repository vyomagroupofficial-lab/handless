"""Generate the Windows icon and installer artwork from the bot logo.

Outputs (committed under packaging/):
  handless.ico          multi-size application icon
  wizard-large.bmp      Inno Setup side panel (welcome / finish pages)
  wizard-small.bmp      Inno Setup header badge (inner pages)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "src" / "handless" / "assets" / "handless-bot-withoutbg.png"
OUT = ROOT / "packaging"

PAPER = (250, 249, 245)
INK = (24, 24, 27)
MUTED = (113, 113, 122)


def _square_logo(size: int) -> Image.Image:
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(logo, ((size - logo.width) // 2, (size - logo.height) // 2), logo)
    return canvas


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    names = ["georgiab.ttf" if bold else "georgia.ttf", "segoeuib.ttf" if bold else "segoeui.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon() -> None:
    base = _square_logo(256)
    base.save(OUT / "handless.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def make_wizard_large(scale: int = 2) -> None:
    w, h = 164 * scale, 314 * scale
    img = Image.new("RGB", (w, h), PAPER)
    draw = ImageDraw.Draw(img)
    # subtle bottom band
    draw.rectangle([0, h - 70 * scale, w, h], fill=(243, 241, 234))
    logo = _square_logo(104 * scale)
    img.paste(logo, ((w - logo.width) // 2, 70 * scale), logo)
    title = _font(17 * scale, bold=True)
    sub = _font(10 * scale)
    for text, font, y, color in (
        ("Handless", title, 196 * scale, INK),
        ("Your desktop,", sub, 224 * scale, MUTED),
        ("without hands.", sub, 239 * scale, MUTED),
    ):
        tw = draw.textlength(text, font=font)
        draw.text(((w - tw) / 2, y), text, font=font, fill=color)
    img.save(OUT / "wizard-large.bmp")


def make_wizard_small(scale: int = 2) -> None:
    w, h = 55 * scale, 58 * scale
    img = Image.new("RGB", (w, h), (255, 255, 255))
    logo = _square_logo(46 * scale)
    img.paste(logo, ((w - logo.width) // 2, (h - logo.height) // 2), logo)
    img.save(OUT / "wizard-small.bmp")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    make_icon()
    make_wizard_large()
    make_wizard_small()
    print("Installer assets written to", OUT)
