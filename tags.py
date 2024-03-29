from typing import Literal

import os

import utils

from danbooru_post import Rating
from scrape_util import DanbooruPostItem

from scrape_config import (
    CaptionPostProcessConfig,
    RatingTagConfig,
    CaptionConfig,
    QualityTagConfig,
    FILETYPE,
)

INSERT_POSITION = Literal["start", "end"]

DEFAULT_FILETYPES: list[FILETYPE] = ["jpg", "png", "webp", "avif"]


def normalize_tags(tags: str | list[str]) -> list[str]:
    if isinstance(tags, str):
        if os.path.isfile(tags):
            return utils.load_file_lines(tags)
        else:
            return [tags]
    else:
        return tags


def is_nsfw(
    tags: list[str],
    nsfw_tags: str | list[str] | None,
) -> bool:
    if nsfw_tags is None:
        return False
    return any(tag in normalize_tags(nsfw_tags) for tag in tags)


def process_replace(
    original: list[str], _from: str | list[str] | None, to: str
) -> list[str]:
    if _from is None:
        return original

    for i, tag in enumerate(original):
        for f in normalize_tags(_from):
            if tag == f:
                original[i] = to
                break

    return original


def process_keep(original: list[str], keep: str | list[str] | None) -> list[str]:
    if keep is None:
        return original

    new_tags = []

    for tag in original:
        if tag in normalize_tags(keep):
            new_tags.append(tag)

    return new_tags


def process_delete(original: list[str], delete: str | list[str] | None) -> list[str]:
    if delete is None:
        return original

    new_tags = []

    for tag in original:
        if tag not in normalize_tags(delete):
            new_tags.append(tag)

    return new_tags


def process_insert(
    original: list[str], insert: str | list[str] | None, position: INSERT_POSITION
) -> list[str]:
    if insert is None:
        return original

    insert = normalize_tags(insert)

    if position == "start":
        return insert + original
    elif position == "end":
        return original + insert
    else:
        raise Exception("Invalid position: " + position)


def do_caption_post_process(
    original: list[str], config: CaptionPostProcessConfig | bool
) -> list[str]:
    tags = original

    if isinstance(config, bool):
        if config:
            return tags
        else:
            return []

    for replace in config.replaces:
        tags = process_replace(tags, replace.tags, replace.to)

    for keep in config.keeps:
        tags = process_keep(tags, keep.tags)

    for delete in config.deletes:
        tags = process_delete(tags, delete.tags)

    for insert in config.inserts:
        tags = process_insert(tags, insert.tags, insert.position)

    return tags


## TODO: フォールバックするしくみをつける
def do_all_caption_post_process(item: DanbooruPostItem, config: bool | CaptionConfig):
    if isinstance(config, bool):
        if not config:
            return item
        else:
            config = CaptionConfig()

    item.rating_tags = create_rating_tag(item.general_tags, item, config.rating)
    item.quality_tags = create_quality_tag(item, config.quality)

    item.artist_tags = do_caption_post_process(item.artist_tags, config.artist)
    item.copyright_tags = do_caption_post_process(item.copyright_tags, config.copyright)
    item.character_tags = do_caption_post_process(item.character_tags, config.character)
    item.general_tags = do_caption_post_process(item.general_tags, config.general)
    item.meta_tags = do_caption_post_process(item.meta_tags, config.meta)

    # 共通の処理
    if config.common is not None:
        item.artist_tags = do_caption_post_process(item.artist_tags, config.common)
        item.copyright_tags = do_caption_post_process(
            item.copyright_tags, config.common
        )
        item.character_tags = do_caption_post_process(
            item.character_tags, config.common
        )
        item.general_tags = do_caption_post_process(item.general_tags, config.common)
        item.meta_tags = do_caption_post_process(item.meta_tags, config.common)

    return item


def create_rating_tag(
    original: list[str], post_item: DanbooruPostItem, config: bool | RatingTagConfig
) -> list[str]:
    if isinstance(config, bool):
        if not config:  # false
            return []
        else:  # true
            config = RatingTagConfig()  # デフォルト設定

    if config.type == "none":
        return []

    elif config.type == "by_tag":
        if is_nsfw(original, config.nsfw_tags):
            return (
                normalize_tags(config.insert_tags)
                if config.insert_tags is not None
                else []
            )
        else:
            return []

    elif config.type == "by_rating":
        if post_item.post.rating == Rating.EXPLICIT:
            return (
                normalize_tags(config.explicit) if config.explicit is not None else []
            )
        elif post_item.post.rating == Rating.SENSITIVE:
            return (
                normalize_tags(config.sensitive) if config.sensitive is not None else []
            )
        elif post_item.post.rating == Rating.QUESTIONABLE:
            return (
                normalize_tags(config.questionable)
                if config.questionable is not None
                else []
            )
        elif post_item.post.rating == Rating.GENERAL:
            return normalize_tags(config.general) if config.general is not None else []
        else:
            raise Exception("Invalid rating: " + post_item.post.rating)

    raise Exception(f"Unexpected config type: {config.type}")


def create_quality_tag(
    post_item: DanbooruPostItem, config: QualityTagConfig | None
) -> list[str]:
    if config is None:
        return []

    tags = []

    for quality_tag, score in config.items():
        if post_item.post.score >= score:
            tags.append(quality_tag)
            break

    return tags
