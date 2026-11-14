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
# Voci Kokoro (licenza Apache 2.0), più espressive: servono kokoro, torch ed espeak-ng (vedi workflow reel.yml).
KOKORO = {"sara": "if_sara", "nicola": "im_nicola"}
VOCE = os.environ.get("BIT_VOCE", "riccardo")
# Voci neurali di Google Cloud Text-to-Speech: BIT_VOCE="google:it-IT-Chirp3-HD-..." con la chiave in GOOGLE_TTS_KEY.
GOOGLE = VOCE.split(":", 1)[1] if VOCE.startswith("google:") else None
# Voci Gemini-TTS (sempre Google Cloud Text-to-Speech, stessa chiave): BIT_VOCE="gemini:Achird".
# Seguono un'indicazione di stile scritta (BIT_VOCE_STILE), quindi possono suonare più vive e meno "lettura".
GEMINI = VOCE.split(":", 1)[1] if VOCE.startswith("gemini:") else None
# Scelta di Simone (14/11/2026): Puck con gemini-2.5-flash-tts e tono "racconto a un amico".
GEMINI_MODELLO = os.environ.get("BIT_VOCE_MODELLO", "gemini-2.5-flash-tts")
STILE = os.environ.get("BIT_VOCE_STILE", (
    "Parla in italiano in modo naturale, come un ragazzo che racconta di corsa "
    "a un amico una cosa che gli è appena successa: tono caldo e complice, "
    "ritmo VELOCE e incalzante, frasi attaccate senza pause lunghe, "
    "niente tono da annunciatore o da pubblicità."))
# Gemini non ha un parametro di velocità: si accelera dopo (atempo, non cambia il tono) e si accorciano le pause interne.
GEMINI_VELOCITA = float(os.environ.get("BIT_VOCE_ACCELERA", 1.25))
PAUSA_MAX = 0.12   # secondi: le pause interne più lunghe vengono accorciate a questo

_voce = None


def _carica():
    global _voce
    if _voce is None and VOCE in KOKORO:
        from kokoro import KPipeline
        _voce = KPipeline(lang_code="i")
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
    if GOOGLE or GEMINI:
        return bool(os.environ.get("GOOGLE_TTS_KEY") or os.environ.get("GEMINI_API_KEY"))
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
    if GEMINI and os.environ.get("GOOGLE_SA_JSON"):
        return _google(testo)        # Gemini via Cloud Text-to-Speech con account di servizio
    if GEMINI:
        return _gemini_api(testo)
    if GOOGLE:
        return _google(testo)
    voce = _carica()
    if VOCE in KOKORO:
        # Kokoro regola la velocità da sé e lavora a 24 kHz: si porta a 44,1 kHz.
        a24 = np.concatenate([np.asarray(a, dtype=np.float32) for _, _, a in voce(pronuncia(testo), voice=KOKORO[VOCE], speed=VELOCITA)])
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", "24000", "-ac", "1", "-i", "-",
                              "-ar", str(RATE), "-f", "f32le", "-"], input=a24.tobytes(), capture_output=True, check=True).stdout
        return np.frombuffer(raw, dtype=np.float32).copy()
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


def _google(testo: str) -> np.ndarray:
    """Sintesi con Google Cloud Text-to-Speech (la chiave va solo nei Secrets di GitHub, mai nel codice)."""
    import base64
    import json
    from urllib.request import Request, urlopen

    corpo = {"input": {"text": pronuncia(testo)},
             "voice": {"languageCode": "it-IT", "name": GOOGLE},
             "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": RATE, "speakingRate": VELOCITA}}
    if GEMINI:
        corpo = {"input": {"text": pronuncia(testo), "prompt": STILE},
                 "voice": {"languageCode": "it-IT", "name": GEMINI, "modelName": GEMINI_MODELLO},
                 "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": RATE}}
    intestazioni = {"Content-Type": "application/json"}
    if GEMINI and os.environ.get("GOOGLE_SA_JSON"):
        intestazioni.update(_token_account_servizio())
    else:
        intestazioni["X-Goog-Api-Key"] = os.environ["GOOGLE_TTS_KEY"]
    req = Request("https://texttospeech.googleapis.com/v1/text:synthesize", data=json.dumps(corpo).encode(), headers=intestazioni)
    from urllib.error import HTTPError
    try:
        risposta = urlopen(req, timeout=60).read()
    except HTTPError as e:   # il messaggio di Google dice cosa manca (API da attivare, permessi...)
        raise RuntimeError(f"Google TTS {e.code}: {e.read().decode(errors='replace')[:800]}") from None
    wav = base64.b64decode(json.loads(risposta)["audioContent"])
    import io
    with wave.open(io.BytesIO(wav)) as w:
        rate, canali, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    if canali > 1:
        audio = audio.reshape(-1, canali).mean(axis=1)
    filtro = f"aresample={RATE}"
    if GEMINI:
        audio = _accorcia_pause(audio, rate)
        if GEMINI_VELOCITA != 1:
            filtro = f"atempo={GEMINI_VELOCITA},{filtro}"
    if rate != RATE or GEMINI:   # Gemini-TTS risponde a 24 kHz qualunque cosa si chieda
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-",
                              "-af", filtro, "-f", "f32le", "-"], input=audio.tobytes(), capture_output=True, check=True).stdout
        audio = np.frombuffer(raw, dtype=np.float32).copy()
    return audio


