"""Trasforma un post della pagina sorgente in una bozza originale in italiano con Claude."""
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-5-5"

SYSTEM = """Sei il redattore di una pagina Instagram italiana di notizie tech, brevi e chiare.
Ricevi un post di un'altra pagina (in inglese) come SPUNTO sull'argomento.
Regole:
- Scrivi un post nuovo e originale in italiano: non tradurre frase per frase, non copiare struttura,
  battute o grafica dell'originale. Riporta solo i fatti, con parole tue.
- Tono: diretto, informativo, accessibile. Niente clickbait.
- Se un'affermazione è incerta o non verificabile dal contenuto ricevuto, inseriscila in `da_verificare`
  invece di presentarla come fatto.
- Non citare né taggare la pagina di origine nel testo.
- Le slide sono un carosello: la prima è un titolo forte, le successive spiegano (max ~220 caratteri l'una).
- Guarda l'immagine del post: se contiene dati, confronti, classifiche o una sequenza di eventi,
  ricavane un'infografica NOSTRA in `infografica` (scegli il tipo più adatto: `numeri` per 1-3 cifre
  chiave, `barre` per confrontare 2-6 valori numerici nella stessa unità, `timeline` per 3-6 tappe).
  Usa la stessa informazione, non la stessa impaginazione. Ogni numero che riporti va anche in
  `da_verificare`. Se l'immagine non ha dati utili, lascia `infografica` vuota."""


class Slide(BaseModel):
    titolo: str = Field(description="Titolo breve della slide, max 60 caratteri")
    testo: str = Field(description="Corpo della slide, max 220 caratteri; vuoto per la copertina")


class Elemento(BaseModel):
    etichetta: str = Field(description="Nome della voce o data della tappa, max 30 caratteri")
    valore: float | None = Field(description="Valore numerico (numeri e barre); null per la timeline")
    testo: str = Field(description="Breve descrizione o valore formattato (es. '1,2 mld'), max 80 caratteri")


class Infografica(BaseModel):
    tipo: Literal["numeri", "barre", "timeline"]
    titolo: str = Field(description="Titolo dell'infografica, max 60 caratteri")
    unita: str = Field(description="Unità di misura dei valori (es. 'miliardi di $'), vuota se non serve")
    elementi: list[Elemento]
    nota: str = Field(description="Fonte dei dati o nota metodologica, max 90 caratteri")


class Bozza(BaseModel):
    argomento: str
    slides: list[Slide] = Field(description="Da 3 a 6 slide, la prima è la copertina")
    didascalia: str = Field(description="Caption Instagram in italiano, max 1500 caratteri")
    hashtag: list[str] = Field(description="8-15 hashtag pertinenti, senza #")
    infografica: Infografica | None = Field(description="Inserita come seconda slide")
    da_verificare: list[str] = Field(description="Affermazioni da controllare prima di pubblicare")


def generate_draft(post: dict, client: anthropic.Anthropic | None = None) -> Bozza:
    client = client or anthropic.Anthropic()
    content: list[dict] = []
    image_url = post.get("media_url") or next(
        (c.get("media_url") for c in post.get("children", {}).get("data", []) if c.get("media_type") == "IMAGE"),
        None,
    )
    if image_url and post.get("media_type") != "VIDEO":
        content.append({"type": "image", "source": {"type": "url", "url": image_url}})
    content.append({
        "type": "text",
        "text": f"Post di spunto (pubblicato {post.get('timestamp')}):\n\n{post.get('caption') or '(senza didascalia)'}",
    })

    def ask(blocks):
        return client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": blocks}],
            output_format=Bozza,
        )

    try:
        response = ask(content)
    except anthropic.BadRequestError:
        # L'URL dell'immagine di Instagram può essere scaduto o non scaricabile: si riprova solo col testo.
        response = ask([b for b in content if b["type"] == "text"])
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"Generazione non riuscita (stop_reason={response.stop_reason})")
    return response.parsed_output
