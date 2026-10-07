"""Pubblica un carosello tramite la Content Publishing API di Instagram (Graph API).

Le immagini devono essere raggiungibili da un URL pubblico: Instagram le scarica da lì.
"""
import time

import requests

from .config import env


def _post(path: str, **params) -> dict:
    version = env("GRAPH_API_VERSION", "v26.0")
    params["access_token"] = env("META_ACCESS_TOKEN", required=True)
    resp = requests.post(f"https://graph.facebook.com/{version}/{path}", data=params, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"Graph API {path}: {resp.status_code} {resp.text}")
    return resp.json()


def _wait_ready(container_id: str, attempts: int = 20) -> None:
    version = env("GRAPH_API_VERSION", "v26.0")
    token = env("META_ACCESS_TOKEN", required=True)
    for _ in range(attempts):
        r = requests.get(
            f"https://graph.facebook.com/{version}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if r.get("status_code") == "FINISHED":
            return
        if r.get("status_code") == "ERROR":
            raise RuntimeError(f"Container {container_id} in errore: {r}")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} non pronto")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    ig = env("IG_USER_ID", required=True)
    if len(image_urls) == 1:
        container = _post(f"{ig}/media", image_url=image_urls[0], caption=caption)["id"]
    else:
        children = [_post(f"{ig}/media", image_url=u, is_carousel_item="true")["id"] for u in image_urls]
        for c in children:
            _wait_ready(c)
        container = _post(f"{ig}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    _wait_ready(container)
    return _post(f"{ig}/media_publish", creation_id=container)["id"]
