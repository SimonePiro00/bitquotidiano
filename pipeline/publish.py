"""Pubblica un carosello tramite la Content Publishing API di Instagram (Graph API).

Le immagini devono essere raggiungibili da un URL pubblico: Instagram le scarica da lì.
"""
import time
from datetime import datetime

from .config import env
from .graph import GraphError, call


def _post(path: str, **params) -> dict:
    return call("POST", path, **params)


def _gia_uscito(ig: str, edge: str, inizio: float, caption: str | None) -> str | None:
    """Cerca tra gli ultimi media dell'account uno pubblicato dopo `inizio` (e con la stessa
    didascalia, se data). Serve perché media_publish può dare errore anche quando il post è uscito."""
    time.sleep(15)
    recenti = call("GET", f"{ig}/{edge}", fields="id,caption,timestamp", limit=5).get("data", [])
    for m in recenti:
        quando = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp()
        if quando >= inizio - 60 and (caption is None or m.get("caption", "").strip()[:80] == caption.strip()[:80]):
            return m["id"]
    return None


def _publish(ig: str, container: str, edge: str, caption: str | None = None, attempts: int = 6) -> str:
    """media_publish a volte risponde #9007 "Media ID is not available" anche con il container
    FINISHED: Instagram non ha ancora finito di elaborarlo, basta riprovare poco dopo.
    Con altri errori (per esempio #4, limite di richieste) il post a volte esce lo stesso: prima di
    fallire controlla se è già sul profilo, così rilanciare il workflow non crea doppioni."""
    inizio = time.time()
    for i in range(attempts):
        try:
            return _post(f"{ig}/media_publish", creation_id=container)["id"]
        except GraphError as e:
            if "#9007" not in str(e) or i == attempts - 1:
                try:
                    trovato = _gia_uscito(ig, edge, inizio, caption)
                except GraphError:
                    trovato = None
                if trovato:
                    print(f"media_publish ha risposto {e}, ma il contenuto risulta pubblicato: {trovato}")
                    return trovato
                raise
            time.sleep(10)


def _wait_ready(container_id: str, attempts: int = 20) -> None:
    for _ in range(attempts):
        status = call("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} in errore")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} non pronto")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    ig = env("IG_USER_ID", required=True).strip()
    if len(image_urls) == 1:
        container = _post(f"{ig}/media", image_url=image_urls[0], caption=caption)["id"]
    else:
        children = [_post(f"{ig}/media", image_url=u, is_carousel_item="true")["id"] for u in image_urls]
        for c in children:
            _wait_ready(c)
        container = _post(f"{ig}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    _wait_ready(container)
    return _publish(ig, container, "media", caption)


def publish_story(image_url: str) -> str:
    """Pubblica una storia con un'immagine. L'API non permette di "ricondividere" un post con lo
    sticker nativo, quindi la storia è un'immagine nostra che rimanda al post."""
    ig = env("IG_USER_ID", required=True).strip()
    container = _post(f"{ig}/media", image_url=image_url, media_type="STORIES")["id"]
    _wait_ready(container)
    return _publish(ig, container, "stories")


def publish_reel(video_url: str, caption: str) -> str:
    """Pubblica un Reel solo nella sezione Reel (share_to_feed=false), per non doppiare il carosello
    nella griglia. I video richiedono più tempo di elaborazione delle immagini."""
    ig = env("IG_USER_ID", required=True).strip()
    container = _post(f"{ig}/media", media_type="REELS", video_url=video_url, caption=caption, share_to_feed="false")["id"]
    _wait_ready(container, attempts=72)
    return _publish(ig, container, "media", caption)
