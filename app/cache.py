import json
import os

CACHE_FILE = "ingested_urls.json"


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def is_url_ingested(url: str) -> bool:
    cache = _load_cache()
    return url in cache


def save_ingested_url(url: str, meta: dict = None):
    cache = _load_cache()
    cache[url] = meta or {}
    _save_cache(cache)


def remove_ingested_url(url: str):
    cache = _load_cache()
    if url in cache:
        del cache[url]
        _save_cache(cache)


def get_all_ingested_urls() -> list[dict]:
    cache = _load_cache()
    return [{"url": k, **v} for k, v in cache.items()]


def clear_cache():
    _save_cache({})
