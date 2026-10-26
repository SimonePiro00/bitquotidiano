"""Legge i risultati dei post pubblicati dalla pagina (Instagram Insights) per un periodo.

Serve il permesso instagram_manage_insights. Ogni metrica che l'API rifiuta viene saltata,
così un cambio di versione dell'API non blocca tutto il resto.
"""
import time
from datetime import datetime, timedelta, timezone

from .config import env
from .graph import GraphError, call

METRICHE_POST = ["reach", "views", "saved", "shares", "likes", "comments", "total_interactions", "follows", "profile_visits"]


def _insights(media_id: str) -> dict:
    out = {}
    try:
        data = call("GET", f"{media_id}/insights", metric=",".join(METRICHE_POST))["data"]
    except GraphError:
        # Una metrica non supportata fa fallire tutta la richiesta: riprova una alla volta.
        data = []
        for m in METRICHE_POST:
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
                     "titolo": (m.get("caption") or "").split("\n")[0][:90], **_insights(m["id"])})
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
