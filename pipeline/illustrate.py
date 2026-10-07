"""Illustrazioni originali per le slide: Claude disegna un SVG nello stile della pagina,
che viene convertito in PNG. Niente immagini prese dal post sorgente."""
import io
import re

import anthropic
import cairosvg
from PIL import Image

from .generate import MODEL

BOX_W, BOX_H = 900, 560

SYSTEM = f"""Sei l'illustratore di una pagina Instagram italiana di notizie tech.
Disegni illustrazioni vettoriali piatte (flat), pulite e leggibili su telefono.
Rispondi SOLO con un unico elemento <svg> valido, senza testo prima o dopo.
Regole:
- viewBox="0 0 {BOX_W} {BOX_H}", sfondo trasparente (nessun rettangolo a tutto campo).
- Palette obbligatoria: blu notte #09112A (già lo sfondo della slide, usalo solo per dettagli),
  arancio #FF7A1A come unico accento, bianco #F2F5FA, grigio-blu #8796B4, blu medio #1C2B55 per le superfici.
- Stile: forme geometriche, angoli arrotondati, tratti 4-6px, nessun gradiente complesso, nessuna ombra realistica.
- Testo: al massimo poche parole brevi (etichette di menu o componenti), font-family="DejaVu Sans", min 26px.
- Vietati: loghi, marchi, personaggi protetti da copyright, volti reali, elementi <image>, link esterni, script.
- Se il soggetto è un'interfaccia (es. impostazioni di un telefono), disegnane una versione schematica generica,
  non una copia fedele dell'interfaccia di un prodotto."""


def _clean(svg: str) -> str | None:
    match = re.search(r"<svg\b.*?</svg>", svg, re.S | re.I)
    if not match:
        return None
    svg = match.group(0)
    # Niente contenuti esterni o eseguibili, anche se il renderer non li caricherebbe comunque.
    svg = re.sub(r"<(script|image|foreignObject)\b.*?(</\1>|/>)", "", svg, flags=re.S | re.I)
    svg = re.sub(r'\s(xlink:)?href="(?!#)[^"]*"', "", svg)
    return svg


def draw(descrizione: str, contesto: str, client: anthropic.Anthropic | None = None) -> Image.Image | None:
    """Restituisce l'illustrazione come immagine RGBA, oppure None se qualcosa va storto."""
    client = client or anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": f"Contesto della slide: {contesto}\n\nDisegna: {descrizione}"}],
        )
    except anthropic.APIError as e:
        print(f"Illustrazione non generata: {e.__class__.__name__}")
        return None
    if response.stop_reason in ("refusal", "max_tokens"):
        return None
    text = "".join(b.text for b in response.content if b.type == "text")
    svg = _clean(text)
    if not svg:
        return None
    try:
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=BOX_W * 2, output_height=BOX_H * 2)
    except Exception as e:  # SVG malformato: la slide resta senza illustrazione
        print(f"SVG non valido: {e}")
        return None
    return Image.open(io.BytesIO(png)).convert("RGBA")
