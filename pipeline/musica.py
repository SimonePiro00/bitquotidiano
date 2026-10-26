"""Musichetta di sottofondo originale per i Reel, composta e sintetizzata da zero (niente diritti d'autore).

Ogni bozza ha la sua: tonalità, tempo, giro di accordi, suoni e melodia dipendono da un seme (l'id della bozza).
Stile pop elettronico leggero: cassa in quattro, clap, charleston, basso, accordi pulsanti e un arpeggio.
"""
import hashlib
import wave
from pathlib import Path

import numpy as np

RATE = 44100
GIRI = [[0, 7, 9, 5], [9, 5, 0, 7], [0, 9, 5, 7], [5, 7, 9, 9], [0, 4, 9, 5]]   # I-V-vi-IV e simili, in semitoni
SCALA_MAGGIORE = [0, 2, 4, 5, 7, 9, 11]


def _nota(semitoni_da_la4: float) -> float:
    return 440.0 * 2 ** (semitoni_da_la4 / 12)


def _triade(radice: int) -> list[int]:
    """Accordo diatonico costruito sul grado della scala maggiore (radice in semitoni dalla tonica)."""
    grado = SCALA_MAGGIORE.index(radice % 12) if radice % 12 in SCALA_MAGGIORE else 0
    return [SCALA_MAGGIORE[(grado + i) % 7] + 12 * ((grado + i) // 7) for i in (0, 2, 4)]


def _onda(freq, n, tipo):
    t = np.arange(n) / RATE
    fase = (freq * t) % 1.0
    if tipo == "sega":
        return 2 * fase - 1
    if tipo == "quadra":
        return np.where(fase < 0.5, 1.0, -1.0)
    if tipo == "triangolo":
        return 4 * np.abs(fase - 0.5) - 1
    return np.sin(2 * np.pi * freq * t)


def _morbido(x, n):
    """Passa-basso semplice (media mobile, due volte): toglie l'asprezza alle onde quadre e a sega."""
    k = np.ones(n) / n
    return np.convolve(np.convolve(x, k, "same"), k, "same")


def _env(n, attacco=0.005, rilascio=0.2):
    t = np.arange(n) / RATE
    return np.minimum(1, t / attacco) * np.exp(-t / rilascio)


def genera(durata: float, seme: str) -> np.ndarray:
    rng = np.random.default_rng(int(hashlib.sha256(seme.encode()).hexdigest()[:8], 16))
    bpm = int(rng.integers(98, 122))
    tonica = int(rng.integers(-9, 3))                  # semitoni dal La4: tonalità tra Do e Do#
    giro = GIRI[rng.integers(len(GIRI))]
    suono_accordi = rng.choice(["sega", "quadra", "triangolo"])
    suono_arpeggio = rng.choice(["quadra", "triangolo", "seno"])
    schema_arp = rng.permutation([0, 1, 2, 1, 2, 0, 2, 1])[:8]
    sedicesimo = 60 / bpm / 4
    battuta = 16 * sedicesimo
    n_tot = int(durata * RATE) + RATE
    mix = np.zeros(n_tot, dtype=np.float64)

    def metti(segnale, inizio_s, volume):
        i = int(inizio_s * RATE)
        if i >= n_tot:
            return
        s = segnale[:n_tot - i]
        mix[i:i + s.size] += volume * s

    n16 = int(sedicesimo * RATE)
    cassa = np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-np.arange(n16 * 3) / RATE / 0.03)) / RATE) * _env(n16 * 3, 0.001, 0.12)
    rumore = rng.uniform(-1, 1, n16 * 2)
    clap = np.diff(rumore, prepend=0) * _env(n16 * 2, 0.001, 0.06)
    charleston = np.diff(np.diff(rumore[:n16], prepend=0), prepend=0) * _env(n16, 0.001, 0.02)

    battute = int(durata / battuta) + 1
    for b in range(battute):
        accordo = tonica + giro[b % 4]
        inizio = b * battuta
        intro = b == 0                                  # la prima battuta senza batteria: entra dopo
        for q in range(4):
            if not intro:
                metti(cassa, inizio + q * 4 * sedicesimo, 0.9)
                if q in (1, 3):
                    metti(clap, inizio + q * 4 * sedicesimo, 0.12)
            for h in (2,) if intro else (0, 2):
                metti(charleston, inizio + (q * 4 + h) * sedicesimo, 0.05 if h == 2 else 0.025)
        # Basso sugli ottavi, con la "pompa" che lascia spazio alla cassa.
        for o in range(8):
            n = int(2 * sedicesimo * RATE)
            nota = _morbido(_onda(_nota(accordo - 24), n, "sega"), 24) * _env(n, 0.003, 0.18)
            metti(nota, inizio + o * 2 * sedicesimo, 0.0 if intro else 0.32)
        # Accordi pulsanti sugli ottavi.
        for o in range(8):
            n = int(2 * sedicesimo * RATE * 0.9)
            voce = sum(_onda(_nota(tonica + iv + (giro[b % 4] - giro[b % 4] % 12)), n, suono_accordi) for iv in _triade(giro[b % 4]))
            metti(_morbido(voce, 10) * _env(n, 0.01, 0.25), inizio + o * 2 * sedicesimo, 0.07)
        # Arpeggio sui sedicesimi, un'ottava sopra, dalla terza battuta.
        if b >= 2:
            triade = _triade(giro[b % 4])
            for s in range(16):
                n = int(sedicesimo * RATE)
                nota = _onda(_nota(tonica + 12 + triade[schema_arp[s % 8]] + (giro[b % 4] - giro[b % 4] % 12)), n, suono_arpeggio)
                metti(_morbido(nota, 5) * _env(n, 0.002, 0.08), inizio + s * sedicesimo, 0.09)

    mix = mix[:int(durata * RATE)]
    sfuma = int(1.5 * RATE)
    mix[-sfuma:] *= np.linspace(1, 0, sfuma)
    mix[:int(0.05 * RATE)] *= np.linspace(0, 1, int(0.05 * RATE))
    mix = np.tanh(mix * 1.2)                            # limita i picchi in modo morbido
    return (mix / max(1e-6, np.abs(mix).max()) * 0.8).astype(np.float32)


def salva(audio: np.ndarray, percorso: Path):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(percorso), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
