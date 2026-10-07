"""Trasforma un post della pagina sorgente in una bozza originale in italiano con Claude."""
import base64
from typing import Literal

import anthropic
import requests
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
- Ricevi TUTTE le immagini del carosello originale, in ordine: leggi il testo di ogni slide, non solo la prima.
- Se il post è un tutorial o una guida (passaggi, impostazioni, componenti, comandi), la bozza deve
  permettere a chi legge di rifarlo davvero: riporta tutti i passaggi concreti, nell'ordine giusto,
  uno o due per slide, numerati nel titolo (es. "1. Apri Impostazioni"). Usa i nomi dei menu come
  appaiono con il dispositivo in italiano; se non sei sicuro del nome italiano, mettilo in `da_verificare`.
  Non sostituire i passaggi con una descrizione generica.
- Dove l'originale mostra un'immagine (schermata, prodotto, componente), compila `illustrazione` per la
  slide corrispondente: verrà disegnata un'illustrazione originale. Al massimo 5 slide con illustrazione.
- Guarda l'immagine del post: se contiene dati, confronti, classifiche o una sequenza di eventi,
  ricavane un'infografica NOSTRA in `infografica` (scegli il tipo più adatto: `numeri` per 1-3 cifre
  chiave, `barre` per confrontare 2-6 valori numerici nella stessa unità, `timeline` per 3-6 tappe).
  Usa la stessa informazione, non la stessa impaginazione. Ogni numero che riporti va anche in
  `da_verificare`. Se l'immagine non ha dati utili, lascia `infografica` vuota."""


class Slide(BaseModel):
    titolo: str = Field(description="Titolo breve della slide, max 60 caratteri")
    testo: str = Field(description="Corpo della slide, max 220 caratteri; vuoto per la copertina")
    illustrazione: str | None = Field(
        description="Se nel post originale questa parte era accompagnata da un'immagine utile (schermata, oggetto, "
        "componente, schema), descrivi in max 300 caratteri un'illustrazione NOSTRA da disegnare che mostri lo stesso "
        "concetto in modo schematico. Null se non serve. Mai loghi, marchi o copie di immagini altrui."
    )


class Elemento(BaseModel):
    etichetta: str = Field(description="Nome della voce o data della tappa, max 30 caratteri")
    valore: float | None = Field(description="Valore numerico (numeri e barre); null per la timeline")
    testo: str = Field(description="Per `numeri` e `barre`: solo il valore formattato, max 12 caratteri (es. '1,2 mld', '3,5\"'); per `timeline`: breve descrizione, max 80 caratteri")


class Infografica(BaseModel):
    tipo: Literal["numeri", "barre", "timeline"]
    titolo: str = Field(description="Titolo dell'infografica, max 60 caratteri")
    unita: str = Field(description="Unità di misura dei valori (es. 'miliardi di $'), vuota se non serve")
    elementi: list[Elemento]
    nota: str = Field(description="Fonte dei dati o nota metodologica, max 90 caratteri")


class Bozza(BaseModel):
    argomento: str
    slides: list[Slide] = Field(description="Da 3 a 9 slide, la prima è la copertina; per i tutorial una slide per passaggio")
    didascalia: str = Field(description="Caption Instagram in italiano, max 1500 caratteri")
    hashtag: list[str] = Field(description="8-15 hashtag pertinenti, senza #")
    infografica: Infografica | None = Field(description="Inserita come seconda slide")
    da_verificare: list[str] = Field(description="Affermazioni da controllare prima di pubblicare")


def _image_urls(post: dict) -> list[str]:
    children = post.get("children", {}).get("data", [])
    if children:
        return [c["media_url"] for c in children if c.get("media_type") == "IMAGE" and c.get("media_url")]
    if post.get("media_type") == "IMAGE" and post.get("media_url"):
        return [post["media_url"]]
    return []


def _download_images(post: dict, limit: int = 10) -> list[tuple[str, str]]:
    """Scarica le immagini del post e le restituisce in base64 (gli URL di Instagram non sono
    sempre raggiungibili dall'API di Claude). Le immagini non scaricabili vengono saltate."""
    images = []
    for url in _image_urls(post)[:limit]:
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        mt = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        if mt not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            mt = "image/jpeg"
        images.append((mt, base64.b64encode(resp.content).decode()))
    return images


def generate_draft(post: dict, client: anthropic.Anthropic | None = None) -> Bozza:
    client = client or anthropic.Anthropic()
    content: list[dict] = [
        {"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}
        for mt, data in _download_images(post)
    ]
    print(f"Post {post.get('id')}: {len(content)} immagini su {len(_image_urls(post))} lette")
    content.append({
        "type": "text",
        "text": (
            f"Post di spunto (pubblicato {post.get('timestamp')}), "
            f"{len(content)} immagini allegate in ordine.\n\n"
            f"Didascalia originale:\n{post.get('caption') or '(senza didascalia)'}"
        ),
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
        # Un'immagine non accettata (formato o dimensione): si riprova solo col testo.
        response = ask([b for b in content if b["type"] == "text"])
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"Generazione non riuscita (stop_reason={response.stop_reason})")
    return response.parsed_output
