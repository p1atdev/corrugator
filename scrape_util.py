from typing import Optional

from pathlib import Path
import requests
from urllib import parse
import json

from tqdm import tqdm

import utils
from danbooru_post import DanbooruPost
from scrape_config import (
    AVAIABLE_DOMAINS,
    ScrapeSubset,
    CaptionConfig,
    SearchResultFilterConfig,
)

from default_tags import EXCLUSION_TAGS_FILE, KAOMOJI_TAGS_FILE


# _ ありの空白区切りから _ なしの配列にする
def parse_general_tags(tag_text: str) -> list[str]:
    tags = tag_text.split(" ")
    for i, tag in enumerate(tags):
        if not tag in utils.load_file_lines(EXCLUSION_TAGS_FILE):
            tags[i] = tag.replace("_", " ")
    return tags


def parse_other_tags(tag_text: str) -> list[str]:
    tags = tag_text.split(" ")
    for i, tag in enumerate(tags):
        tags[i] = tag.replace("_", " ")
    return tags


class DanbooruScraper:
    domain: AVAIABLE_DOMAINS

    def __init__(self, domain: AVAIABLE_DOMAINS = "danbooru.donmai.us") -> None:
        self.domain = domain

    def get_posts(
        self, query: str, page: int = 1, limit_per_page: int = 20
    ) -> list[DanbooruPost]:
        url = f"https://{self.domain}/posts.json?tags={parse.quote(query)}&page={page}&limit={limit_per_page}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Error: " + str(response.status_code))

        posts = [DanbooruPost(**post) for post in json.loads(response.text)]

        return posts

    def get_post(self, post_id: int) -> DanbooruPost:
        url = f"https://{self.domain}/posts/{post_id}.json"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Error: " + str(response.status_code))

        post = DanbooruPost(**json.loads(response.text))

        return post


class DanbooruPostItem:
    post: DanbooruPost

    artist_tags: list[str]
    character_tags: list[str]
    copyright_tags: list[str]
    general_tags: list[str]
    meta_tags: list[str]

    rating_tags: list[str] = []

    large_file_url: str

    def __init__(self, post: DanbooruPost):
        self.post = post

        self.artist_tags = parse_other_tags(post.tag_string_artist)
        self.character_tags = parse_other_tags(post.tag_string_character)
        self.copyright_tags = parse_other_tags(post.tag_string_copyright)
        self.general_tags = parse_general_tags(post.tag_string_general)
        self.meta_tags = parse_other_tags(post.tag_string_meta)

        self.large_file_url = post.large_file_url

    def compose_tags(self) -> str:
        return ", ".join(
            tag
            for tag in [
                *self.artist_tags,
                *self.character_tags,
                *self.general_tags,
                *self.meta_tags,
            ]
            if tag.strip() != ""
        )


class ScrapeResultCache:
    output_path: str
    save_state_path: Optional[str] = None
    caption: Optional[bool | CaptionConfig] = False

    items: list[DanbooruPostItem]

    def __init__(self, items: list[DanbooruPostItem], subset: ScrapeSubset) -> None:
        self.items = items
        self.output_path = subset.output_path
        self.save_state_path = subset.save_state_path
        self.caption = subset.caption


def get_posts(
    scraper: DanbooruScraper,
    query: str,
    search_result_filter: Optional[bool | SearchResultFilterConfig],
    fallback_search_result_filter: SearchResultFilterConfig,
    total_limit: int = 100,
    limit_per_page: int = 200,
) -> list[DanbooruPostItem]:
    posts: list[DanbooruPostItem] = []
    page = 1
    limit_per_page = 200

    result_filter = fallback_search_result_filter
    if search_result_filter is not None:
        if isinstance(search_result_filter, bool):
            if search_result_filter:
                pass  # デフォルト値
            else:
                result_filter = None
        else:
            result_filter = search_result_filter

    with tqdm(total=total_limit) as pbar:
        while len(posts) < total_limit:
            new_posts = [
                DanbooruPostItem(post)
                for post in scraper.get_posts(query, page, limit_per_page)
                if post.md5 is not None
            ]

            if len(new_posts) == 0:
                break

            for post in new_posts:
                all_tags = (
                    post.artist_tags
                    + post.character_tags
                    + post.copyright_tags
                    + post.general_tags
                    + post.meta_tags
                )

                if result_filter.include_any != [] and all(
                    tag not in result_filter.include_any for tag in all_tags
                ):
                    continue  # どれも入っていなかったら
                if result_filter.include_all != [] and any(
                    tag not in result_filter.include_all for tag in all_tags
                ):
                    continue  # ひとつでも入っていなかったら
                if result_filter.exclude_any != [] and any(
                    tag in result_filter.exclude_any for tag in all_tags
                ):
                    continue  # どれか入っていたら
                if result_filter.exclude_all != [] and all(
                    tag in result_filter.exclude_all for tag in all_tags
                ):
                    continue  # 全部入っていたら

                # OKなら追加
                posts.append(post)

                pbar.update(1)

            page += 1

    return posts[:total_limit]


def get_domain_and_post_id_from_url(url: str) -> tuple[AVAIABLE_DOMAINS, int]:
    parsed = parse.urlparse(url)
    if parsed.scheme != "https":
        raise Exception("Invalid url: " + url)

    domain = parsed.netloc

    if domain == "danbooru.donmai.us" or domain == "safebooru.donmai.us":
        post_id = int(parsed.path.split("/")[-1])
        return domain, post_id
    else:
        raise Exception("Invalid url: " + url)


def download_image(
    url: str, output_dir: str | Path, filename: str, extension: str
) -> None:
    output_path = Path(output_dir) / f"{filename}.{extension}"

    if output_path.exists():
        return

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Error: " + str(response.status_code))

    with open(output_path, "wb") as f:
        f.write(response.content)


def download_post_images(
    items: list[DanbooruPostItem],
    caches: list[ScrapeResultCache],
    pbar,
) -> None:
    for item, cache in zip(items, caches):
        output_dir = cache.output_path

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        download_image(
            item.large_file_url, output_dir, item.post.id, item.post.file_ext
        )
        pbar.update(1)


def save_caption(
    caption: str, output_dir: str | Path, filename: str, extension: str, overwrite: bool
) -> None:
    output_path = Path(output_dir) / f"{filename}.{extension}"

    if output_path.exists() and not overwrite:
        return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(caption)


def save_post_captions(
    items: list[DanbooruPostItem],
    caches: list[ScrapeResultCache],
    fallback_caption_config: CaptionConfig,
) -> None:
    for item, cache in zip(items, caches):
        if isinstance(cache.caption, bool):
            if not cache.caption:
                continue  # キャプションを保存しない
            else:
                cache.caption = CaptionConfig()  # デフォルト値

        config = fallback_caption_config if cache.caption is None else cache.caption

        output_dir = cache.output_path

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        save_caption(
            item.compose_tags(),
            output_dir,
            item.post.id,
            config.extension,
            config.overwrite,
        )


def save_from_cache(
    chunk: list[DanbooruPostItem],
    caches: list[ScrapeResultCache],
    fallback_caption_config: CaptionConfig,
    pbar,
) -> None:
    save_post_captions(chunk, caches, fallback_caption_config)

    download_post_images(chunk, caches, pbar)
