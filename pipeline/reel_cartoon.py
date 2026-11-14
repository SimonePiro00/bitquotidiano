"""Reel "cartoon" (prova di novembre 2026): Bit animato, icone che si muovono, transizioni a fumetto e sottotitoli.

Circa 12 secondi. La pillola "Mandalo a ..." è in alto dal primo fotogramma. Struttura:
gancio (testo già completo al fotogramma 0) -> tre punti con icona animata -> invito a inoltrare -> loop.
La voce legge esattamente il testo sullo schermo; la parola detta in quel momento si accende (sottotitoli).
I fotogrammi li disegna Chromium (pipeline/cartoon/scena.js), l'audio è voce + musichetta originale + effetti.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from . import musica, voce

FPS = 30
QUI = Path(__file__).parent / "cartoon"
ICONE = ["qr", "carta", "telefono", "stop", "avviso", "lucchetto", "chat", "pacco", "link", "soldi", "batteria"]
TRANSIZIONE = 0.32   # secondi della banda arancio tra una scena e l'altra (vedi scena.js)


def _parole(testo: str) -> list[str]:
    return [p.replace("*", "") for p in testo.split() if p.replace("*", "")]


def _tempi_parole(parole: list[str], inizio: int, durata: int) -> list[list[int]]:
    """Stima quando viene detta ogni parola: tempo proporzionale alle lettere, più una pausa dopo la punteggiatura."""
    pesi = [len(re.sub(r"\W", "", p)) + 2 + (3 if re.search(r"[.,:;?!]$", p) else 0) for p in parole]
    tot, acc, out = sum(pesi) or 1, 0, []
    for w in pesi:
        da = inizio + round(durata * acc / tot)
        acc += w
        out.append([da, inizio + round(durata * acc / tot)])
    return out


def _effetto(tipo: str, rate=voce.RATE) -> np.ndarray:
    """Piccoli effetti sonori sintetizzati: 'whoosh' (transizione) e 'pop' (numero che compare)."""
    rng = np.random.default_rng(7 if tipo == "whoosh" else 3)
    if tipo == "whoosh":
        n = int(0.35 * rate)
        rumore = rng.standard_normal(n)
        inv = np.sin(np.linspace(0, np.pi, n)) ** 2
        # filtro passa-banda che sale: media mobile di lunghezza decrescente
        out = np.zeros(n)
        for i, k in enumerate(np.linspace(40, 6, 8).astype(int)):
            a, b = i * n // 8, (i + 1) * n // 8
            out[a:b] = np.convolve(rumore, np.ones(k) / k, "same")[a:b]
        return (out * inv * 0.5).astype(np.float32)
    if tipo == "rullo":   # rullo di tamburi che accelera e cresce
        n = int(0.62 * rate)
        out = np.zeros(n, dtype=np.float32)
        tempo, colpo = 0.0, 0
        while tempo < 0.6:
            i0 = int(tempo * rate)
            m = min(int(0.05 * rate), n - i0)
            env = np.exp(-np.arange(m) / rate * 60)
            out[i0:i0 + m] += (rng.standard_normal(m) * env * (0.15 + 0.35 * tempo / 0.6)).astype(np.float32)
            tempo += max(0.03, 0.09 - colpo * 0.006)
            colpo += 1
        return out
    if tipo == "ding":
        n = int(0.6 * rate)
        t = np.arange(n) / rate
        return ((np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)) * np.exp(-t * 6) * 0.3).astype(np.float32)
    n = int(0.12 * rate)
    t = np.arange(n) / rate
    f = 900 * np.exp(-t * 25) + 250
    return (np.sin(2 * np.pi * np.cumsum(f) / rate) * np.exp(-t * 30) * 0.45).astype(np.float32)


def copione_e_audio(b: dict, seme: str):
    """Dal JSON della bozza al copione per scena.js e alla traccia audio."""
    gancio, annuncio = b.get("gancio") or b["slides"][0]["titolo"], b.get("annuncio") or "Il terzo è quello che frega tutti"
    invio = b.get("invio") or "*Mandalo* a chi ne ha bisogno"
    punti = b["reel_punti"][:3]
    icone = (b.get("reel_icone") or ["avviso"] * 4) + ["avviso"] * 4
    serie, _, titolo = (b.get("reel_titolo") or "").partition(" · ")
    pulito = lambda x: x.replace("*", "")
    # Invito a seguire (scelto da Simone): segui la pagina per non farti fregare.
    segui = b.get("reel_segui") or "Segui la pagina per non farti fregare!"
    prossima = ""
    frasi = [f"{pulito(gancio)} {annuncio}."] + [p.rstrip(".") + "." for p in punti] + [f"{pulito(invio)}. {segui}"]
    parole_scena = [_parole(gancio) + _parole(annuncio)] + [_parole(p) for p in punti] + [_parole(invio) + _parole(segui)]

    con_voce = voce.disponibile()
    if con_voce:
        parlato = [voce.rifila(voce.parla(f)) for f in frasi]
    else:   # senza voce: ritmo di lettura, circa 14 caratteri al secondo
        parlato = [np.zeros(int(len(f) / 14 * voce.RATE), dtype=np.float32) for f in frasi]
    pausa = [0.25, 0.2, 0.2, 0.3, 0.7]   # respiro dopo ogni frase (l'ultima lascia tempo per il loop)
    SOSPENSE = float(b.get("reel_suspense", 0))   # >0: pausa con rullo prima del terzo punto: rullo di tamburi e lucchetto che trema
    scene, inizio = [], 0
    tipi = ["gancio"] + ["punto"] * len(punti) + ["fine"]
    for i, (tipo, a) in enumerate(zip(tipi, parlato)):
        attacco = 0 if i == 0 else int(TRANSIZIONE * FPS * 0.6)   # la voce parte quando la banda è passata
        sospensione = int(SOSPENSE * FPS) if tipo == "punto" and i == len(punti) else 0
        attacco += sospensione
        dur_voce = int(np.ceil(a.size / voce.RATE * FPS))
        dur = attacco + dur_voce + int(pausa[min(i, 4)] * FPS)
        sc = {"tipo": tipo, "da": inizio, "a": inizio + dur, "voce_da": inizio + attacco,
              "parole": _tempi_parole(parole_scena[i], inizio + attacco, dur_voce)}
        if tipo == "punto":
            sc["i"], sc["suspense"] = i - 1, sospensione
        scene.append(sc)
        inizio += dur
    frames = inizio

    # Audio: musica sotto, voce sopra, effetti sulle transizioni.
    n_campioni = int(frames / FPS * voce.RATE)
    audio = musica.genera(frames / FPS, seme)[:n_campioni]
    audio = np.pad(audio, (0, max(0, n_campioni - audio.size))) * (0.28 if con_voce else 0.6)
    bocca = np.zeros(frames)
    for sc, a in zip(scene, parlato):
        i0 = int(sc["voce_da"] / FPS * voce.RATE)
        n = min(a.size, n_campioni - i0)
        audio[i0:i0 + n] += a[:n] * 0.95
        if con_voce:
            for f in range(sc["voce_da"], min(frames, sc["voce_da"] + int(np.ceil(a.size / voce.RATE * FPS)))):
                pezzo = a[int((f - sc["voce_da"]) / FPS * voce.RATE):int((f - sc["voce_da"] + 1) / FPS * voce.RATE)]
                bocca[f] = float(np.sqrt(np.mean(pezzo ** 2))) if pezzo.size else 0
        else:   # bocca finta mentre "parla"
            for f in range(sc["voce_da"], sc["voce_da"] + int(a.size / voce.RATE * FPS)):
                bocca[f] = 0.5 + 0.5 * np.sin(f * 1.7)
        if sc.get("suspense"):
            effetti = [("whoosh", sc["da"] / FPS - 0.1), ("rullo", sc["da"] / FPS + 0.05), ("ding", sc["voce_da"] / FPS - 0.12)]
        elif sc["tipo"] != "gancio":
            effetti = [("whoosh", sc["da"] / FPS - 0.1), ("pop", sc["da"] / FPS + 0.15)]
        else:
            effetti = []
        for nome, quando in effetti:
            e = _effetto(nome)
            j = max(0, int(quando * voce.RATE))
            m = min(e.size, n_campioni - j)
            audio[j:j + m] += e[:m]
    if con_voce and bocca.max() > 0:
        bocca = np.clip(bocca / np.percentile(bocca[bocca > 0], 90), 0, 1)
    audio = np.clip(audio, -1, 1)

    copione = {"fps": FPS, "frames": frames, "stile": b.get("reel_stile", "schede"), "serie": serie or "Bit Quotidiano", "titolo": titolo,
               "gancio": gancio, "annuncio": annuncio, "invio": invio, "segui": segui, "prossima": prossima, "icona_gancio": icone[0],
               "punti": [{"testo": p, "icona": icone[i + 1]} for i, p in enumerate(punti)],
               "scene": scene, "bocca": [round(float(x), 3) for x in bocca]}
    return copione, audio


def make_reel_cartoon(folder: Path, b: dict, nome="reel.mp4", seme: str | None = None) -> Path:
    copione, audio = copione_e_audio(b, seme or folder.name)
    out = folder / nome
    with tempfile.TemporaryDirectory() as tmp:
        cj, wav = Path(tmp) / "copione.json", Path(tmp) / "audio.wav"
        cj.write_text(json.dumps(copione, ensure_ascii=False))
        musica.salva(audio, wav)
        subprocess.run(["node", str(QUI / "disegna.js"), str(cj), str(out), str(wav)], check=True)
    return out
