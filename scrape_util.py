from typing import Optional

from pathlib import Path
import requests
from urllib import parse
import json

from tqdm import tqdm
from pydantic import BaseModel

import utils
from danbooru_post import DanbooruPost
from scrape_config import (
    AVAIABLE_DOMAINS,
    ScrapeConfig,
    ScrapeSubset,
    CaptionConfig,
    SearchResultFilterConfig,
    AuthConfig,
    CATEGORY_ORDER_STYLE,
)

from default_tags import KAOMOJI_TAGS_FILE, PERSON_TAGS_FILE

KAOMOJI_TAGS = utils.load_file_lines(KAOMOJI_TAGS_FILE)
PERSON_TAGS = utils.load_file_lines(PERSON_TAGS_FILE)


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


# 人物タグとそうじゃないタグに分離する
def separate_person_tags(tags: list[str]):
    person_tags = []
    not_person_tags = []
    for tag in tags:
        if tag in PERSON_TAGS:
            person_tags.append(tag)
        else:
            not_person_tags.append(tag)
    return person_tags, not_person_tags


class DanbooruScraper:
    domain: AVAIABLE_DOMAINS
    auth: Optional[AuthConfig]

    def __init__(
        self,
        domain: AVAIABLE_DOMAINS = "danbooru.donmai.us",
        auth: Optional[AuthConfig] = None,
    ) -> None:
        self.domain = domain
        self.auth = auth

    def _get_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "Danbooru Scraper"}
        if self.auth is not None:
            headers["Authorization"] = f"Basic {self.auth.basic_auth()}"
        return headers

    def get_posts(
        self, query: str, page: int = 1, limit_per_page: int = 20
    ) -> list[DanbooruPost]:
        url = f"https://{self.domain}/posts.json?tags={parse.quote(query)}&page={page}&limit={limit_per_page}"
        headers = self._get_headers()

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception("Error: " + str(response.status_code) + " " + response.text)

        posts = [DanbooruPost(**post) for post in json.loads(response.text)]

        return posts

    def get_post(self, post_id: int) -> DanbooruPost:
        url = f"https://{self.domain}/posts/{post_id}.json"
        headers = self._get_headers()

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception("Error: " + str(response.status_code) + " " + response.text)

        post = DanbooruPost(**json.loads(response.text))

        return post


class DanbooruPostItem(BaseModel):
    post: DanbooruPost

    artist_tags: list[str] = []
    character_tags: list[str] = []
    copyright_tags: list[str] = []
    general_tags: list[str] = []
    meta_tags: list[str] = []

    quality_tags: list[str] = []

    rating_tags: list[str] = []

    @staticmethod
    def new(post: DanbooruPost):
        return DanbooruPostItem(
            post=post,
            artist_tags=parse_other_tags(post.tag_string_artist),
            character_tags=parse_other_tags(post.tag_string_character),
            copyright_tags=parse_other_tags(post.tag_string_copyright),
            general_tags=parse_general_tags(post.tag_string_general),
            meta_tags=parse_other_tags(post.tag_string_meta),
        )

    def _compose_tags_wd_style(
        self,
        category_separator: str = ", ",
    ):
        return category_separator.join(
            [
                category
                for category in (
                    ", ".join([tag for tag in tags if tag.strip() != ""])
                    for tags in [
                        self.rating_tags,
                        self.quality_tags,
                        self.artist_tags,
                        self.character_tags,
                        self.general_tags,
                        self.meta_tags,
                    ]
                )
                if category.strip() != ""
            ]
        )

    def _compose_tags_nai_style(
        self,
        category_separator: str = ", ",
    ):
        person_tags, other_tags = separate_person_tags(self.general_tags)
        return category_separator.join(
            [
                category
                for category in (
                    ", ".join([tag for tag in tags if tag.strip() != ""])
                    for tags in [
                        person_tags,
                        self.artist_tags,
                        self.character_tags,
                        self.copyright_tags,
                        other_tags,
                        self.meta_tags,
                        self.quality_tags,
                        self.rating_tags,
                    ]
                )
                if category.strip() != ""
            ]
        )

    def _compose_tags_animaginexl_style(
        self,
        category_separator: str = ", ",
    ):
        person_tags, other_tags = separate_person_tags(self.general_tags)
        return category_separator.join(
            [
                category
                for category in (
                    ", ".join([tag for tag in tags if tag.strip() != ""])
                    for tags in [
                        person_tags,
                        self.character_tags,
                        self.copyright_tags,
                        other_tags,
                        self.meta_tags,
                        self.quality_tags,
                        self.rating_tags,
                    ]
                )
                if category.strip() != ""
            ]
        )

    def compose_tags(
        self,
        category_separator: str = ", ",
        category_order: CATEGORY_ORDER_STYLE | None = None,
    ) -> str:
        if category_order is None or category_order == "wd":
            return self._compose_tags_wd_style(category_separator)
        elif category_order == "naidv3":
            return self._compose_tags_nai_style(category_separator)
        elif category_order == "animaginexlv3":
            return self._compose_tags_animaginexl_style(category_separator)


