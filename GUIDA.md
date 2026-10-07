# Guida: far partire la pagina

I passi 1-5 li fai tu (sono account e chiavi a tuo nome). Dal passo 6 in poi ci penso io.

## 1. Account Instagram professionale
1. Crea il nuovo account Instagram con il nome scelto per la pagina.
2. Impostazioni > Tipo di account e strumenti > **Passa a un account professionale** (Creator o Business).

## 2. Pagina Facebook collegata
1. Crea una Pagina Facebook (anche minimale) con lo stesso nome.
2. Dalla Pagina: Impostazioni > **Account collegati** > Instagram > collega l'account del passo 1.
   Serve perché la lettura dei post di @technologybrief (Business Discovery) funziona solo con questo collegamento.

## 3. App Meta e token
1. Vai su developers.facebook.com, crea un account sviluppatore e poi **Crea app** (tipo *Business*).
2. Aggiungi il prodotto **Instagram** con la configurazione "API con accesso Facebook".
3. Apri **Graph API Explorer**, scegli la tua app, clicca *Generate Access Token* e concedi:
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`, `pages_read_engagement`, `business_management`
   (`instagram_manage_insights` serve per leggere gli altri account; se la Pagina è in un portfolio business aggiungi anche `ads_read`).
4. Il token generato dura poche ore: nello **Strumento di debug dei token** clicca *Extend Access Token*
   per averne uno da 60 giorni. (Più avanti possiamo passare a un "utente di sistema" in Business Manager,
   con un token che non scade.)
5. Sempre nell'Explorer esegui `me/accounts?fields=instagram_business_account{id,username}`:
   il numero in `instagram_business_account.id` è il tuo **IG_USER_ID**.

L'app può restare in modalità sviluppo: pubblichi solo sul tuo account, quindi non serve la revisione di Meta.

## 4. Chiave Anthropic
Su console.anthropic.com crea una chiave API e carica un po' di credito.
Ogni bozza costa indicativamente pochi centesimi.

## 5. Repository GitHub
1. Crea un repository **pubblico** (es. `instagram-tech-it`): pubblico serve perché Instagram
   deve poter scaricare le immagini.
2. Collegalo al progetto da [Impostazioni progetto > Risorse] e dimmi il nome.
3. In Settings > Secrets and variables > Actions aggiungi i **Secrets**:
   `ANTHROPIC_API_KEY`, `META_ACCESS_TOKEN`, `IG_USER_ID`.
   Non incollarli in chat: vanno solo lì.

## 6. Cosa faccio io
1. Carico il codice nel repository e attivo GitHub Pages, che ospita le immagini.
2. Imposto le variabili `PUBLIC_IMAGE_BASE_URL` e `BRAND_HANDLE`.
3. Verifico che @technologybrief sia leggibile con Business Discovery.
4. Genero 2-3 bozze di prova dagli ultimi post e te le mostro, senza pubblicare nulla.

## 7. Uso quotidiano
- Ogni 2 ore il workflow **Controllo nuovi post** crea le bozze in `drafts/<id>/`.
- Le guardi (slide, didascalia e lista "da verificare").
- Per pubblicarne una: Actions > **Pubblica bozza** > Run workflow > inserisci l'ID.
  Oppure dimmi qui "pubblica <id>".

## Promemoria
- Il token da 60 giorni va rinnovato, a meno di passare all'utente di sistema.
- Limite di Meta: 50 pubblicazioni ogni 24 ore.
