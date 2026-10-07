"""Pubblica un carosello tramite la Content Publishing API di Instagram (Graph API).

Le immagini devono essere raggiungibili da un URL pubblico: Instagram le scarica da lì.
"""
import time

from .config import env
from .graph import call


def _post(path: str, **params) -> dict:
    return call("POST", path, **params)


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
    return _post(f"{ig}/media_publish", creation_id=container)["id"]
