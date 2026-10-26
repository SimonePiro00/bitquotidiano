"""Variante "infografica" del Reel: schema animato a passi numerati, con Bit piccolo che fa da voce narrante.

Gancio con il titolo, poi un passo per ogni punto (numero grande, titolo, illustrazione del carosello
se c'è, testo che compare mentre Bit lo dice), infine un riepilogo a spunte e l'invito a seguire la pagina.
"""
import math
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .reel import (ACCENT, BG, FG, FPS, H, MUTED, SCURO, W, _bit, _bocca, _chiudi, _codifica, _scene, _tempi)
from .render import FONT_BOLD, FONT_REG, _font, _wrap

X0, X1 = 90, 950          # zona sicura orizzontale
LARGHEZZA = X1 - X0
BIT_LATO = 260
_cache_bit = {}


def _ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _mix(c, a: float):
    """Colore c sfumato sul fondo: a=0 invisibile, a=1 pieno."""
    return tuple(int(b + (v - b) * a) for v, b in zip(c, BG))


def _bit_piccolo(bocca, occhi, braccio, lato=BIT_LATO):
    chiave = (bocca, occhi, braccio, lato)
    if chiave not in _cache_bit:
        _cache_bit[chiave] = _bit(bocca, occhi, braccio).resize((lato, lato), Image.LANCZOS)
    return _cache_bit[chiave]


def _testata(d, n, tot):
    d.text((X0, 170), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    if tot <= 0:
        return
    # Indicatore dei passi: pallini collegati, pieni quelli già spiegati.
    y, r = 290, 20
    passo = (LARGHEZZA - 2 * r) / max(1, tot - 1)
    d.line([(X0 + r, y), (X1 - r, y)], fill=SCURO, width=6)
    if n > 0:
        d.line([(X0 + r, y), (X0 + r + passo * min(n, tot - 1), y)], fill=ACCENT, width=6)
    f = _font(FONT_BOLD, 24)
    for i in range(tot):
        x = X0 + r + passo * i
        rr = r + 6 if i == n else r
        if i <= n:
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=ACCENT)
            d.text((x, y), str(i + 1), font=f, fill=BG, anchor="mm")
        else:
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=BG, outline=SCURO, width=5)
            d.text((x, y), str(i + 1), font=f, fill=MUTED, anchor="mm")


def _righe_visibili(righe, parole_visibili):
    out, restanti = [], parole_visibili
    for r in righe:
        p = r.split()
        if restanti <= 0:
            out.append("")
        elif restanti >= len(p):
            out.append(r)
        else:
            out.append(" ".join(p[:restanti]))
        restanti -= len(p)
    return out


