from typing import Literal

from pydantic import BaseModel, validator, root_validator
import yaml
import json
import toml
from base64 import b64encode

import utils
from default_tags import (
    SENSITIVE_TAGS_FILE,
    NSFW_PREFIX_FILE,
    ALLOWED_META_TAGS_FILE,
    EXCLUSION_TAGS_FILE,
)

AVAIABLE_DOMAINS = Literal["danbooru.donmai.us", "safebooru.donmai.us"]

INSERT_POSITION = Literal["start", "end"]
RATING_TAG_ACTION = Literal["by_tag", "by_rating", "none"]

# https://danbooru.donmai.us/wiki_pages/howto%3Arate
SEARCH_RATING_TAG_SHORT = Literal["g", "s", "q", "e"]
SEARCH_RATING_TAG_LONG = Literal["general", "sensitive", "questionable", "explicit"]
SEARCH_RATING_ALIAS = Literal["sfw", "nsfw"]
SEARCH_RATING_TAG = SEARCH_RATING_TAG_SHORT | SEARCH_RATING_TAG_LONG
SEARCH_RATING_TAG_ALL = SEARCH_RATING_TAG | SEARCH_RATING_ALIAS

# tags で str の場合は強制的にファイルパスとみなし、そのファイルを読みに行く

CATEGORY_ORDER_STYLE = Literal["wd", "naidv3", "animaginexlv3"]

FILETYPE = Literal["jpg", "png", "gif", "webm", "mp4", "swf", "zip", "webp", "avif"]


# レーティング (nsfwなど) タグ設定
class RatingTagConfig(BaseModel):
    type: RATING_TAG_ACTION = "by_tag"  # 推奨

    # by_tag (事前に設定したタグが含まれる場合のみ nsfw判定。投稿のレーティングは無視される)
    nsfw_tags: str | list[str] = utils.load_file_lines(SENSITIVE_TAGS_FILE)
    insert_tags: str | list[str] = utils.load_file_lines(NSFW_PREFIX_FILE)

    # こちらが指定されたらこっちを優先
    nsfw_tag_file_path: str | None = None
    insert_tag_file_path: str | None = None

    # by_rating (非推奨)
    explicit: str | list[str] | None = "explicit"
    sensitive: str | list[str] | None = "sensitive"
    questionable: str | list[str] | None = "questionable"
    general: str | list[str] | None = None


# 置換
class ReplaceConfig(BaseModel):
    tags: str | list[str]
    to: str


# 保持・それ以外削除
class KeepConfig(BaseModel):
    tags: str | list[str]


# 削除
class DeleteConfig(BaseModel):
    tags: str | list[str]


# 挿入
class InsertConfig(BaseModel):
    tags: str | list[str]

    position: INSERT_POSITION = "start"


# 保存される画像のタグ (1girlなど) の調整
class CaptionPostProcessConfig(BaseModel):
    replaces: list[ReplaceConfig] = []  # 指定されたものを置換
    keeps: list[KeepConfig] = []  # 指定されたもの以外を除外
    deletes: list[DeleteConfig] = []  # 指定されたものを削除
    inserts: list[InsertConfig] = []  # 指定されたものを追加 (前か後ろ)


# masterpiece... などのタグを投稿の評価を基準に追加する
QualityTagConfig = dict[str, int]


# 使用するタグの設定
class CaptionConfig(BaseModel):
    extension: str = "txt"
    overwrite: bool = False

    # False は使用しない、True　はすべて使用、 それ以外は CaptionPostProcessConfig の処理を実行
    artist: bool | CaptionPostProcessConfig = False
    character: bool | CaptionPostProcessConfig = True
    copyright: bool | CaptionPostProcessConfig = True
    general: bool | CaptionPostProcessConfig = True
    meta: bool | CaptionPostProcessConfig = CaptionPostProcessConfig(
        keeps=[
            KeepConfig(tags=utils.load_file_lines(ALLOWED_META_TAGS_FILE)),
        ]
    )

    category_separator: str = ", "
    category_order: CATEGORY_ORDER_STYLE | None = None

    rating: bool | RatingTagConfig = RatingTagConfig()

    quality: QualityTagConfig | None = None

    common: bool | CaptionPostProcessConfig | None = None

    @validator("quality", pre=True)
    def sort_array(cls, v, values):
        if v is None:
            return v
        if isinstance(v, dict):
            return dict(sorted(v.items(), key=lambda item: item[1], reverse=True))
        return v

    @validator("category_order", pre=True)
    def lower_category_order(cls, v, values):
        if v is None:
            return v

        return v.lower()


# 検索時のフィルター (人的スコア)
class ScoreFilterConfig(BaseModel):
    min: int | None = None
    max: int | None = None


# 検索時のフィルター (投稿日)
class DateFilterConfig(BaseModel):
    start: str | None = None
    end: str | None = None


# 検索時のフィルター (投稿日からの経過日数)
class AgeFilterConfig(BaseModel):
    min: str | None = None
    max: str | None = None


