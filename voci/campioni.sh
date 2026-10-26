#!/usr/bin/env bash
# Crea i campioni delle voci di Bit in voci/campioni/ (lanciato dal workflow "Campioni voce").
set -e
mkdir -p voci/campioni
FRASE="Ciao, sono Bit! Oggi ti spiego come riconoscere la truffa del finto operatore della banca. Primo segnale: l'urgenza. Ti dicono che tra dieci minuti i soldi spariscono."
while read -r nome voce tono velocita; do
  [ -z "$nome" ] && continue
  BIT_VOCE=$voce BIT_TONO=$tono BIT_VELOCITA=$velocita python -c "
import sys; from pathlib import Path; from pipeline import voce
voce.salva(voce.parla(sys.argv[1]), Path('voci/campioni/tmp.wav'))" "$FRASE"
  ffmpeg -loglevel error -y -i voci/campioni/tmp.wav -b:a 128k "voci/campioni/$nome.mp3"
done <<'LISTA'
1_paola_naturale paola 1.0 0.95
2_paola_lenta paola 1.0 0.85
3_paola_vocina paola 1.15 0.85
4_riccardo_naturale riccardo 1.0 0.92
5_riccardo_vocina riccardo 1.15 0.85
LISTA
rm -f voci/campioni/tmp.wav
