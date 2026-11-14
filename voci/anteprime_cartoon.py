"""Anteprime del Reel cartoon con voci diverse, in anteprime/cartoon/. Serve il secret GOOGLE_TTS_KEY. Non pubblica nulla."""
import importlib
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, ".")
OUT = Path("anteprime/cartoon")
OUT.mkdir(parents=True, exist_ok=True)

ICONE = {"cal-2026-11-15": ["qr", "carta", "telefono", "stop"],
         "cal-2026-11-12": ["chat", "avviso", "lucchetto", "chat"]}
# (bozza, nome file, stile grafico, voce, velocità): la velocità vale solo per Chirp 3 HD, Gemini segue l'indicazione di stile.
PROVE = [
    ("cal-2026-11-15", "1_palco_v4_achird", "palco", "google:it-IT-Chirp3-HD-Achird", "1.22"),
    ("cal-2026-11-15", "2_palco_gemini_achird", "palco", "gemini:Achird", "1"),
    ("cal-2026-11-15", "3_palco_gemini_puck", "palco", "gemini:Puck", "1"),
    ("cal-2026-11-15", "4_palco_gemini_fenrir", "palco", "gemini:Fenrir", "1"),
    ("cal-2026-11-15", "5_schede_gemini_achird", "schede", "gemini:Achird", "1"),
    ("cal-2026-11-12", "6_whatsapp_palco_gemini_achird", "palco", "gemini:Achird", "1"),
]
solo = os.environ.get("SOLO") or "1,2"   # es. "2,5" per rifare solo alcune prove
for bozza, nome, stile, voce_scelta, vel in PROVE:
    if solo and nome.split("_")[0] not in solo.split(","):
        continue
    os.environ["BIT_VOCE"], os.environ["BIT_VELOCITA"] = voce_scelta, vel
    from pipeline import voce, reel_cartoon
    importlib.reload(voce)
    importlib.reload(reel_cartoon)
    b = json.loads(Path(f"drafts/{bozza}/bozza.json").read_text())["bozza"]
    b["reel_icone"], b["reel_stile"] = ICONE[bozza], stile
    try:
        p = reel_cartoon.make_reel_cartoon(OUT, b, f"{nome}.mp4", seme=bozza)
        print("OK", p)
    except Exception:   # una voce che non va non deve fermare le altre
        print("ERRORE", nome)
        traceback.print_exc()
