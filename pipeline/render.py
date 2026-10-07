"""Disegna le slide del carosello (1080x1350, formato verticale 4:5) con una grafica propria."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
BG = (9, 17, 42)        # blu notte, come il logo
ACCENT = (255, 122, 26)  # arancio, unico accento
FG = (242, 245, 250)
MUTED = (135, 150, 180)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MARGIN = 90


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def _wrap(draw, text, font, max_width):
    lines = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            trial = f"{line} {w}".strip()
            if draw.textlength(trial, font=font) <= max_width:
                line = trial
            else:
                lines.append(line)
                line = w
        lines.append(line)
    return lines


def _frame(index: int, total: int, handle: str):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=ACCENT)
    d.text((MARGIN, 70), handle, font=_font(FONT_BOLD, 34), fill=ACCENT)
    d.text((W - MARGIN, 70), f"{index}/{total}", font=_font(FONT_REG, 34), fill=MUTED, anchor="ra")
    return img, d


def _title(d, text, y, size=64):
    font = _font(FONT_BOLD, size)
    for line in _wrap(d, text, font, W - 2 * MARGIN):
        d.text((MARGIN, y), line, font=font, fill=FG)
        y += font.size + 18
    return y


def _save(img, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)  # Instagram accetta solo JPEG per le immagini
    return out


def render_slide(titolo: str, testo: str, index: int, total: int, handle: str, out: Path, ill=None) -> Path:
    img, d = _frame(index, total, handle)
    cover = index == 1
    y = _title(d, titolo, 420 if cover else 260, 96 if cover else 64)
    if testo:
        body_font = _font(FONT_REG, 46)
        y += 40
        d.rectangle([MARGIN, y, MARGIN + 120, y + 8], fill=ACCENT)
        y += 60
        for line in _wrap(d, testo, body_font, W - 2 * MARGIN):
            d.text((MARGIN, y), line, font=body_font, fill=FG)
            y += body_font.size + 16
    if ill is not None:
        # L'illustrazione occupa lo spazio libero sotto il testo, centrata.
        top, bottom = y + 50, H - 150
        scale = min((W - 2 * MARGIN) / ill.width, (bottom - top) / ill.height, 1.0)
        if scale > 0.25:
            pic = ill.resize((int(ill.width * scale), int(ill.height * scale)), Image.LANCZOS)
            img.paste(pic, ((W - pic.width) // 2, top + (bottom - top - pic.height) // 2), pic)
    footer = "Scorri →" if cover else ("Seguici per altre news tech" if index == total else "")
    if footer:
        d.text((MARGIN, H - 120), footer, font=_font(FONT_BOLD, 38), fill=MUTED)
    return _save(img, out)


def _numeri(d, info, y):
    """1-3 cifre chiave, grandi, una sotto l'altra."""
    small = _font(FONT_REG, 40)
    for el in info.elementi[:3]:
        # La cifra si rimpicciolisce finché sta nella larghezza della slide.
        size = 120
        big = _font(FONT_BOLD, size)
        while size > 56 and d.textlength(el.testo, font=big) > W - 2 * MARGIN:
            size -= 8
            big = _font(FONT_BOLD, size)
        for line in _wrap(d, el.testo, big, W - 2 * MARGIN)[:2]:
            d.text((MARGIN, y), line, font=big, fill=ACCENT)
            y += big.size + 12
        y += 8
        for line in _wrap(d, el.etichetta, small, W - 2 * MARGIN):
            d.text((MARGIN, y), line, font=small, fill=FG)
            y += small.size + 10
        y += 60