def _gancio(titolo, sec, k, t, seg, scrittura, n_punti):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _testata(d, -1, 0)
    a = _ease(k / 12)
    d.text((X0, 420 - 40 * (1 - a)), f"IN {n_punti} PUNTI", font=_font(FONT_BOLD, 44), fill=_mix(ACCENT, a))
    for size in (100, 90, 80, 70):
        f = _font(FONT_BOLD, size)
        righe = _wrap(d, titolo, f, LARGHEZZA)
        if len(righe) * size * 1.2 <= 560:
            break
    y = 500
    for i, r in enumerate(righe):
        ai = _ease((k - 6 - 5 * i) / 12)
        d.text((X0 + 60 * (1 - ai), y), r, font=f, fill=_mix(FG, ai))
        y += size * 1.2
    d.rounded_rectangle([X0, y + 30, X0 + 260 * _ease((k - 20) / 15), y + 46], 8, fill=ACCENT)
    bit = _bit_piccolo(_bocca(seg, k, sec, scrittura), (t % 75) < 4, (k // 8) % 2 == 0, 420)
    img.paste(bit, ((W - 420) // 2, int(1060 + 10 * math.sin(t / FPS * 5))), bit)
    return img


def _punto(n, tot, titolo, corpo, ill, sec, k, t, seg, scrittura):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _testata(d, n, tot)
    a = _ease(k / 10)
    d.text((X0 - 80 * (1 - a), 360), f"{n + 1:02d}", font=_font(FONT_BOLD, 180), fill=_mix(ACCENT, a))
    bit = _bit_piccolo(_bocca(seg, k, sec, scrittura), (t % 75) < 4, False)
    img.paste(bit, (X1 - BIT_LATO, int(350 + 8 * math.sin(t / FPS * 5))), bit)

    # Impaginazione: scala il testo finché titolo, illustrazione e corpo stanno sopra y=1480.
    alto_ill = 0
    if ill is not None:
        alto_ill = min(380, int(LARGHEZZA * ill.height / ill.width))
    misure = [(76, 54, 1.0), (70, 50, 0.85), (64, 46, 0.75), (58, 42, 0.65)] if ill is not None else \
        [(86, 64, 1), (80, 60, 1), (74, 56, 1), (68, 52, 1), (62, 48, 1)]
    for st, sc, ridu in misure:
        ft, fc = _font(FONT_BOLD, st), _font(FONT_REG, sc)
        rt, rc = _wrap(d, titolo, ft, LARGHEZZA), _wrap(d, corpo, fc, LARGHEZZA)
        h_ill = int(alto_ill * ridu)
        h = len(rt) * st * 1.18 + 70 + (h_ill + 40 if ill is not None else 0) + len(rc) * sc * 1.35
        if 600 + h <= 1480:
            break
    y = 600 if ill is not None else max(600, 600 + (880 - h) / 3)   # senza illustrazione il testo scende un po'
    at = _ease((k - 4) / 10)
    for r in rt:
        d.text((X0 + 50 * (1 - at), y), r, font=ft, fill=_mix(FG, at))
        y += st * 1.18
    d.rounded_rectangle([X0, y + 18, X0 + 200 * _ease((k - 10) / 12), y + 30], 6, fill=ACCENT)
    y += 70
    if ill is not None:
        ai = _ease((k - 8) / 12)
        alto = int(h_ill * (0.85 + 0.15 * ai))
        im = ill.resize((int(alto * ill.width / ill.height), alto), Image.LANCZOS)
        if ai < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * ai)))
        img.paste(im, (X0 + (LARGHEZZA - im.width) // 2, int(y + (h_ill - im.height) / 2)), im)
        y += h_ill + 40
    parole = len(corpo.split())
    if seg is None:
        # Senza voce il testo compare tutto insieme: ognuno lo legge con i suoi tempi.
        visibili, colore = parole, _mix(FG, _ease((k - 12) / 10))
    else:
        visibili, colore = parole if sec >= scrittura else max(0, int(parole * sec / max(scrittura, 0.1)) + 1), FG
    for r in _righe_visibili(rc, visibili):
        d.text((X0, y), r, font=fc, fill=colore)
        y += sc * 1.35
    return img


def _riepilogo(titoli, invito, sec, k, t, seg, scrittura, tot):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _testata(d, tot - 1, tot)
    d.text((X0, 370), "RIEPILOGO", font=_font(FONT_BOLD, 52), fill=ACCENT)
    f = _font(FONT_BOLD, 46)
    y = 470
    durata = max(scrittura, 0.1)
    for i, tit in enumerate(titoli):
        a = _ease((sec - durata * i / len(titoli)) * 3)   # una spunta dopo l'altra mentre Bit parla
        r = 30
        d.ellipse([X0, y, X0 + 2 * r, y + 2 * r], fill=_mix(ACCENT, a) if a > 0 else BG, outline=ACCENT, width=4)
        if a > 0.3:
            d.line([(X0 + 16, y + 31), (X0 + 27, y + 43), (X0 + 46, y + 19)], fill=BG, width=7, joint="curve")
        righe = _wrap(d, tit, f, LARGHEZZA - 90)
        for j, rg in enumerate(righe):
            d.text((X0 + 90, y + 6 + j * 56), rg, font=f, fill=FG if a > 0 else MUTED)
        y += max(1, len(righe)) * 56 + 26
    ai = _ease((sec - durata * 0.6) * 2)
    fi = _font(FONT_BOLD, 50)
    y = max(y + 30, 1120)
    for rg in _wrap(d, invito, fi, LARGHEZZA - 280):
        d.text((X0, y), rg, font=fi, fill=_mix(ACCENT, ai))
        y += 62
    bit = _bit_piccolo(_bocca(seg, k, sec, scrittura), (t % 75) < 4, (k // 8) % 2 == 0)
    img.paste(bit, (X1 - BIT_LATO, int(1180 + 8 * math.sin(t / FPS * 5))), bit)
    return img


def make_reel_info(folder: Path, slides: list[dict], nome="reel_info.mp4") -> Path:
    # I titoli del carosello a volte sono già numerati ("2. Libera il disco"): qui il numero c'è già.
    scene = [(re.sub(r"^\d+[.)]\s*", "", t), c, tipo) for t, c, tipo in _scene(slides)]
    punti = scene[1:-1]
    illustrazioni = []
    for i in range(1, len(slides) - 1):
        p = folder / f"illustrazione_{i}.png"
        illustrazioni.append(Image.open(p).convert("RGBA") if p.exists() else None)
    out = folder / nome
    with tempfile.TemporaryDirectory() as tmp:
        traccia = Path(tmp) / "voce.wav"
        tempi = _tempi(scene, traccia, pausa_fine=2.0)
        proc = _codifica(out, traccia)
        t = 0
        for n, ((titolo, corpo, tipo), (totale, inizio, scrittura, seg)) in enumerate(zip(scene, tempi)):
            for k in range(totale):
                sec = k / FPS - inizio
                if tipo == "gancio":
                    frame = _gancio(corpo, sec, k, t, seg, scrittura, len(punti))
                elif tipo == "fine":
                    frame = _riepilogo([p[0] for p in punti], "Segui @bitquotidiano.it per un trucco tech al giorno",
                                       sec, k, t, seg, scrittura, len(punti))
                else:
                    frame = _punto(n - 1, len(punti), titolo, corpo, illustrazioni[n - 1], sec, k, t, seg, scrittura)
                proc.stdin.write(frame.tobytes())
                t += 1
        _chiudi(proc)
    return out
