"""Campioni di TUTTE le voci italiane maschili Chirp 3 HD di Google (gratuite fino a 1M caratteri/mese), in anteprime/voci-chirp3/."""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

FRASE = ("Paghi il parcheggio con il QR code? Guarda prima se è un adesivo. Il terzo è quello che frega tutti. "
         "Il sito chiede la carta. Paga con l'app del comune. Se il QR è un adesivo, fermati. "
         "Mandalo a chi parcheggia in città. Segui la pagina per non farti fregare!")
GIA_SENTITE = {"Achird", "Algenib", "Algieba", "Alnilam"}
chiave = os.environ["GOOGLE_TTS_KEY"]
req = Request("https://texttospeech.googleapis.com/v1/voices?languageCode=it-IT", headers={"X-Goog-Api-Key": chiave})
voci = [v for v in json.loads(urlopen(req).read())["voices"]
        if "Chirp3-HD" in v["name"] and v["ssmlGender"] == "MALE"]
out = Path("anteprime/voci-chirp3")
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, ".")
for v in sorted(voci, key=lambda v: (v["name"].split("-")[-1] in GIA_SENTITE, v["name"])):
    nome = v["name"].split("-")[-1]
    os.environ["BIT_VOCE"], os.environ["BIT_VELOCITA"] = "google:" + v["name"], "1.15"
    from pipeline import voce
    importlib.reload(voce)
    tmp = out / "tmp.wav"
    voce.salva(voce.parla(FRASE), tmp)
    etichetta = ("gia_sentita_" if nome in GIA_SENTITE else "") + nome
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-b:a", "128k", str(out / f"{etichetta}.mp3")], check=True)
    tmp.unlink()
    print(etichetta)
