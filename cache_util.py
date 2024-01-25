from pathlib import Path
from hashlib import sha256
import json

from scrape_util import DanbooruPostItem


def _calc_query_hash(search_query: str) -> str:
    return sha256(search_query.encode("utf-8")).hexdigest()[:16]


def load_cache(directory: str | Path, hash: str, tmp_dirname: str = "cache"):
    if isinstance(directory, str):
        directory = Path(directory)

    tmp_dir = directory / tmp_dirname

    if not tmp_dir.exists():
        return None

    cache_file = tmp_dir / f"{hash}.json"

    if not cache_file.exists():
        return None

    with open(cache_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(directory: str | Path, hash: str, data, tmp_dirname: str = "cache"):
    if isinstance(directory, str):
        directory = Path(directory)

    tmp_dir = directory / tmp_dirname

    if not tmp_dir.exists():
        tmp_dir.mkdir(parents=True)

    cache_file = tmp_dir / f"{hash}.json"

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_search_cache(
    directory: str | Path, search_query: str, tmp_dirname: str = "cache"
) -> list[DanbooruPostItem] | None:
    if isinstance(directory, str):
        directory = Path(directory)

    query_hash = _calc_query_hash(search_query)

    result = load_cache(
        directory,
        query_hash,
        tmp_dirname=tmp_dirname,
    )

    if result is None:
        return None

    return [DanbooruPostItem(**item) for item in result]


def save_search_cache(
    directory: str | Path,
    search_query: str,
    items: list[DanbooruPostItem],
    tmp_dirname: str = "cache",
):
    if isinstance(directory, str):
        directory = Path(directory)

    query_hash = _calc_query_hash(search_query)

    save_cache(
        directory,
        query_hash,
        [item.dict() for item in items],
        tmp_dirname=tmp_dirname,
    )
