"""Reel "lampo" (novembre 2026): circa 9 secondi, pensato per essere rivisto in loop e inoltrato.

0-2,2 s  frase-gancio enorme, già completa al fotogramma 0 (niente animazione d'ingresso);
2,2-7 s  tre punti brevissimi che si aggiungono uno sotto l'altro sulla stessa schermata;
7-9,5 s  invito a inoltrare ("Mandalo a ...") e a seguire; l'ultimo fotogramma richiama il primo,
         così quando il Reel riparte il passaggio quasi non si nota.
"""
import math
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from . import musica
from .reel import ACCENT, BG, FG, FPS, H, MUTED, SCURO, W, _chiudi, _codifica
from .reel_info import LARGHEZZA, X0, X1, _bit_piccolo, _ease, _fondo_gancio, _mix, _righe_evidenziate
from .render import FONT_BOLD, _font, _wrap

GANCIO_S, PUNTO_S, FINE_S = 2.2, 1.6, 2.5


def _scrivi_evidenziato(d, testo, size, y, colore=FG):
    f = _font(FONT_BOLD, size)
    spazio = d.textlength(" ", font=f)
    for riga in _righe_evidenziate(d, testo, f, LARGHEZZA):
        x = X0
        for pezzi in riga:
            for pezzo, arancio in pezzi:
                d.text((x, y), pezzo, font=f, fill=ACCENT if arancio else colore)
                x += d.textlength(pezzo, font=f)
            x += spazio
        y += size * 1.15
    return y


def _gancio(testo, k, t):
    img = _fondo_gancio(testo, 3)[0].copy()
    d = ImageDraw.Draw(img)
    # Copre il "3 cose da sapere" del gancio lungo: qui basta la freccia.
    fine = _fondo_gancio(testo, 3)[1]
    d.rectangle([X0, fine - 70, X1, fine], fill=BG)
    d.text((X0, fine - 60), "Guarda fino alla fine ↓", font=_font(FONT_BOLD, 46), fill=MUTED)
    d.text((X0, 170), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    lato = 420
    bit = _bit_piccolo(1 + (k // 5) % 2 if (k // 5) % 3 else 0, False, True, lato)
    img.paste(bit, (X1 - lato, int(max(1080, fine + 40) + 8 * math.sin(t / FPS * 6))), bit)
    return img


def _punti(titolo, punti, n, k, t):
    """Mostra i punti da 0 a n; l'ultimo entra con un piccolo scatto."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((X0, 170), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    y = _scrivi_evidenziato(d, titolo, 64, 300, MUTED) + 40
    f = _font(FONT_BOLD, 72)
    for i, p in enumerate(punti[:n + 1]):
        a = 1.0 if i < n else _ease(k / 5)
        dx = int(60 * (1 - a))
        r = 40
        d.ellipse([X0 + dx, y + 8, X0 + dx + 2 * r, y + 8 + 2 * r], fill=_mix(ACCENT, a))
        d.text((X0 + dx + r, y + 8 + r), str(i + 1), font=_font(FONT_BOLD, 50), fill=BG, anchor="mm")
        righe = _wrap(d, p, f, LARGHEZZA - 120)
        for j, rg in enumerate(righe):
            d.text((X0 + 120 + dx, y + j * 84), rg, font=f, fill=_mix(FG, a))
        y += max(1, len(righe)) * 84 + 60
    return img


def _fine(invio, k, t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((X0, 170), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    a = _ease(k / 6)
    # Icona "invia" disegnata: aeroplanino di carta.
    cx, cy, s = X0 + 70, 400, 70 * (0.8 + 0.2 * a)
    d.polygon([(cx - s, cy), (cx + s, cy - s * 0.8), (cx + s * 0.2, cy + s * 0.9)], fill=_mix(ACCENT, a))
    y = _scrivi_evidenziato(d, invio, 96, 520)
    pulsa = 1 + 0.04 * math.sin(k / 3)
    fs = _font(FONT_BOLD, int(52 * pulsa))
    testo = "+ Segui per la prossima"
    lt = d.textlength(testo, font=fs)
    y = max(y + 80, 1000)
    d.rounded_rectangle([X0, y, X0 + lt + 70, y + 100], 50, fill=ACCENT)
    d.text((X0 + 35, y + 50), testo, font=fs, fill=BG, anchor="lm")
    lato = 300
    bit = _bit_piccolo(0, (t % 60) < 4, (k // 8) % 2 == 0, lato)
    img.paste(bit, (X1 - lato, int(y + 140 + 6 * math.sin(t / FPS * 5))), bit)
    return img


def _barra(frame, t, totale):
    d = ImageDraw.Draw(frame)
    d.rectangle([0, 0, W, 12], fill=SCURO)
    d.rectangle([0, 0, int(W * t / totale), 12], fill=ACCENT)
    return frame


def make_reel_lampo(folder: Path, gancio: str, titolo: str, punti: list[str], invio: str, nome="reel.mp4") -> Path:
    """gancio e invio: parole tra *asterischi* in arancio. punti: 3 frasi di 2-6 parole."""
    punti = punti[:3]
    durate = [int(GANCIO_S * FPS)] + [int(PUNTO_S * FPS)] * len(punti) + [int(FINE_S * FPS)]
    totale = sum(durate)
    out = folder / nome
    with tempfile.TemporaryDirectory() as tmp:
        traccia = Path(tmp) / "musica.wav"
        musica.salva(musica.genera(totale / FPS, folder.name), traccia)
        proc = _codifica(out, traccia)
        t = 0
        for scena, n_frame in enumerate(durate):
            for k in range(n_frame):
                if scena == 0:
                    frame = _gancio(gancio, k, t)
                elif scena <= len(punti):
                    frame = _punti(titolo, punti, scena - 1, k, t)
                elif k >= n_frame - 6:
                    frame = _gancio(gancio, 0, t)   # ultimi 0,2 s: torna il gancio, il loop è morbido
                else:
                    frame = _fine(invio, k, t)
                proc.stdin.write(_barra(frame, t, totale).tobytes())
                t += 1
        _chiudi(proc)
    return out
