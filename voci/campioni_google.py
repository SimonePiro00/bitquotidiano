"""Campioni delle voci italiane di Google (Chirp 3 HD e Neural2) con la frase del Reel: voci/campioni_google/."""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

FRASE = ("Il tuo pacco è in giacenza? Non cliccare quel link. Ecco tre segnali, e il terzo è quello che frega tutti. "
         "Uno: ti mette fretta. Due: chiede solo pochi euro. Tre: il link non è del corriere. "
         "Mandalo a chi aspetta sempre un pacco, e segui per la prossima!")
chiave = os.environ["GOOGLE_TTS_KEY"]
req = Request("https://texttospeech.googleapis.com/v1/voices?languageCode=it-IT", headers={"X-Goog-Api-Key": chiave})
voci = [v for v in json.loads(urlopen(req).read())["voices"] if "Chirp3-HD" in v["name"] or "Neural2" in v["name"]]
scelte = [v for v in voci if "Chirp3-HD" in v["name"]][:8] + [v for v in voci if "Neural2" in v["name"]][:2]
out = Path("voci/campioni_google")
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, ".")
for i, v in enumerate(scelte, 1):
    os.environ["BIT_VOCE"] = "google:" + v["name"]
    import importlib
    from pipeline import voce
    importlib.reload(voce)
    tmp = out / "tmp.wav"
    voce.salva(voce.parla(FRASE), tmp)
    nome = f"{i}_{v['name'].split('-')[-1]}_{v['ssmlGender'][0].lower()}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-b:a", "128k", str(out / f"{nome}.mp3")], check=True)
    tmp.unlink()
    print(nome, v["name"])
