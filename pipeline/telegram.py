"""Avvisi a Simone su Telegram (le notifiche dell'app Claude non gli arrivano).

Servono i GitHub Secrets TG_BOT_SECRET (token da @BotFather, passato come TELEGRAM_BOT_TOKEN) e TELEGRAM_CHAT_ID.
Se TELEGRAM_CHAT_ID manca, prova a ricavarlo dall'ultimo messaggio scritto al bot.
Uso: python -m pipeline.telegram "testo"   oppure   python -m pipeline.telegram --esito ID success|failure URL
"""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API = "https://api.telegram.org/bot{}/{}"


def _chiama(metodo: str, **dati) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    with urlopen(API.format(token, metodo), data=urlencode(dati).encode(), timeout=30) as r:
        return json.loads(r.read())


def chat_id() -> str:
    cid = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if cid:
        return cid
    aggiornamenti = _chiama("getUpdates").get("result", [])
    chat = [u["message"]["chat"]["id"] for u in aggiornamenti if "message" in u]
    if not chat:
        sys.exit("Nessun messaggio trovato: scrivi /start al bot su Telegram e riprova.")
    print(f"TELEGRAM_CHAT_ID da salvare nei Secrets: {chat[-1]}")
    return str(chat[-1])


def avvisa(testo: str) -> None:
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("Telegram non configurato (manca TELEGRAM_BOT_TOKEN): nessun avviso.")
        return
    risposta = _chiama("sendMessage", chat_id=chat_id(), text=testo, disable_web_page_preview="true")
    print("Avviso Telegram inviato." if risposta.get("ok") else f"Telegram ha risposto: {risposta}")


def testo_esito(id_: str, esito: str, url_run: str) -> str:
    b = {}
    p = Path("drafts") / id_ / "bozza.json"
    if p.exists():
        b = json.loads(p.read_text())["bozza"]
    titolo = b.get("reel_titolo") or b.get("argomento") or id_
    if esito == "success":
        return f"✅ Reel pubblicato: {titolo}\nRicordati di ricondividerlo nelle storie 📲"
    return (f"⚠️ Pubblicazione NON riuscita: {titolo}\nNon riprovo da solo per evitare doppioni: "
            f"controlla il profilo prima di rilanciare.\nDettagli: {url_run}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--esito"]:
        avvisa(testo_esito(*sys.argv[2:5]))
    else:
        avvisa(" ".join(sys.argv[1:]) or "Prova: gli avvisi di Bit Quotidiano arrivano qui 🤖")
