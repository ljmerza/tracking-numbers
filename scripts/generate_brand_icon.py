"""Regenerate the HACS / Home Assistant brand assets for this integration.

Outputs (transparent PNGs, RGBA):

  custom_components/tracking_numbers/brand/icon.png        256x256
  custom_components/tracking_numbers/brand/icon@2x.png     512x512
  custom_components/tracking_numbers/brand/logo.png        landscape, 128 px tall
  custom_components/tracking_numbers/brand/logo@2x.png     landscape, 256 px tall

home-assistant/brands rules used here:
  - icon: square 256/512.
  - logo: shortest side 128-256 px (logo) / 256-512 px (@2x), landscape, trimmed.

Run with `python3 scripts/generate_brand_icon.py` from the repo root.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = REPO_ROOT / "custom_components" / "tracking_numbers" / "brand"

ACCENT = (3, 169, 244, 255)         # HA blue
ACCENT_SOFT = (3, 169, 244, 64)     # translucent fill for box body
TRANSPARENT = (0, 0, 0, 0)


def _box(draw: ImageDraw.ImageDraw, size: int) -> None:
    """Draw a stylised package on `draw` covering a `size`x`size` canvas."""
    s = size / 256  # scale factor relative to the 256 reference design

    # Outer cardboard box, rounded corners.
    left, top, right, bottom = 36 * s, 78 * s, 220 * s, 222 * s
    radius = 14 * s
    stroke = max(2, round(6 * s))
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=radius,
        fill=ACCENT_SOFT,
        outline=ACCENT,
        width=stroke,
    )

    # Lid seam (horizontal).
    seam_y = 122 * s
    draw.line(
        (left + stroke / 2, seam_y, right - stroke / 2, seam_y),
        fill=ACCENT,
        width=stroke,
    )

    # Tape strip (vertical, only on the lid section).
    tape_x = (left + right) / 2
    draw.line(
        (tape_x, top + stroke / 2, tape_x, seam_y),
        fill=ACCENT,
        width=stroke,
    )

    # Barcode-ish bars on the lower body, hinting at a tracking label.
    bar_top = 150 * s
    bar_bottom = 200 * s
    bars = [
        (78, 2), (88, 4), (100, 2), (110, 6), (126, 2),
        (134, 3), (146, 5), (160, 2), (170, 4), (184, 2),
    ]
    for x_ref, w_ref in bars:
        bx = x_ref * s
        bw = max(1, round(w_ref * s))
        draw.rectangle((bx, bar_top, bx + bw, bar_bottom), fill=ACCENT)


def _icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), TRANSPARENT)
    draw = ImageDraw.Draw(img)
    _box(draw, size)
    return img


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _logo(height: int) -> Image.Image:
    """Compose icon-glyph + wordmark, trimmed to fit (landscape)."""
    text = "Tracking Numbers"
    font = _load_font(int(height * 0.55))
    gap = int(height * 0.12)

    # Measure text bounds first so we can size the canvas.
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = measure.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    icon_size = height
    width = icon_size + gap + text_w + gap  # trailing padding ~= gap

    img = Image.new("RGBA", (width, height), TRANSPARENT)
    glyph = _icon(icon_size)
    img.paste(glyph, (0, 0), glyph)

    draw = ImageDraw.Draw(img)
    text_x = icon_size + gap - bbox[0]
    text_y = (height - text_h) // 2 - bbox[1]
    draw.text((text_x, text_y), text, font=font, fill=ACCENT)

    return img


def main() -> None:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)

    targets = {
        BRAND_DIR / "icon.png": _icon(256),
        BRAND_DIR / "icon@2x.png": _icon(512),
        BRAND_DIR / "logo.png": _logo(128),
        BRAND_DIR / "logo@2x.png": _logo(256),
    }
    for path, image in targets.items():
        image.save(path, format="PNG", optimize=True)
        print(f"wrote {path.relative_to(REPO_ROOT)}  {image.size}  {image.mode}")


if __name__ == "__main__":
    main()