def _accorcia_pause(audio: np.ndarray, rate: int, soglia: float = 0.015) -> np.ndarray:
    """Riduce a PAUSA_MAX ogni silenzio interno più lungo (Gemini respira parecchio tra le frasi)."""
    blocco = int(0.01 * rate)
    n = audio.size // blocco
    if n == 0:
        return audio
    energia = np.sqrt(np.mean(audio[:n * blocco].reshape(n, blocco) ** 2, axis=1))
    tieni, muti, max_muti = [], 0, int(PAUSA_MAX / 0.01)
    for i, e in enumerate(energia):
        muti = muti + 1 if e < soglia else 0
        if muti <= max_muti:
            tieni.append(audio[i * blocco:(i + 1) * blocco])
    tieni.append(audio[n * blocco:])
    return np.concatenate(tieni)


def rifila(audio: np.ndarray, soglia: float = 0.02, margine: float = 0.04) -> np.ndarray:
    """Toglie il silenzio all'inizio e alla fine di una frase (le voci Gemini ne lasciano parecchio)."""
    forte = np.flatnonzero(np.abs(audio) > soglia)
    if forte.size == 0:
        return audio
    m = int(margine * RATE)
    return audio[max(0, forte[0] - m):forte[-1] + m]


MODELLI_GEMINI = [GEMINI_MODELLO, "gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts", "gemini-2.5-flash-tts"]


def _gemini_api(testo: str) -> np.ndarray:
    """Voce Gemini tramite la Gemini API (basta una chiave API, niente account di servizio).
    Chiave: GEMINI_API_KEY (da Google AI Studio) oppure la stessa GOOGLE_TTS_KEY se ha la Generative Language API."""
    import base64
    import json
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    chiave = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_TTS_KEY"]
    print("Voce Gemini: uso la chiave", "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else "GOOGLE_TTS_KEY (GEMINI_API_KEY vuota)")
    import hashlib   # solo un'impronta per capire se le due chiavi sono uguali, mai la chiave
    impronta = lambda k: hashlib.sha256(k.strip().encode()).hexdigest()[:6] if k else "-"
    print("Impronte chiavi: GEMINI", impronta(os.environ.get("GEMINI_API_KEY", "")), "TTS", impronta(os.environ.get("GOOGLE_TTS_KEY", "")))
    corpo = {"contents": [{"parts": [{"text": f"{STILE}\n\nTesto da leggere: {pronuncia(testo)}"}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI}}}}}
    ultimo = ""
    for modello in dict.fromkeys(MODELLI_GEMINI):
        req = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{modello}:generateContent",
                      data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": chiave})
        try:
            r = json.loads(urlopen(req, timeout=120).read())
        except HTTPError as e:
            ultimo = f"{modello} {e.code}: {e.read().decode(errors='replace')[:600]}"
            if e.code in (402, 404, 429):
                print("Voce Gemini:", ultimo[:160])
                continue   # modello non disponibile o senza credito per quel modello: prova il successivo
            raise RuntimeError(f"Gemini API {ultimo}") from None
        dati = r["candidates"][0]["content"]["parts"][0]["inlineData"]
        pcm = np.frombuffer(base64.b64decode(dati["data"]), dtype=np.int16).astype(np.float32) / 32768
        rate = int(re.search(r"rate=(\d+)", dati.get("mimeType", "")).group(1)) if "rate=" in dati.get("mimeType", "") else 24000
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-",
                              "-ar", str(RATE), "-f", "f32le", "-"], input=pcm.tobytes(), capture_output=True, check=True).stdout
        print(f"Voce Gemini: modello {modello}")
        return np.frombuffer(raw, dtype=np.float32).copy()
    raise RuntimeError(f"Gemini API: nessun modello TTS disponibile ({ultimo})")


_token = None
_progetto = ""


def _token_account_servizio() -> dict:
    """Token OAuth dall'account di servizio (secret GOOGLE_SA_JSON): serve per Gemini-TTS su Cloud Text-to-Speech."""
    global _token, _progetto
    import json
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GReq
    if _token is None:
        info = json.loads(os.environ["GOOGLE_SA_JSON"])
        _token = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
        _progetto = info.get("project_id", "")
    if not _token.valid:
        _token.refresh(GReq())
    return {"Authorization": f"Bearer {_token.token}", "x-goog-user-project": _progetto}
