"""Scarica testo e immagini di post Instagram indicati per link, tramite Business Discovery.

Business Discovery legge solo account Business/Creator pubblici e vuole lo username: il post
si ritrova scorrendo i media dell'account e confrontando lo shortcode del link.
"""
import json
import re

import requests

from .config import ROOT, env
from .graph import call
from .monitor import FIELDS

FONTI_DIR = ROOT / "fonti"


def shortcode(link: str) -> str:
    m = re.search(r"instagram\.com/(?:[^/]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", link)
    if not m:
        raise SystemExit(f"Link Instagram non riconosciuto: {link}")
    return m.group(1)


def trova(account: str, codici: set[str], max_pagine: int = 10) -> dict[str, dict]:
    ig_user_id = env("IG_USER_ID", required=True).strip()
    trovati, after = {}, ""
    for _ in range(max_pagine):
        pagina = f".after({after})" if after else ""
        fields = f"business_discovery.username({account}){{media{pagina}.limit(50){{{FIELDS}}}}}"
        media = call("GET", ig_user_id, fields=fields)["business_discovery"]["media"]
        for m in media["data"]:
            c = shortcode(m.get("permalink", "instagram.com/p/x/"))
            if c in codici:
                trovati[c] = m
        after = media.get("paging", {}).get("cursors", {}).get("after", "")
        if codici <= trovati.keys() or not after or "next" not in media.get("paging", {}):
            break
    return trovati


def salva(account: str, link: list[str]) -> None:
    codici = {shortcode(l) for l in link}
    trovati = trova(account, codici)
    for c, m in trovati.items():
        out = FONTI_DIR / c
        out.mkdir(parents=True, exist_ok=True)
        immagini = [x for x in m.get("children", {}).get("data", []) or [m]]
        for k, x in enumerate(immagini):
            if x.get("media_type") == "VIDEO" or not x.get("media_url"):
                continue
            r = requests.get(x["media_url"], timeout=60)
            if r.ok:
                (out / f"img_{k}.jpg").write_bytes(r.content)
        m.pop("media_url", None); m.pop("children", None)  # URL firmati e temporanei
        (out / "post.json").write_text(json.dumps({"account": account, **m}, ensure_ascii=False, indent=2))
        print(f"Salvato {c}: {len(list(out.glob('img_*.jpg')))} immagini")
    mancanti = codici - trovati.keys()
    if mancanti:
        raise SystemExit(f"Non trovati su @{account}: {', '.join(sorted(mancanti))}")
