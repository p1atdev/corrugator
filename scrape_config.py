from typing import Optional, Literal

from pydantic import BaseModel
import yaml
import json
import toml

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


# tags で str の場合は強制的にファイルパスとみなし、そのファイルを読みに行く


# レーティング (nsfwなど) タグ設定
class RatingTagConfig(BaseModel):
    type: RATING_TAG_ACTION = "by_tag"  # 推奨

    # by_tag (事前に設定したタグが含まれる場合のみ nsfw判定。投稿のレーティングは無視される)
    nsfw_tags: str | list[str] = utils.load_file_lines(SENSITIVE_TAGS_FILE)
    insert_tags: str | list[str] = utils.load_file_lines(NSFW_PREFIX_FILE)

    # こちらが指定されたらこっちを優先
    nsfw_tag_file_path: Optional[str] = None
    insert_tag_file_path: Optional[str] = None

    # by_rating (非推奨)
    explicit: Optional[str] = "explicit"
    sensitive: Optional[str] = "sensitive"
    questionable: Optional[str] = "questionable"
    general: Optional[str] = None


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

    rating: bool | RatingTagConfig = RatingTagConfig()

    common: Optional[CaptionPostProcessConfig] = None


# 検索時のフィルター (人的スコア)
class ScoreFilterConfig(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


# 検索時のフィルター (投稿日)
class DateFilterConfig(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


# 検索時のフィルター (投稿日からの経過日数)
class AgeFilterConfig(BaseModel):
    min: Optional[str] = None
    max: Optional[str] = None


# 検索時のフィルター (画像についてるタグ数)
class TagCountFilterConfig(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None


# 検索時のフィルター設定
class SearchFilterConfig(BaseModel):
    score: Optional[ScoreFilterConfig] = None
    date: Optional[DateFilterConfig] = None
    age: Optional[AgeFilterConfig] = None
    tag_count: Optional[TagCountFilterConfig] = None
    filetypes: Optional[list[str]] = None

    # TODO: ソート順の対応


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
    domain: Optional[AVAIABLE_DOMAINS] = None

    output_path: str
    save_state_path: Optional[str] = None

    limit: int = 100
    caption: bool | CaptionConfig = False


# シンプルに検索ワードで検索
class QuerySubset(ScrapeSubset):
    query: str

    search_filter: Optional[SearchFilterConfig] = None
    search_result_filter: Optional[SearchResultFilterConfig] = None


# 事前に用意した検索ワードのリストファイルを使って検索
class QueryListSubset(ScrapeSubset):
    query_list_file: str

    search_filter: Optional[SearchFilterConfig] = None
    search_result_filter: Optional[SearchResultFilterConfig] = None


# danbooru の post の url リストから取得する
class PostListSubset(ScrapeSubset):
    post_url_list_file: str
    # FIXME: 実装する


# 全体の設定
class ScrapeConfig(BaseModel):
    domain: AVAIABLE_DOMAINS = "danbooru.donmai.us"

    # TODO: 認証情報の対応

    subsets: list[QuerySubset | QueryListSubset | PostListSubset]

    # サブセットで指定されなかったらこっちにフォールバックされる
    caption: bool | CaptionConfig = False
    search_filter: Optional[SearchFilterConfig] = SearchFilterConfig()
    search_result_filter: Optional[
        SearchResultFilterConfig
    ] = SearchResultFilterConfig()

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
