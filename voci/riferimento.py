"""Legge un Reel di riferimento (solo per studiarne lo stile): stampa didascalia e link temporanei al video.
Non salva né pubblica nulla."""
import sys
sys.path.insert(0, ".")
from pipeline.graph import call, GraphError
from pipeline.config import env

CODICE = "DfsSkvOo-fV"
CANDIDATI = ["cosadiconoidati", "cosa_dicono_i_dati", "cosadiconoi.dati", "cosa.dicono.i.dati", "cosadiconoidati_"]
ig = env("IG_USER_ID", required=True).strip()
for nome in CANDIDATI:
    try:
        after = ""
        for _ in range(15):
            pag = f".after({after})" if after else ""
            r = call("GET", ig, fields=f"business_discovery.username({nome}){{username,followers_count,media{pag}.limit(50){{id,caption,media_type,media_url,thumbnail_url,permalink,like_count,comments_count}}}}")
            bd = r["business_discovery"]
            media = bd["media"]
            for m in media["data"]:
                if CODICE in m.get("permalink", ""):
                    print("ACCOUNT", bd["username"], bd.get("followers_count"))
                    print("CAPTION", (m.get("caption") or "")[:1500].replace("\n", " | "))
                    print("LIKE", m.get("like_count"), "COMMENTI", m.get("comments_count"))
                    print("VIDEO_URL", m.get("media_url"))
                    print("THUMB_URL", m.get("thumbnail_url"))
                    # Foglio di fotogrammi a bassa risoluzione, stampato nel log (non viene salvato nel repo).
                    import base64, subprocess, requests
                    open("/tmp/r.mp4", "wb").write(requests.get(m["media_url"], timeout=120).content)
                    subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "/tmp/r.mp4"])
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "/tmp/r.mp4", "-t", "40", "-vf",
                                    "fps=0.6,scale=170:-1,tile=6x4", "-frames:v", "1", "-q:v", "9", "/tmp/f.jpg"], check=True)
                    b = base64.b64encode(open("/tmp/f.jpg", "rb").read()).decode()
                    print("FOGLIO_INIZIO")
                    for i in range(0, len(b), 4000):
                        print(b[i:i + 4000])
                    print("FOGLIO_FINE")
                    sys.exit(0)
            after = media.get("paging", {}).get("cursors", {}).get("after", "")
            if not after or "next" not in media.get("paging", {}):
                break
        print("Trovato account", nome, "ma non il Reel")
    except GraphError as e:
        print("No", nome, e)
