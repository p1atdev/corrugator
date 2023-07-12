from typing import Optional

from pathlib import Path
import requests
from urllib import parse
import json


from danbooru_post import DanbooruPost
from scrape_config import AVAIABLE_DOMAINS, ScrapeSubset, CaptionConfig

from default_tags import DEFAULT_EXLUSION_META_TAGS, KAOMOJI_TAGS


# _ ありの空白区切りから _ なしの配列にする
def parse_general_tags(tag_text: str) -> list[str]:
    tags = tag_text.split(" ")
    for i, tag in enumerate(tags):
        if not tag in KAOMOJI_TAGS:
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
            [
                *self.artist_tags,
                *self.character_tags,
                *self.general_tags,
                *self.meta_tags,
            ]
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
    exclusion_general_tags: list[str] = [],
    exclusion_meta_tags: list[str] = DEFAULT_EXLUSION_META_TAGS,
    total_limit: int = 100,
    limit_per_page: int = 200,
) -> list[DanbooruPostItem]:
    posts: list[DanbooruPostItem] = []
    page = 1
    limit_per_page = 200

    while len(posts) < total_limit:
        new_posts = [
            DanbooruPostItem(post)
            for post in scraper.get_posts(query, page, limit_per_page)
            if post.md5 is not None
        ]
        new_posts = [
            post
            for post in new_posts
            if not any(tag in exclusion_general_tags for tag in post.general_tags)
            and not any(tag in exclusion_meta_tags for tag in post.meta_tags)
        ]
        posts += new_posts
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
    pbar,
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
        pbar.update(1)


def process_post_cache(
    chunk: list[DanbooruPostItem],
    caches: list[ScrapeResultCache],
    fallback_caption_config: CaptionConfig,
    pbar,
) -> None:
    save_post_captions(chunk, caches, fallback_caption_config, pbar)

    download_post_images(chunk, caches, pbar)


def load_query_list_file(file: str | Path) -> list[str]:
    with open(file, "r", encoding="utf-8") as f:
        return [
            line.strip().replace(" ", "_")
            for line in f.readlines()
            if line.strip() != ""
        ]


def load_url_list_file(file: str | Path) -> list[str]:
    with open(file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip() != ""]