class ScrapeResultCache:
    output_path: str
    save_state_path: Optional[str] = None
    caption: CaptionConfig | None = None

    items: list[DanbooruPostItem]

    def __init__(self, items: list[DanbooruPostItem], subset: ScrapeSubset) -> None:
        self.items = items
        self.output_path = subset.output_path
        self.save_state_path = subset.save_state_path
        self.caption = subset.caption


def get_posts(
    scraper: DanbooruScraper,
    query: str,
    search_result_filter: SearchResultFilterConfig | None,
    fallback_search_result_filter: SearchResultFilterConfig,
    total_limit: int = 100,
    limit_per_page: int = 200,
) -> list[DanbooruPostItem]:
    posts: list[DanbooruPostItem] = []
    page = 1
    limit_per_page = 200

    result_filter = (
        search_result_filter
        if search_result_filter is not None
        else fallback_search_result_filter
    )

    with tqdm(total=total_limit) as pbar:
        while len(posts) < total_limit:
            new_posts = [
                DanbooruPostItem.new(post)
                for post in scraper.get_posts(query, page, limit_per_page)
                if post.md5 is not None
            ]

            if len(new_posts) == 0:
                break

            for post in new_posts:
                all_tags = [
                    *post.artist_tags,
                    *post.copyright_tags,
                    *post.character_tags,
                    *post.general_tags,
                    *post.meta_tags,
                ]

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
    url: str,
    output_dir: str | Path,
    filename: str,
    extension: str,
    headers: dict[str, str],
) -> None:
    output_path = Path(output_dir) / f"{filename}.{extension}"

    if output_path.exists():
        return

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Error: " + str(response.status_code))

    with open(output_path, "wb") as f:
        f.write(response.content)


def download_post_images(
    items: list[DanbooruPostItem],
    caches: list[ScrapeResultCache],
    auth: Optional[AuthConfig],
    pbar,
) -> None:
    for item, cache in zip(items, caches):
        output_dir = cache.output_path

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        if item.post.file_url is None:
            print(f"file_url is None! (skipped: ID {item.post.id})")
            pbar.update(1)
            return

        download_image(
            item.post.file_url,
            output_dir,
            str(item.post.id),
            item.post.file_ext,
            {
                "User-Agent": "Danbooru Scraper",
                "Authorization": f"Basic {auth.basic_auth()}"
                if auth is not None
                else "",
            },
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
        caption_config = (
            cache.caption if cache.caption is not None else fallback_caption_config
        )

        output_dir = cache.output_path

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        save_caption(
            item.compose_tags(
                caption_config.category_separator, caption_config.category_order
            ),
            output_dir,
            str(item.post.id),
            caption_config.extension,
            caption_config.overwrite,
        )


def save_from_cache(
    chunk: list[DanbooruPostItem],
    caches: list[ScrapeResultCache],
    config: ScrapeConfig,
    pbar,
) -> None:
    save_post_captions(chunk, caches, config.caption)

    download_post_images(chunk, caches, config.auth, pbar)
