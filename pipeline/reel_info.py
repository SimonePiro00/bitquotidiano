"""Variante "infografica" del Reel: schema animato a passi numerati, con Bit piccolo che fa da voce narrante.

Gancio con il titolo, poi un passo per ogni punto (numero grande, titolo, illustrazione del carosello
se c'è, testo che compare mentre Bit lo dice), infine un riepilogo a spunte e l'invito a seguire la pagina.
"""
import math
from functools import lru_cache
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .reel import (ACCENT, BG, FG, FPS, H, MUTED, SCURO, W, _bit, _bocca, _chiudi, _codifica, _scene, _sintesi, _tempi)
from . import musica
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


def _righe_evidenziate(d, testo, font, larghezza):
    """Va a capo come _wrap, ma tiene in arancio il testo tra *asterischi* (anche a metà parola, es. *"ciao"*:).
    Restituisce righe di parole; ogni parola è una lista di pezzi (testo, arancio)."""
    righe, riga, w_riga, acceso = [], [], 0, False
    spazio = d.textlength(" ", font=font)
    for parola in testo.split():
        pezzi, corrente = [], ""
        for c in parola:
            if c == "*":
                if corrente:
                    pezzi.append((corrente, acceso))
                corrente, acceso = "", not acceso
            else:
                corrente += c
        if corrente:
            pezzi.append((corrente, acceso))
        lw = sum(d.textlength(t, font=font) for t, _ in pezzi)
        if riga and w_riga + spazio + lw > larghezza:
            righe.append(riga)
            riga, w_riga = [], 0
        w_riga += (spazio if riga else 0) + lw
        riga.append(pezzi)
    if riga:
        righe.append(riga)
    return righe


@lru_cache(maxsize=4)
def _fondo_gancio(testo, n_punti):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for size in (124, 112, 100, 90, 80):
        f = _font(FONT_BOLD, size)
        righe = _righe_evidenziate(d, testo, f, LARGHEZZA)
        if len(righe) * size * 1.15 <= 700:
            break
    y = 330
    spazio = d.textlength(" ", font=f)
    for riga in righe:
        x = X0
        for pezzi in riga:
            for pezzo, arancio in pezzi:
                d.text((x, y), pezzo, font=f, fill=ACCENT if arancio else FG)
                x += d.textlength(pezzo, font=f)
            x += spazio
        y += size * 1.15
    fi = _font(FONT_BOLD, 46)
    d.text((X0, y + 50), f"{n_punti} cose da sapere ↓", font=fi, fill=MUTED)
    return img, int(y + 110)


