"""Legge i risultati dei post pubblicati dalla pagina (Instagram Insights) per un periodo.

Serve il permesso instagram_manage_insights. Ogni metrica che l'API rifiuta viene saltata,
così un cambio di versione dell'API non blocca tutto il resto.
"""
import csv
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

from .config import env
from .graph import GraphError, call

METRICHE_POST = ["reach", "views", "saved", "shares", "likes", "comments", "total_interactions", "follows", "profile_visits"]
# Solo per i Reel: tempo medio e totale di visione (in millisecondi).
METRICHE_REEL = ["reach", "views", "saved", "shares", "likes", "comments", "total_interactions",
                 "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


def _insights(media_id: str, reel: bool = False) -> dict:
    out = {}
    metriche = METRICHE_REEL if reel else METRICHE_POST
    try:
        data = call("GET", f"{media_id}/insights", metric=",".join(metriche))["data"]
    except GraphError:
        # Una metrica non supportata fa fallire tutta la richiesta: riprova una alla volta.
        data = []
        for m in metriche:
            try:
                data += call("GET", f"{media_id}/insights", metric=m)["data"]
            except GraphError as e:
                out.setdefault("errori", []).append(f"{m}: {e}")
    for d in data:
        vals = d.get("values") or [{}]
        out[d["name"]] = d.get("total_value", {}).get("value", vals[0].get("value"))
    return out


def analizza(dal: str, al: str) -> dict:
    ig = env("IG_USER_ID", required=True).strip()
    inizio = datetime.fromisoformat(dal).replace(tzinfo=timezone.utc)
    fine = datetime.fromisoformat(al).replace(tzinfo=timezone.utc) + timedelta(days=1)
    profilo = call("GET", ig, fields="username,followers_count,media_count")
    media = call("GET", f"{ig}/media", fields="id,caption,timestamp,media_type,permalink,like_count,comments_count", limit=50)["data"]
    post = []
    for m in media:
        quando = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if not inizio <= quando < fine:
            continue
        post.append({"id": m["id"], "data": m["timestamp"], "tipo": m["media_type"], "link": m.get("permalink"),
                     "titolo": (m.get("caption") or "").split("\n")[0][:90], **_insights(m["id"], reel=m.get("media_type") == "VIDEO")})
        time.sleep(1)
    account = {}
    for metrica, extra in [("reach", {"period": "day", "metric_type": "total_value"}),
                           ("follows_and_unfollows", {"period": "day", "metric_type": "total_value"}),
                           ("profile_views", {"period": "day", "metric_type": "total_value"})]:
        try:
            d = call("GET", f"{ig}/insights", metric=metrica, since=int(inizio.timestamp()), until=int(fine.timestamp()), **extra)["data"]
            account[metrica] = d[0].get("total_value") if d else None
        except GraphError as e:
            account[metrica] = f"errore: {e}"
    return {"periodo": [dal, al], "profilo": profilo, "account": account, "post": sorted(post, key=lambda p: p["data"])}


def registro_giornaliero(cartella: Path = Path("analisi")) -> str:
    """Aggiunge una riga per giorno a follower.csv e una riga per ogni Reel degli ultimi 30 giorni
    a reel_giornaliero.csv. Il tempo medio è in secondi. Se il giorno c'è già, lo sostituisce."""
    ig = env("IG_USER_ID", required=True).strip()
    oggi = datetime.now(timezone.utc).date().isoformat()
    cartella.mkdir(exist_ok=True)
    profilo = call("GET", ig, fields="followers_count,media_count")
    _scrivi(cartella / "follower.csv", ["data", "follower", "post"], oggi,
            [[oggi, profilo.get("followers_count"), profilo.get("media_count")]])
    limite = datetime.now(timezone.utc) - timedelta(days=30)
    media = call("GET", f"{ig}/media", fields="id,caption,timestamp,media_type,permalink", limit=50)["data"]
    righe = []
    for m in media:
        quando = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if m.get("media_type") != "VIDEO" or quando < limite:
            continue
        ins = _insights(m["id"], reel=True)
        media_ms = ins.get("ig_reels_avg_watch_time")
        righe.append([oggi, m["id"], m["timestamp"][:10], (m.get("caption") or "").split("\n")[0][:60],
                      ins.get("views"), ins.get("reach"), round(media_ms / 1000, 1) if media_ms else "",
                      ins.get("shares"), ins.get("likes"), ins.get("comments"), ins.get("saved"), m.get("permalink")])
        time.sleep(1)
    _scrivi(cartella / "reel_giornaliero.csv",
            ["data", "reel_id", "pubblicato", "titolo", "views", "reach", "tempo_medio_s", "invii", "like", "commenti",
             "salvataggi", "link"], oggi, righe)
    return f"{oggi}: {profilo.get('followers_count')} follower, {len(righe)} Reel registrati"


def _scrivi(file: Path, intestazione: list, oggi: str, righe: list):
    vecchie = []
    if file.exists():
        with file.open(newline="") as f:
            vecchie = [r for r in csv.reader(f)][1:]
    vecchie = [r for r in vecchie if r and r[0] != oggi]
    with file.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(intestazione)
        w.writerows(vecchie + righe)
