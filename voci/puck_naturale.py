"""Varianti più naturali della voce Puck (Chirp 3 HD, gratuita), in anteprime/voci-puck/. Non pubblica nulla.

Tre leve: velocità più bassa, testo letto tutto di fila (non frase per frase) e pause/punteggiatura da parlato.
L'ultima variante è Puck con Gemini-TTS (non gratuita, ~1 cent a Reel) solo come termine di paragone.
"""
import base64
import io
import json
import os
import subprocess
import sys
import wave
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, ".")
VOCE = "it-IT-Chirp3-HD-Puck"
TESTO = ("Paghi il parcheggio con il QR code? Guarda prima se è un adesivo. Il terzo è quello che frega tutti. "
         "Il sito chiede la carta. Paga con l'app del comune. Se il QR è un adesivo, fermati. "
         "Mandalo a chi parcheggia in città. Segui la pagina per non farti fregare!")
# Stesso contenuto, scritto come si parla: pause vere e punteggiatura che guida l'intonazione.
PARLATO = ("Paghi il parcheggio col QR code? [pause short] Ecco, guarda prima se è un adesivo. "
           "[pause short] E il terzo... è quello che frega tutti. [pause] "
           "Uno: il sito ti chiede la carta? [pause short] Strano. [pause] "
           "Due: paga con l'app del comune, [pause short] sempre. [pause] "
           "Tre: se il QR è un adesivo... [pause short] fermati. [pause] "
           "Mandalo a chi parcheggia in città, [pause short] e segui la pagina per non farti fregare!")
SENZA_TAG = PARLATO.replace("[pause short] ", "").replace("[pause] ", "")

VARIANTI = [
    ("1_com_era_1.15", {"text": TESTO}, 1.15),
    ("2_piu_calma_1.0", {"text": TESTO}, 1.0),
    ("3_parlato_1.05", {"markup": PARLATO}, 1.05),
    ("4_parlato_1.12", {"markup": PARLATO}, 1.12),
    ("5_parlato_senza_pause_1.1", {"text": SENZA_TAG}, 1.1),
]
out = Path("anteprime/voci-puck")
out.mkdir(parents=True, exist_ok=True)


def mp3(wav_bytes: bytes, nome: str):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "-", "-b:a", "128k", str(out / f"{nome}.mp3")],
                   input=wav_bytes, check=True)
    print(nome)


for nome, inp, vel in VARIANTI:
    corpo = {"input": inp, "voice": {"languageCode": "it-IT", "name": VOCE},
             "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 44100, "speakingRate": vel}}
    req = Request("https://texttospeech.googleapis.com/v1/text:synthesize", data=json.dumps(corpo).encode(),
                  headers={"Content-Type": "application/json", "X-Goog-Api-Key": os.environ["GOOGLE_TTS_KEY"]})
    try:
        mp3(base64.b64decode(json.loads(urlopen(req, timeout=60).read())["audioContent"]), nome)
    except Exception as e:  # noqa: BLE001
        print(nome, "FALLITA:", getattr(e, "read", lambda: b"")().decode(errors="replace")[:500] or e)

# Paragone a pagamento: Puck con Gemini-TTS e un'indicazione di stile "naturale".
if os.environ.get("GOOGLE_SA_JSON"):
    os.environ["BIT_VOCE"] = "gemini:Puck"
    os.environ["BIT_VOCE_STILE"] = ("Parla in italiano in modo naturale e rilassato, come un ragazzo che racconta "
                                    "a un amico una cosa che gli è appena successa: tono caldo e complice, "
                                    "ritmo vivace ma senza fretta, niente tono da annunciatore o da pubblicità.")
    from pipeline import voce
    a = voce.parla(SENZA_TAG)
    buf = io.BytesIO()
    voce.salva(a, out / "tmp.wav")
    mp3((out / "tmp.wav").read_bytes(), "6_gemini_puck_a_pagamento")
    (out / "tmp.wav").unlink()
