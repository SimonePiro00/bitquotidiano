# Bit Quotidiano (@bitquotidiano.it): pagina Instagram tech gestita da agenti

Prototipo di pipeline che osserva **@technologybrief**, rileva i nuovi post e prepara
per ognuno un **carosello originale in italiano** (testo e grafica propri), pubblicato
sul nostro account solo dopo approvazione.

## Come funziona

1. **Rilevamento** (`pipeline/monitor.py`): ogni 2 ore legge gli ultimi post della pagina
   sorgente con la *Business Discovery API* ufficiale di Instagram (nessuno scraping).
   Gli ID già visti stanno in `state/seen.json`; al primo avvio parte dai post futuri.
2. **Generazione** (`pipeline/generate.py`): Claude riceve didascalia e immagine del post
   come spunto e scrive un post nuovo: 3-6 slide, didascalia, hashtag e una lista di
   affermazioni da verificare. Non traduce né copia la struttura dell'originale.
3. **Grafica** (`pipeline/render.py`): disegna le slide 1080x1350 con uno stile nostro.
   Se l'immagine sorgente contiene dati, Claude ne estrae le informazioni e la seconda slide
   diventa un'**infografica ridisegnata da zero** in uno di tre modelli: `numeri` (cifre chiave),
   `barre` (confronto di valori), `timeline` (tappe). Le immagini originali non vengono mai riusate;
   ogni numero finisce nella lista da verificare. Esempi in `esempi/infografica_*/slide_2.jpg`.
4. **Approvazione**: le bozze finiscono in `drafts/<id>/` con stato `in_attesa`.
5. **Pubblicazione** (`pipeline/publish.py`): `python run.py publish <id> --conferma`
   crea il carosello tramite la *Content Publishing API* (limite Meta: 50 post / 24h).

## Comandi

```
pip install -r requirements.txt
cp config.example.env .env   # poi compila e carica le variabili
python run.py check [--backfill N]   # cerca nuovi post e crea bozze
python run.py list           # elenca le bozze
python run.py publish ID --conferma
python run.py demo esempi/bozza_esempio.json --out esempi/render   # solo grafica, senza API
```

`.github/workflows/controllo.yml` esegue `check` ogni 2 ore su GitHub Actions.

## Cosa serve per andare in produzione

- Un account Instagram **professionale** (Business o Creator) collegato a una **Pagina Facebook**.
- Un'app su developers.facebook.com con token di lunga durata e permessi
  `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `business_management`.
- Una chiave API Anthropic.
- Un URL pubblico per le immagini (es. GitHub Pages del repository, o un bucket S3/Cloudinary):
  Instagram scarica le slide da lì.
- Un repository GitHub dove tenere il codice e far girare la routine.

## Note su copyright e termini

- Le notizie (i fatti) non sono protette; testo, grafica e foto dell'originale sì.
  Per questo il testo è riscritto e la grafica è generata da zero: non riusiamo le immagini.
- Business Discovery funziona solo se @technologybrief è un account Business/Creator.
  Se non lo fosse, l'alternativa corretta è partire dalle stesse fonti (feed RSS di testate tech)
  invece di leggere Instagram.
- Meglio tenere l'approvazione umana almeno all'inizio: un errore pubblicato resta visibile.