def _gancio(testo, sec, k, t, seg, scrittura, n_punti):
    """Primo secondo: frase-gancio enorme già leggibile al fotogramma 0, con un leggero zoom all'indietro,
    e Bit che spunta dal basso con un punto esclamativo."""
    base, fine_testo = _fondo_gancio(testo, n_punti)
    z = 1 + 0.04 * (1 - _ease(k / 18))
    if z > 1.001:
        lw, lh = int(W / z), int(H / z)
        x0, y0 = (W - lw) // 2, int((H - lh) * 0.3)
        img = base.crop((x0, y0, x0 + lw, y0 + lh)).resize((W, H), Image.BILINEAR)
    else:
        img = base.copy()
    d = ImageDraw.Draw(img)
    d.text((X0, 170), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    lato = 460
    sale = _ease(k / 8)
    arrivo = max(1080, fine_testo + 70)             # Bit e il "!" non coprono mai il testo
    y_bit = int(1500 - (1500 - arrivo) * sale + 8 * math.sin(t / FPS * 6))
    bit = _bit_piccolo(_bocca(seg, k, sec, scrittura), False, True, lato)
    img.paste(bit, (X1 - lato, y_bit), bit)
    if k >= 6:
        # Il fumetto con il punto esclamativo "pulsa" per attirare l'occhio.
        r = int(52 + 6 * math.sin(k / 3))
        cx, cy = X1 - lato - 20, y_bit + 60
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
        d.text((cx, cy), "!", font=_font(FONT_BOLD, 76), fill=BG, anchor="mm")
    return img


def _punto(n, tot, titolo, corpo, ill, sec, k, t, seg, scrittura):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _testata(d, n, tot)
    a = _ease(k / 5)
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
        if 600 + h <= 1370:
            break
    y = 600 if ill is not None else max(600, 600 + (770 - h) / 3)   # senza illustrazione il testo scende un po'
    at = _ease((k - 1) / 6)
    for r in rt:
        d.text((X0 + 50 * (1 - at), y), r, font=ft, fill=_mix(FG, at))
        y += st * 1.18
    d.rounded_rectangle([X0, y + 18, X0 + 200 * _ease((k - 4) / 8), y + 30], 6, fill=ACCENT)
    y += 70
    if ill is not None:
        ai = _ease((k - 3) / 8)
        alto = int(h_ill * (0.85 + 0.15 * ai))
        im = ill.resize((int(alto * ill.width / ill.height), alto), Image.LANCZOS)
        if ai < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * ai)))
        img.paste(im, (X0 + (LARGHEZZA - im.width) // 2, int(y + (h_ill - im.height) / 2)), im)
        y += h_ill + 40
    parole = len(corpo.split())
    if seg is None:
        # Senza voce il testo compare tutto insieme: ognuno lo legge con i suoi tempi.
        visibili, colore = parole, _mix(FG, _ease((k - 4) / 6))
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


def _sovrimpressioni(frame, t, totale, mostra_invito):
    """Barra di avanzamento di tutto il video (si vede che è corto) e, da metà, l'invito a seguire."""
    d = ImageDraw.Draw(frame)
    d.rectangle([0, 0, W, 12], fill=SCURO)
    d.rectangle([0, 0, int(W * t / totale), 12], fill=ACCENT)
    if mostra_invito:
        f = _font(FONT_BOLD, 40)
        testo = "+ Segui @bitquotidiano.it"
        lt = d.textlength(testo, font=f)
        d.rounded_rectangle([X0, 1390, X0 + lt + 50, 1462], 36, fill=ACCENT)
        d.text((X0 + 25, 1426), testo, font=f, fill=BG, anchor="lm")
    return frame


def make_reel_info(folder: Path, slides: list[dict], nome="reel_info.mp4", gancio: str | None = None) -> Path:
    """gancio: frase d'apertura (parole tra *asterischi* in arancio); se manca si usa il titolo."""
    # I titoli del carosello a volte sono già numerati ("2. Libera il disco"): qui il numero c'è già.
    scene = [(re.sub(r"^\d+[.)]\s*", "", t), c, tipo) for t, c, tipo in _scene(slides)]
    # Testi più brevi: i Reel devono durare circa 20 secondi.
    scene = [(t, _sintesi(slides[n]["testo"], 80) if tipo == "punto" else c, tipo) for n, (t, c, tipo) in enumerate(scene)]
    punti = scene[1:-1]
    illustrazioni = []
    for i in range(1, len(slides) - 1):
        p = folder / f"illustrazione_{i}.png"
        illustrazioni.append(Image.open(p).convert("RGBA") if p.exists() else None)
    out = folder / nome
    with tempfile.TemporaryDirectory() as tmp:
        traccia = Path(tmp) / "voce.wav"
        tempi = _tempi(scene, traccia, pausa_fine=2.0)
        if not traccia.exists():
            # Senza voce il ritmo è veloce: 2 s di gancio, 2-3 s per punto, 3 s di riepilogo.
            def durata(titolo, corpo, tipo):
                if tipo == "gancio":
                    return 2.0
                if tipo == "fine":
                    return 3.0
                return min(3.2, 1.3 + len(f"{titolo} {corpo}".split()) / 7)
            tempi = [(int(durata(*sc) * FPS), 0, 0.1, None) for sc in scene]
        totale_video = sum(tm[0] for tm in tempi)
        meta = sum(tm[0] for tm in tempi[:1 + len(punti) // 2])
        if not traccia.exists():
            # Senza voce: musichetta originale, diversa per ogni bozza.
            musica.salva(musica.genera(sum(tm[0] for tm in tempi) / FPS, folder.name), traccia)
        proc = _codifica(out, traccia)
        t = 0
        for n, ((titolo, corpo, tipo), (totale, inizio, scrittura, seg)) in enumerate(zip(scene, tempi)):
            for k in range(totale):
                sec = k / FPS - inizio
                if tipo == "gancio":
                    frame = _gancio(gancio or corpo, sec, k, t, seg, scrittura, len(punti))
                elif tipo == "fine":
                    frame = _riepilogo([p[0] for p in punti], "Segui @bitquotidiano.it per un trucco tech al giorno",
                                       sec, k, t, seg, scrittura, len(punti))
                else:
                    frame = _punto(n - 1, len(punti), titolo, corpo, illustrazioni[n - 1], sec, k, t, seg, scrittura)
                if tipo != "fine":
                    frame = _sovrimpressioni(frame, t, totale_video, t >= meta)
                else:
                    frame = _sovrimpressioni(frame, t, totale_video, False)
                proc.stdin.write(frame.tobytes())
                t += 1
        _chiudi(proc)
    return out
