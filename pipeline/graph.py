"""Chiamate alla Graph API di Meta.

Il token viaggia nell'header Authorization e mai nell'URL: così non può finire nei log
(gli errori di requests stampano l'URL completo della richiesta).
"""
import requests

from .config import env


class GraphError(RuntimeError):
    pass


def _token() -> str:
    token = env("META_ACCESS_TOKEN", required=True).strip()
    if not token.startswith("EA") or any(c.isspace() for c in token):
        raise SystemExit("META_ACCESS_TOKEN non sembra un token valido: deve iniziare con 'EA' e non contenere spazi.")
    return token


def call(method: str, path: str, **params) -> dict:
    version = env("GRAPH_API_VERSION", "v26.0")
    url = f"https://graph.facebook.com/{version}/{path}"
    headers = {"Authorization": f"Bearer {_token()}"}
    if method == "GET":
        resp = requests.get(url, params=params, headers=headers, timeout=60)
    else:
        resp = requests.post(url, data=params, headers=headers, timeout=60)
    if not resp.ok:
        try:
            err = resp.json().get("error", {})
            detail = f"{err.get('type')} (#{err.get('code')}): {err.get('message')}"
        except ValueError:
            detail = resp.text[:300]
        raise GraphError(f"Graph API {method} {path.split('/')[-1] or path} -> {resp.status_code}: {detail}")
    return resp.json()
