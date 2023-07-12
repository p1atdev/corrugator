from typing import Optional, Literal, Union

from pydantic import BaseModel
import yaml
import json
import toml


from default_tags import (
    SENSITIVE_TAGS,
    NSFW_TAG,
    ALLOWED_META_TAGS,
)

AVAIABLE_DOMAINS = Literal["danbooru.donmai.us", "safebooru.donmai.us"]

INSERT_POSITION = Literal["start", "end"]
RATING_TAG_ACTION = Literal["by_tag", "by_rating", "none"]


class RatingTagConfig(BaseModel):
    type: RATING_TAG_ACTION = "by_tag"

    # by_tag
    nsfw_tags: list[str] = SENSITIVE_TAGS
    insert_tags: str | list[str] = NSFW_TAG

    # by_rating
    explicit: Optional[str] = "explicit"
    sensitive: Optional[str] = "sensitive"
    questionable: Optional[str] = "questionable"
    general: Optional[str] = None


class ReplaceConfig(BaseModel):
    tags: str | list[str]
    to: str


class KeepConfig(BaseModel):
    tags: str | list[str]


class DeleteConfig(BaseModel):
    tags: str | list[str]


class InsertConfig(BaseModel):
    tags: str | list[str]

    position: INSERT_POSITION = "start"


class PostProcessConfig(BaseModel):
    replaces: list[ReplaceConfig] = []
    keeps: list[KeepConfig] = []
    deletes: list[DeleteConfig] = []
    inserts: list[InsertConfig] = []


class CaptionConfig(BaseModel):
    extension: str = "txt"
    overwrite: bool = False

    artist_tags: bool | PostProcessConfig = False
    character_tags: bool | PostProcessConfig = True
    copyright_tags: bool | PostProcessConfig = True
    general_tags: bool | PostProcessConfig = True
    meta_tags: bool | PostProcessConfig = PostProcessConfig(
        keeps=[
            KeepConfig(tags=ALLOWED_META_TAGS),
        ]
    )

    rating: bool | RatingTagConfig = RatingTagConfig()

    common: Optional[PostProcessConfig] = None


class ScoreFilterConfig(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class DateFilterConfig(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class AgeFilterConfig(BaseModel):
    min: Optional[str] = None
    max: Optional[str] = None


class TagCountFilterConfig(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


class FilterConfig(BaseModel):
    score: Optional[ScoreFilterConfig] = None
    date: Optional[DateFilterConfig] = None
    age: Optional[AgeFilterConfig] = None
    tag_count: Optional[TagCountFilterConfig] = None
    filetypes: Optional[list[str]] = None


class ScrapeSubset(BaseModel):
    domain: Optional[AVAIABLE_DOMAINS] = None

    output_path: str
    save_state_path: Optional[str] = None

    limit: int = 100
    caption: bool | CaptionConfig = False


# シンプルに検索ワードで検索
class QuerySubset(ScrapeSubset):
    query: str

    filter: Optional[FilterConfig] = FilterConfig()


# 事前に用意した検索ワードのリストファイルを使って検索
class QueryListSubset(ScrapeSubset):
    query_list_file: str

    filter: Optional[FilterConfig] = FilterConfig()


# danbooru の post の url リストから取得する
class PostListSubset(ScrapeSubset):
    post_url_list_file: str


class ScrapeConfig(BaseModel):
    domain: AVAIABLE_DOMAINS = "danbooru.donmai.us"

    subsets: list[QuerySubset | QueryListSubset | PostListSubset]

    caption: bool | CaptionConfig = False
    filter: Optional[FilterConfig] = FilterConfig()

    max_workers: int = 10


def load_scrape_config_yaml(yaml_file: str) -> ScrapeConfig:
    with open(yaml_file, "r", encoding="utf-8") as f:
        return ScrapeConfig(**yaml.safe_load(f))


def load_scrape_config_toml(toml_file: str) -> ScrapeConfig:
    with open(toml_file, "r", encoding="utf-8") as f:
        return ScrapeConfig(**toml.load(f))


def load_scrape_config_json(json_file: str) -> ScrapeConfig:
    with open(json_file, "r", encoding="utf-8") as f:
        return ScrapeConfig(**json.load(f))


def load_scrape_config(file: str) -> ScrapeConfig:
    if file.lower().endswith(".yaml"):
        return load_scrape_config_yaml(file)
    elif file.lower().endswith(".toml"):
        return load_scrape_config_toml(file)
    elif file.lower().endswith(".json"):
        return load_scrape_config_json(file)
    else:
        raise Exception("Unsupported config file type")
