"""Rileva i nuovi post della pagina sorgente tramite la Business Discovery API di Instagram.

Business Discovery è il modo ufficiale per leggere i post pubblici di un altro account
Business/Creator: niente scraping, quindi niente violazioni dei termini di Instagram.
"""
import json

import requests

from .config import STATE_FILE, env

FIELDS = "id,caption,media_type,media_url,permalink,timestamp,children{media_url,media_type}"


def fetch_recent_media(limit: int = 10) -> list[dict]:
    ig_user_id = env("IG_USER_ID", required=True)
    token = env("META_ACCESS_TOKEN", required=True)
    version = env("GRAPH_API_VERSION", "v26.0")
    source = env("SOURCE_USERNAME", "technologybrief")
    fields = f"business_discovery.username({source}){{media.limit({limit}){{{FIELDS}}}}}"
    resp = requests.get(
        f"https://graph.facebook.com/{version}/{ig_user_id}",
        params={"fields": fields, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["business_discovery"]["media"]["data"]


def load_seen() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(seen), indent=2))


def new_posts(media: list[dict], seen: set[str]) -> list[dict]:
    """Post non ancora visti, dal più vecchio al più recente."""
    fresh = [m for m in media if m["id"] not in seen]
    return sorted(fresh, key=lambda m: m["timestamp"])
