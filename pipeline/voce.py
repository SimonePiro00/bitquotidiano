"""La voce di Bit: sintesi vocale italiana offline (Piper) con tono e velocità regolabili.

Le voci (modelli Piper italiani, licenza libera) vengono scaricate la prima volta in ~/.cache/bitquotidiano.
Voce, tono e velocità si possono cambiare con BIT_VOCE, BIT_TONO e BIT_VELOCITA. Se Piper o la voce non sono disponibili, o con BIT_MUTO=1, il Reel resta muto.
"""
import os
import re
import subprocess
import tarfile
import tempfile
import wave
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

RATE = 44100
ALZA_TONO = float(os.environ.get("BIT_TONO", 1.0))       # 1 = tono originale; >1 più acuta
VELOCITA = float(os.environ.get("BIT_VELOCITA", 0.92))   # <1 più lenta dell'originale, per seguire bene il testo
ROBOT = 0.0        # effetto robot: 0 voce pulita (scelta di Simone), 1 solo modulazione
CACHE = Path.home() / ".cache" / "bitquotidiano"
_HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT"
VOCI = {
    # nome: (file del modello, da dove scaricarlo)
    "riccardo": ("it-riccardo_fasol-x-low.onnx",
                 "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-it-riccardo_fasol-x-low.tar.gz"),
    "paola": ("it_IT-paola-medium.onnx", f"{_HF}/paola/medium/it_IT-paola-medium.onnx"),
}
VOCE = os.environ.get("BIT_VOCE", "riccardo")

_voce = None


def _carica():
    global _voce
    if _voce is None:
        from piper import PiperVoice
        nome, url = VOCI[VOCE]
        modello = CACHE / nome
        if not modello.exists():
            CACHE.mkdir(parents=True, exist_ok=True)
            if url.endswith(".tar.gz"):
                tgz = CACHE / "voce.tar.gz"
                urlretrieve(url, tgz)
                with tarfile.open(tgz) as t:
                    t.extractall(CACHE, filter="data")
                tgz.unlink()
            else:
                urlretrieve(url + ".json", CACHE / (nome + ".json"))
                urlretrieve(url, modello)
        _voce = PiperVoice.load(str(modello))
    return _voce


def disponibile() -> bool:
    if os.environ.get("BIT_MUTO"):
        return False
    try:
        _carica()
        return True
    except Exception as e:  # noqa: BLE001 - senza voce il Reel resta muto
        print(f"Voce di Bit non disponibile, Reel muto: {e}")
        return False


def pronuncia(testo: str) -> str:
    """Riscrive ciò che la voce leggerebbe male."""
    testo = re.sub(r"@?bitquotidiano\.it", "bit quotidiano punto it", testo, flags=re.I)
    testo = re.sub(r"(\d+)\s*€", r"\1 euro", testo).replace("€", "euro")
    testo = re.sub(r"\btech\b", "tek", testo, flags=re.I)
    testo = re.sub(r"\bAI\b", "A I", testo)
    return testo.replace('"', "").replace("«", "").replace("»", "")


def parla(testo: str) -> np.ndarray:
    """Audio mono float32 a 44,1 kHz con la vocina di Bit."""
    voce = _carica()
    with tempfile.TemporaryDirectory() as tmp:
        sorgente = Path(tmp) / "voce.wav"
        with wave.open(str(sorgente), "wb") as w:
            voce.synthesize_wav(pronuncia(testo), w)
        with wave.open(str(sorgente)) as w:
            rate = w.getframerate()
        filtro = f"asetrate={int(rate * ALZA_TONO)},aresample={RATE},atempo={VELOCITA}"
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(sorgente), "-af", filtro,
                              "-ac", "1", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    if ROBOT:
        # Modulazione ad anello, il classico effetto "voce da robot", mescolata alla voce pulita.
        t = np.arange(audio.size) / RATE
        audio = (1 - ROBOT) * audio + ROBOT * audio * np.sin(2 * np.pi * 55 * t) * 1.6
    return audio


def salva(audio: np.ndarray, percorso: Path):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(percorso), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
