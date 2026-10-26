"""Crea un Reel verticale (1080x1920) in cui Bit, la mascotte, spiega la bozza con i fumetti.

Struttura: Bit saluta e annuncia il titolo (gancio), poi un fumetto per ogni punto con il testo
che compare parola per parola mentre Bit "parla", infine l'invito a seguire la pagina.
I fotogrammi sono disegnati con Pillow (Bit da SVG con cairosvg) e codificati con ffmpeg.
Audio muto: l'API non permette la musica di Instagram.
"""
import math
import re
import subprocess
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw

from .render import FONT_BOLD, FONT_REG, _font, _wrap

W, H, FPS = 1080, 1920, 30
BG, FG, ACCENT, MUTED, SCURO = (9, 17, 42), (242, 245, 250), (255, 122, 26), (135, 150, 180), (28, 43, 85)
BOLLA = (80, 290, 1000, 1010)   # fumetto, fuori dalle icone di Instagram
BIT_Y, BIT_LATO = 1070, 640
PAROLE_AL_SECONDO = 8


@lru_cache(maxsize=None)
def _bit(bocca: int, occhi_chiusi: bool, braccio_su: bool) -> Image.Image:
    """Bit disegnato come in assets/mascotte_bit.svg, con bocca (0 sorriso, 1-2 aperta),
    occhi e braccio sinistro variabili per l'animazione."""
    occhi = ('<rect x="228" y="236" width="44" height="8" rx="4" fill="#F2F5FA"/>'
             '<rect x="328" y="236" width="44" height="8" rx="4" fill="#F2F5FA"/>') if occhi_chiusi else (
             '<ellipse cx="250" cy="240" rx="22" ry="30" fill="#F2F5FA"/><ellipse cx="350" cy="240" rx="22" ry="30" fill="#F2F5FA"/>'
             '<circle cx="257" cy="230" r="8" fill="#09112A"/><circle cx="357" cy="230" r="8" fill="#09112A"/>')
    bocca_svg = ['<path d="M265 290 Q300 318 335 290" stroke="#FF7A1A" stroke-width="10" fill="none" stroke-linecap="round"/>',
                 '<ellipse cx="300" cy="298" rx="22" ry="12" fill="#FF7A1A"/>',
                 '<ellipse cx="300" cy="302" rx="26" ry="22" fill="#FF7A1A"/>'][bocca]
    braccio = ('<path d="M200 420 Q130 380 120 300" stroke="#F2F5FA" stroke-width="12" fill="none" stroke-linecap="round"/>'
               '<circle cx="118" cy="288" r="18" fill="#FF7A1A"/>') if braccio_su else (
               '<path d="M200 420 Q140 400 130 340" stroke="#F2F5FA" stroke-width="12" fill="none" stroke-linecap="round"/>'
               '<circle cx="128" cy="330" r="18" fill="#FF7A1A"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">
  <line x1="300" y1="70" x2="300" y2="130" stroke="#8796B4" stroke-width="10" stroke-linecap="round"/>
  <circle cx="300" cy="60" r="22" fill="#FF7A1A"/>
  <rect x="150" y="130" width="300" height="240" rx="60" fill="#1C2B55" stroke="#F2F5FA" stroke-width="10"/>
  <rect x="185" y="165" width="230" height="170" rx="36" fill="#09112A"/>
  {occhi}{bocca_svg}
  <ellipse cx="215" cy="290" rx="16" ry="9" fill="#FF7A1A" opacity="0.6"/>
  <ellipse cx="385" cy="290" rx="16" ry="9" fill="#FF7A1A" opacity="0.6"/>
  <rect x="200" y="385" width="200" height="130" rx="40" fill="#1C2B55" stroke="#F2F5FA" stroke-width="10"/>
  <text x="300" y="468" font-family="DejaVu Sans Mono" font-weight="bold" font-size="56" fill="#FF7A1A" text-anchor="middle">&gt;_</text>
  {braccio}
  <path d="M400 430 Q450 450 470 490" stroke="#F2F5FA" stroke-width="12" fill="none" stroke-linecap="round"/>
  <rect x="235" y="515" width="34" height="45" rx="12" fill="#8796B4"/>
  <rect x="331" y="515" width="34" height="45" rx="12" fill="#8796B4"/>
</svg>'''
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=BIT_LATO, output_height=BIT_LATO)
    return Image.open(BytesIO(png)).convert("RGBA")


def _sintesi(testo: str, limite: int = 110) -> str:
    out = ""
    for f in re.split(r"(?<=[.!?])\s+", testo.strip()):
        # Una frase brevissima (es. "0 €, 5 minuti.") da sola non dice niente: aggiunge la successiva.
        if len(out) >= 40 and len(out) + len(f) + 1 > limite:
            break
        out = f"{out} {f}".strip()
    return out


def _impagina(d, titolo, corpo, gancio=False):
    """Sceglie la dimensione più grande che fa stare titolo e corpo nel fumetto."""
    x0, y0, x1, y1 = BOLLA
    larghezza, altezza = x1 - x0 - 100, y1 - y0 - 100
    misure = [(52, 96), (50, 88), (48, 80), (46, 72)] if gancio else [(92, 66), (84, 62), (76, 58), (68, 54), (60, 48), (54, 44)]
    for st, sc in misure:
        ft, fc = _font(FONT_BOLD, st), _font(FONT_BOLD if gancio else FONT_REG, sc)
        rt = _wrap(d, titolo, ft, larghezza) if titolo else []
        rc = _wrap(d, corpo, fc, larghezza) if corpo else []
        h = len(rt) * st * 1.22 + (40 if rt and rc else 0) + len(rc) * sc * 1.3
        if h <= altezza:
            break
    return ft, fc, rt, rc, h


def _scena(titolo, corpo, n, tot, colore_titolo=ACCENT):
    """Sfondo con fumetto e testo completo; restituisce anche le righe per l'effetto macchina da scrivere."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    seg = (920 - (tot - 1) * 8) / tot
    for i in range(tot):
        x = 80 + i * (seg + 8)
        d.rounded_rectangle([x, 160, x + seg, 168], 4, fill=ACCENT if i <= n else SCURO)
    d.text((80, 200), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    x0, y0, x1, y1 = BOLLA
    d.rounded_rectangle(BOLLA, 48, fill=FG)
    d.polygon([(470, y1 - 2), (610, y1 - 2), (540, y1 + 70)], fill=FG)
    ft, fc, rt, rc, h = _impagina(d, titolo, corpo, colore_titolo == MUTED)
    y = y0 + (y1 - y0 - h) / 2
    pos = []
    for r in rt:
        pos.append((r, (x0 + 50, y), ft, colore_titolo))
        y += ft.size * 1.22
    if rt and rc:
        y += 40
    for r in rc:
        pos.append((r, (x0 + 50, y), fc, BG))
        y += fc.size * 1.3
    return img, pos


def _disegna_testo(img, pos, parole_visibili):
    d = ImageDraw.Draw(img)
    restanti = parole_visibili
    for riga, xy, font, colore in pos:
        parole = riga.split()
        if restanti >= len(parole):
            d.text(xy, riga, font=font, fill=colore)
            restanti -= len(parole)
        else:
            if restanti > 0:
                d.text(xy, " ".join(parole[:restanti]), font=font, fill=colore)
            return


def make_reel(folder: Path, slides: list[dict]) -> Path:
    """slides: le slide della bozza (titolo, testo). L'ultima, l'invito finale del carosello,
    viene sostituita dall'invito a seguire la pagina."""
    scene = [("Ciao, sono Bit!", slides[0]["titolo"], "gancio")]
    scene += [(s["titolo"], _sintesi(s["testo"]), "punto") for s in slides[1:-1]]
    scene.append(("Ti è stato utile?", "Seguimi su @bitquotidiano.it: ogni giorno un trucco tech spiegato semplice.", "fine"))
    out = folder / "reel.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t = 0
    for n, (titolo, corpo, tipo) in enumerate(scene):
        # Nel gancio il titolo del post è il testo grande del fumetto.
        base, pos = _scena(titolo, corpo, n, len(scene), MUTED if tipo == "gancio" else ACCENT)
        parole = sum(len(r.split()) for r, *_ in pos)
        scrittura = parole / PAROLE_AL_SECONDO
        lettura = {"gancio": 1.5, "fine": 2.0}.get(tipo, min(2.6, 0.8 + parole / 8))
        totale = int((scrittura + lettura) * FPS)
        for k in range(totale):
            sec = k / FPS
            frame = base.copy()
            _disegna_testo(frame, pos, int(sec * PAROLE_AL_SECONDO) + 1 if sec < scrittura else parole)
            parla = sec < scrittura
            bocca = (1 + (k // 4) % 2) if parla and (k // 4) % 3 else 0
            occhi = (t % 75) < 4                       # sbatte gli occhi ogni 2,5 secondi
            braccio = tipo in ("gancio", "fine") and (k // 8) % 2 == 0
            bob = int(10 * math.sin(t / FPS * 2 * math.pi * 0.8))
            bit = _bit(bocca, occhi, braccio)
            frame.paste(bit, ((W - BIT_LATO) // 2, BIT_Y + bob), bit)
            proc.stdin.write(frame.tobytes())
            t += 1
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg non è riuscito a creare il Reel")
    return out
