from PIL import Image, ImageDraw, ImageFont
import os, time
from typing import Dict
from config import ASSETS


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def _open_base() -> Image.Image:
    base_path = ASSETS.get("base")
    if base_path and os.path.exists(base_path):
        try:
            return Image.open(base_path).convert("RGBA")
        except Exception:
            pass
    # Fallback: create a blank 1080x1350 canvas
    return Image.new("RGBA", (1080, 1350), (9, 33, 29, 255))


def _maybe_logo(canvas: Image.Image) -> None:
    logo_path = ASSETS.get("logo")
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            W, H = canvas.size
            lw = int(W * 0.18)
            lh = int(logo.size[1] * (lw / logo.size[0]))
            logo = logo.resize((lw, lh))
            canvas.alpha_composite(logo, dest=(W - lw - 60, 60))
        except Exception:
            pass


def _safe_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default


# Colors
COL_TEXT = (245, 245, 245, 255)
COL_MUTE = (220, 220, 220, 255)
COL_PILL = (70, 122, 129, 255)
COL_EDGE = (149, 200, 160, 255)
COL_ROW  = (5, 41, 37, 255)


def _rounded(draw: ImageDraw.ImageDraw, rect, r: int, fill):
    draw.rounded_rectangle(rect, radius=r, fill=fill)


def _book_logo(book: str):
    if not book:
        return None
    p = f"assets/book_{book.lower().replace(' ', '')}.png"
    if os.path.exists(p):
        try:
            return Image.open(p).convert("RGBA")
        except Exception:
            return None
    return None


def generate_card(data: Dict) -> str:
    base = _open_base()
    W, H = base.size
    draw = ImageDraw.Draw(base)

    font_path = ASSETS.get("font", "")
    title_font = _load_font(font_path, 56)
    label_font = _load_font(font_path, 44)
    body_font = _load_font(font_path, 40)
    tag_font  = _load_font(font_path, 36)

    gray = COL_MUTE
    white = COL_TEXT

    # Logo (optional)
    _maybe_logo(base)

    x_pad, y_pad = 80, 120

    # Title line: league · market
    title = f"{data.get('league','')} · {data.get('market','')}".strip(" ·")
    draw.text((x_pad, y_pad), title, font=title_font, fill=white)

    # Edge badge + tags chips
    try:
        edge_val = float(data.get("edge_percent", 0) or 0)
    except Exception:
        edge_val = 0.0
    badge_w, badge_h = 160, 56
    bx, by = x_pad, y_pad + 64
    _rounded(draw, (bx, by, bx + badge_w, by + badge_h), 24, COL_EDGE)
    badge_txt = f"{edge_val:.1f}%"
    tw = draw.textlength(badge_txt, font=body_font)
    draw.text((bx + (badge_w - tw) / 2, by + 10), badge_txt, font=body_font, fill=(18, 42, 36, 255))

    tags = data.get("tags") or [data.get("league", ""), "Baseball", data.get("market", "")]
    tx, ty = bx + badge_w + 24, by
    for t in [t for t in tags if t][:3]:
        pill_w = int(draw.textlength(t, font=tag_font) + 36)
        _rounded(draw, (tx, ty, tx + pill_w, ty + badge_h), 24, COL_PILL)
        draw.text((tx + 18, ty + 8), t, font=tag_font, fill=white)
        tx += pill_w + 12

    # Event + player
    y = y_pad + 140
    event = data.get("event", "")
    player = data.get("player", "")
    draw.text((x_pad, y), event, font=label_font, fill=white); y += 60
    draw.text((x_pad, y), player, font=label_font, fill=white); y += 70

    # Date line
    kickoff = data.get("kickoff_iso", "")
    draw.text((x_pad, y), f"Date of Event: {kickoff}", font=body_font, fill=gray); y += 50

    # Book rows (containers + optional logos + odds right)
    row_y = y + 20
    for sel_key in ("selection_over", "selection_under"):
        sel = data.get(sel_key, {}) or {}
        _rounded(draw, (x_pad - 16, row_y, W - x_pad + 16, row_y + 140), 24, COL_ROW)
        # Logo
        lg = _book_logo(str(sel.get("book", "")))
        if lg:
            lg = lg.resize((96, 96))
            base.alpha_composite(lg, dest=(x_pad + 8, row_y + 22))
        # Texts
        draw.text((x_pad + 120, row_y + 20), player, font=label_font, fill=white)
        draw.text((x_pad + 120, row_y + 20 + 50), str(sel.get("label", "")), font=body_font, fill=white)
        # Odds right
        odds = _safe_int(sel.get("american", 0))
        otxt = f"{odds:+d}"
        tw = draw.textlength(otxt, font=title_font)
        draw.text((W - x_pad - tw, row_y + 36), otxt, font=title_font, fill=white)
        row_y += 160

    # Footer (logo already handled at top)

    # Save
    out = f"out_{int(time.time())}.png"
    try:
        base.save(out, format="PNG")
    except Exception:
        # As a last resort, change to RGB
        base.convert("RGB").save(out, format="PNG")
    return out
