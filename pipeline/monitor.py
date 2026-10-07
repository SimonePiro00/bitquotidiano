"""Rileva i nuovi post della pagina sorgente tramite la Business Discovery API di Instagram.

Business Discovery è il modo ufficiale per leggere i post pubblici di un altro account
Business/Creator: niente scraping, quindi niente violazioni dei termini di Instagram.
"""
import json

from .config import STATE_FILE, env
from .graph import call

FIELDS = "id,caption,media_type,media_url,permalink,timestamp,children{media_url,media_type}"


def fetch_recent_media(limit: int = 10) -> list[dict]:
    ig_user_id = env("IG_USER_ID", required=True).strip()
    source = env("SOURCE_USERNAME", "technologybrief")
    fields = f"business_discovery.username({source}){{media.limit({limit}){{{FIELDS}}}}}"
    return call("GET", ig_user_id, fields=fields)["business_discovery"]["media"]["data"]


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