# 検索時のフィルター (画像についてるタグ数)
class TagCountFilterConfig(BaseModel):
    min: int | None = None
    max: int | None = None


# ソート順
class SortOrderConfig(BaseModel):
    type: Literal["score", "rank", "upvotes", "downvotes"] | None = None
    direction: Literal["asc", "desc", "none"] | None = None


class RatingFilterConfig(BaseModel):
    include: list[SEARCH_RATING_TAG_ALL] | SEARCH_RATING_TAG_ALL | None = None
    exclude: list[SEARCH_RATING_TAG_ALL] | SEARCH_RATING_TAG_ALL | None = None


# 検索時のフィルター設定
class SearchFilterConfig(BaseModel):
    score: ScoreFilterConfig | None = None
    date: DateFilterConfig | None = None
    age: AgeFilterConfig | None = None
    tag_count: TagCountFilterConfig | None = None
    filetypes: list[FILETYPE] | None = None
    order: SortOrderConfig | str | None = None
    rating: RatingFilterConfig | None = None


# 検索後のフィルター (検索結果数に影響する)
class SearchResultFilterConfig(BaseModel):
    # 上から順に適用される
    include_any: str | list[str] = []  # どれかを含んでいなければならない
    include_all: str | list[str] = []  # すべてを含んでいなければならない
    exclude_any: str | list[str] = utils.load_file_lines(
        EXCLUSION_TAGS_FILE
    )  # ひとつでも含んではいけない
    exclude_all: str | list[str] = []  # すべて含んでいるのはだめ

    # TODO: parent や children などの判定もする


class ScrapeSubset(BaseModel):
    # サブセットごとにドメインを指定可能
    domain: AVAIABLE_DOMAINS | None = None

    output_path: str
    save_state_path: str | None = None

    limit: int = 100
    caption: CaptionConfig | None = None

    @root_validator(pre=True)
    def set_default_values(cls, values):
        if "caption" in values and isinstance(values["caption"], bool):
            if values["caption"]:
                values["caption"] = CacheConfig()
            else:
                values["caption"] = None

        return values


# シンプルに検索ワードで検索
class QuerySubset(ScrapeSubset):
    query: str

    search_filter: SearchFilterConfig | None = None
    search_result_filter: SearchResultFilterConfig | None = None

    @root_validator(pre=True)
    def set_default_values(cls, values):
        if "search_filter" in values and isinstance(values["search_filter"], bool):
            if values["search_filter"]:
                values["search_filter"] = SearchFilterConfig()
            else:
                values["search_filter"] = None

        if "search_result_filter" in values and isinstance(
            values["search_result_filter"], bool
        ):
            if values["search_result_filter"]:
                values["search_result_filter"] = SearchResultFilterConfig()
            else:
                values["search_result_filter"] = None

        return values


# 事前に用意した検索ワードのリストファイルを使って検索
class QueryListSubset(ScrapeSubset):
    query_list_file: str

    search_filter: SearchFilterConfig | None = None
    search_result_filter: SearchResultFilterConfig | None = None

    @root_validator(pre=True)
    def set_default_values(cls, values):
        if "search_filter" in values and isinstance(values["search_filter"], bool):
            if values["search_filter"]:
                values["search_filter"] = SearchFilterConfig()
            else:
                values["search_filter"] = None

        if "search_result_filter" in values and isinstance(
            values["search_result_filter"], bool
        ):
            if values["search_result_filter"]:
                values["search_result_filter"] = SearchResultFilterConfig()
            else:
                values["search_result_filter"] = None

        return values


# danbooru の post の url リストから取得する
class PostListSubset(ScrapeSubset):
    post_url_list_file: str
    # FIXME: 実装する


class AuthConfig(BaseModel):
    username: str
    api_key: str

    def basic_auth(self) -> str:
        return b64encode(f"{self.username}:{self.api_key}".encode("utf-8")).decode(
            "utf-8"
        )


class CacheConfig(BaseModel):
    search_result: bool = True


# 全体の設定
class ScrapeConfig(BaseModel):
    domain: AVAIABLE_DOMAINS = "danbooru.donmai.us"

    auth: AuthConfig | None = None

    subsets: list[QuerySubset | QueryListSubset | PostListSubset]

    # サブセットで指定されなかったらこっちにフォールバックされる
    caption: CaptionConfig = CaptionConfig()
    search_filter: SearchFilterConfig = SearchFilterConfig()
    search_result_filter: SearchResultFilterConfig = SearchResultFilterConfig()

    max_workers: int = 10

    cache: bool | CacheConfig = False

    @root_validator(pre=True)
    def set_default_values(cls, values):
        if "caption" not in values or values["caption"] is None:
            values["caption"] = CacheConfig()

        if "search_filter" not in values or values["search_filter"] is None:
            values["search_filter"] = SearchFilterConfig()

        if (
            "search_result_filter" not in values
            or values["search_result_filter"] is None
        ):
            values["search_result_filter"] = SearchResultFilterConfig()

        return values


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
