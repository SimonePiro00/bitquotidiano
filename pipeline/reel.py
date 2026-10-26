"""Crea un Reel verticale (1080x1920) da una bozza, pensato per chi non segue ancora la pagina.

Struttura: gancio con il titolo nei primi 2 secondi, un punto per schermata con poco testo grande,
chiusura con l'invito a seguire. I fotogrammi sono disegnati con Pillow (il testo entra con una
breve animazione) e passati a ffmpeg. Audio muto: l'API non permette la musica di Instagram.
"""
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from .render import FONT_BOLD, FONT_REG, _font, _wrap

W, H, FPS = 1080, 1920, 30
BG, FG, ACCENT, MUTED = (9, 17, 42), (242, 245, 250), (255, 122, 26), (135, 150, 180)
X0, X1 = 90, 950          # fuori dalle icone di Instagram a destra
TOP, BOTTOM = 300, 1480   # fuori da intestazione e didascalia
ENTRATA = 8               # fotogrammi dell'animazione d'ingresso
MASCOTTE = Path(__file__).resolve().parent.parent / "assets" / "mascotte_bit.png"


def _sintesi(testo: str, limite: int = 130) -> str:
    frasi = re.split(r"(?<=[.!?])\s+", testo.strip())
    out = ""
    for f in frasi:
        # Una frase brevissima (es. "0 €, 5 minuti.") da sola non dice niente: aggiunge la successiva.
        if len(out) >= 40 and len(out) + len(f) + 1 > limite:
            break
        out = f"{out} {f}".strip()
    return out


def _blocco(d, righe, y, font, colore):
    for r in righe:
        d.text((X0, y), r, font=font, fill=colore)
        y += int(font.size * 1.25)
    return y


def _schermata(titolo: str, testo: str, n: int, tot: int, tipo: str):
    """Restituisce (sfondo fisso, livello testo trasparente, altezza del testo)."""
    base = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(base)
    d.text((X0, 200), "@bitquotidiano.it", font=_font(FONT_BOLD, 38), fill=ACCENT)
    seg = (X1 - X0 - (tot - 1) * 8) / tot
    for i in range(tot):
        x = X0 + i * (seg + 8)
        d.rounded_rectangle([x, 160, x + seg, 168], 4, fill=ACCENT if i <= n else (40, 52, 90))
    testo_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t = ImageDraw.Draw(testo_img)
    if tipo == "gancio":
        f = _font(FONT_BOLD, 92)
        righe = _wrap(t, titolo, f, X1 - X0)
        y = 520
        y = _blocco(t, righe, y, f, FG)
        t.rounded_rectangle([X0, y + 20, X0 + 160, y + 34], 7, fill=ACCENT)
        y += 60
    elif tipo == "fine":
        y = 560
        y = _blocco(t, ["Segui"], y, _font(FONT_BOLD, 96), FG)
        y = _blocco(t, ["@bitquotidiano.it"], y, _font(FONT_BOLD, 84), ACCENT)
        y = _blocco(t, _wrap(t, "Ogni giorno un trucco tech spiegato semplice.", _font(FONT_REG, 50), X1 - X0), y + 40, _font(FONT_REG, 50), FG)
        y = _blocco(t, _wrap(t, "Tutti i dettagli nel carosello sul profilo.", _font(FONT_REG, 42), X1 - X0), y + 20, _font(FONT_REG, 42), MUTED)
    else:
        ft, fx = _font(FONT_BOLD, 92), _font(FONT_REG, 60)
        rt, rx = _wrap(t, titolo, ft, X1 - X0), _wrap(t, testo, fx, X1 - X0)
        altezza = len(rt) * ft.size * 1.25 + 60 + len(rx) * fx.size * 1.25
        y = int(max(TOP + 120, (TOP + BOTTOM) / 2 - altezza / 2))
        y = _blocco(t, rt, y, ft, FG)
        t.rounded_rectangle([X0, y + 10, X0 + 110, y + 22], 6, fill=ACCENT)
        y = _blocco(t, rx, y + 50, fx, FG)
    if tipo in ("gancio", "fine") and MASCOTTE.exists():
        m = Image.open(MASCOTTE).convert("RGBA").resize((300, 300))
        testo_img.alpha_composite(m, ((W - 300) // 2, min(y + 60, BOTTOM - 300)))
    return base, testo_img


def _durata(testo: str, tipo: str) -> float:
    if tipo == "gancio":
        return 2.2
    if tipo == "fine":
        return 3.0
    return min(5.0, 1.4 + len(testo.split()) / 4.5)


def make_reel(folder: Path, slides: list[dict]) -> Path:
    """slides: le slide della bozza (titolo, testo). L'ultima, l'invito finale del carosello,
    viene sostituita dalla schermata "Segui"."""
    schermate = [(slides[0]["titolo"], "", "gancio")]
    schermate += [(s["titolo"], _sintesi(s["testo"]), "punto") for s in slides[1:-1]]
    schermate.append(("", "", "fine"))
    out = folder / "reel.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n, (titolo, testo, tipo) in enumerate(schermate):
        base, livello = _schermata(titolo, testo, n, len(schermate), tipo)
        fermo = base.copy()
        fermo.paste(livello, (0, 0), livello)
        fermo_bytes = fermo.tobytes()
        totale = int(_durata(f"{titolo} {testo}", tipo) * FPS)
        for k in range(totale):
            if k < ENTRATA:
                p = (k + 1) / ENTRATA
                frame = base.copy()
                l = livello.copy()
                l.putalpha(l.getchannel("A").point(lambda a: int(a * p)))
                frame.paste(l, (0, int(40 * (1 - p))), l)
                proc.stdin.write(frame.tobytes())
            else:
                proc.stdin.write(fermo_bytes)
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg non è riuscito a creare il Reel")
    return out
