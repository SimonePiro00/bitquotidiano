#!/usr/bin/env bash
# Campioni di voci italiane più naturali per i Reel lampo (workflow "Campioni voce 2"): stessa frase per tutte.
set -e
mkdir -p voci/campioni2
FRASE="Il tuo pacco è in giacenza? Non cliccare quel link. Ecco tre segnali, e il terzo è quello che frega tutti. Uno: il link non è del corriere. Due: ti chiede pochi euro. Tre: ti mette fretta, entro ventiquattro ore. Mandalo a chi aspetta sempre un pacco, e segui per la prossima!"
# Piper, voce femminile "paola" (licenza libera), un po' più svelta.
BIT_VOCE=paola BIT_VELOCITA=1.1 python -c "
import sys; from pathlib import Path; from pipeline import voce
voce.salva(voce.parla(sys.argv[1]), Path('voci/campioni2/tmp.wav'))" "$FRASE"
ffmpeg -loglevel error -y -i voci/campioni2/tmp.wav -b:a 128k voci/campioni2/1_paola.mp3
# Kokoro (licenza Apache 2.0): voci italiane "sara" e "nicola", più espressive.
python - "$FRASE" <<'PY'
import sys, numpy as np, soundfile as sf
from kokoro import KPipeline
p = KPipeline(lang_code="i")
for nome, v in [("2_sara", "if_sara"), ("3_nicola", "im_nicola")]:
    audio = np.concatenate([np.asarray(a) for _, _, a in p(sys.argv[1], voice=v, speed=1.1)])
    sf.write(f"voci/campioni2/{nome}.wav", audio, 24000)
PY
for n in 2_sara 3_nicola; do ffmpeg -loglevel error -y -i voci/campioni2/$n.wav -b:a 128k voci/campioni2/$n.mp3; rm voci/campioni2/$n.wav; done
rm -f voci/campioni2/tmp.wav
