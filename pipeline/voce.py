"""La voce di Bit: sintesi vocale italiana offline (Piper) con il tono alzato per farla sembrare una vocina.

La voce (it-riccardo_fasol-x-low, licenza libera) viene scaricata la prima volta in ~/.cache/bitquotidiano.
Se Piper o la voce non sono disponibili, il Reel resta muto.
"""
import re
import subprocess
import tarfile
import tempfile
import wave
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

RATE = 44100
ALZA_TONO = 1.25    # quanto è più acuta della voce originale
VELOCITA = 0.82     # atempo dopo l'alzata di tono: riporta la voce più o meno alla velocità originale
CACHE = Path.home() / ".cache" / "bitquotidiano"
MODELLO = CACHE / "it-riccardo_fasol-x-low.onnx"
URL = "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-it-riccardo_fasol-x-low.tar.gz"

_voce = None


def _carica():
    global _voce
    if _voce is None:
        from piper import PiperVoice
        if not MODELLO.exists():
            CACHE.mkdir(parents=True, exist_ok=True)
            tgz = CACHE / "voce.tar.gz"
            urlretrieve(URL, tgz)
            with tarfile.open(tgz) as t:
                t.extractall(CACHE, filter="data")
            tgz.unlink()
        _voce = PiperVoice.load(str(MODELLO))
    return _voce


def disponibile() -> bool:
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
    return np.frombuffer(raw, dtype=np.float32)


def salva(audio: np.ndarray, percorso: Path):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(percorso), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