def _barre(d, info, y):
    """Barre orizzontali, un solo colore, valore scritto a fianco; ordinate dal maggiore."""
    els = sorted([e for e in info.elementi if e.valore is not None], key=lambda e: e.valore, reverse=True)[:6]
    if not els:
        return
    # Lo spazio sotto il grafico è riservato all'unità e alla nota (2 righe): se le barre non
    # ci stanno, si riducono font, barre e spazi in proporzione.
    available = H - 80 - 36 * 2 - 60 - y
    scale = min(1.0, available / (len(els) * (38 + 14 + 56 + 62)))
    label_font, value_font = _font(FONT_REG, int(38 * scale)), _font(FONT_BOLD, int(38 * scale))
    max_v = max(e.valore for e in els) or 1
    bar_h, gap = int(56 * scale), int(62 * scale)
    max_w = W - 2 * MARGIN - 220
    for e in els:
        d.text((MARGIN, y), e.etichetta, font=label_font, fill=FG)
        y += label_font.size + int(14 * scale)
        w = max(8, int(max_w * e.valore / max_v))
        d.rounded_rectangle([MARGIN, y, MARGIN + w, y + bar_h], radius=6, fill=ACCENT)
        d.text((MARGIN + w + 20, y + bar_h / 2), e.testo, font=value_font, fill=FG, anchor="lm")
        y += bar_h + gap
    if info.unita:
        d.text((MARGIN, y - gap // 3), f"Valori in {info.unita}", font=_font(FONT_REG, 30), fill=MUTED)


def _timeline(d, info, y):
    """Tappe in verticale lungo una linea, data in evidenza."""
    date_font, txt_font = _font(FONT_BOLD, 40), _font(FONT_REG, 36)
    x_line = MARGIN + 14
    els = info.elementi[:6]
    step = min(170, (H - 220 - y) // max(1, len(els)))
    d.line([x_line, y + 20, x_line, y + step * (len(els) - 1) + 20], fill=MUTED, width=3)
    for e in els:
        d.ellipse([x_line - 14, y + 6, x_line + 14, y + 34], fill=ACCENT, outline=BG, width=4)
        d.text((MARGIN + 60, y), e.etichetta, font=date_font, fill=ACCENT)
        ty = y + date_font.size + 10
        for line in _wrap(d, e.testo, txt_font, W - 2 * MARGIN - 60)[:2]:
            d.text((MARGIN + 60, ty), line, font=txt_font, fill=FG)
            ty += txt_font.size + 6
        y += step


def render_infographic(info, index: int, total: int, handle: str, out: Path) -> Path:
    img, d = _frame(index, total, handle)
    y = _title(d, info.titolo, 200, 60) + 70
    {"numeri": _numeri, "barre": _barre, "timeline": _timeline}[info.tipo](d, info, y)
    if info.nota:
        note_font = _font(FONT_REG, 28)
        lines = _wrap(d, info.nota, note_font, W - 2 * MARGIN)[:2]
        for j, line in enumerate(lines):
            d.text((MARGIN, H - 80 - 36 * (len(lines) - j)), line, font=note_font, fill=MUTED)
    return _save(img, out)


def render_draft(bozza, out_dir: Path, handle: str) -> list[Path]:
    """Copertina, poi l'infografica (se c'è), poi le altre slide.
    Le illustrazioni, se presenti, sono in out_dir/illustrazione_<n>.png (n = indice della slide)."""
    pages = [("slide", (k, s)) for k, s in enumerate(bozza.slides)]
    if getattr(bozza, "infografica", None):
        pages.insert(1, ("info", bozza.infografica))
    total, paths = len(pages), []
    story_src = None
    for i, (kind, item) in enumerate(pages, start=1):
        out = out_dir / f"slide_{i}.jpg"
        if kind == "info":
            paths.append(render_infographic(item, i, total, handle, out))
        else:
            k, slide = item
            ill_path = out_dir / f"illustrazione_{k}.png"
            ill = Image.open(ill_path).convert("RGBA") if ill_path.exists() else None
            paths.append(render_slide(slide.titolo, slide.testo, i, total, handle, out, ill))
    render_story(paths[0], out_dir / "story.jpg", handle)
    return paths


def render_story(cover: Path, out: Path, handle: str) -> Path:
    """Storia 1080x1920 che rilancia il post: la copertina al centro e l'invito ad aprirlo."""
    sw, sh = 1080, 1920
    img = Image.new("RGB", (sw, sh), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, sw, 14], fill=ACCENT)
    d.text((sw // 2, 170), "NUOVO POST", font=_font(FONT_BOLD, 64), fill=ACCENT, anchor="mm")
    card = Image.open(cover).convert("RGB").resize((840, 1050), Image.LANCZOS)
    x, y = (sw - card.width) // 2, 300
    d.rounded_rectangle([x - 6, y - 6, x + card.width + 6, y + card.height + 6], radius=24, fill=ACCENT)
    img.paste(card, (x, y))
    d.text((sw // 2, y + card.height + 130), "Lo trovi sul profilo", font=_font(FONT_BOLD, 54), fill=FG, anchor="mm")
    d.text((sw // 2, y + card.height + 210), handle, font=_font(FONT_REG, 44), fill=MUTED, anchor="mm")
    return _save(img, out)
