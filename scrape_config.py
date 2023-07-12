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


# レーティング (nsfwなど) タグ設定
class RatingTagConfig(BaseModel):
    type: RATING_TAG_ACTION = "by_tag"  # 推奨

    # by_tag (事前に設定したタグが含まれる場合のみ nsfw判定。投稿のレーティングは無視される)
    nsfw_tags: list[str] = SENSITIVE_TAGS
    insert_tags: str | list[str] = NSFW_TAG

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
    artist_tags: bool | CaptionPostProcessConfig = False
    character_tags: bool | CaptionPostProcessConfig = True
    copyright_tags: bool | CaptionPostProcessConfig = True
    general_tags: bool | CaptionPostProcessConfig = True
    meta_tags: bool | CaptionPostProcessConfig = CaptionPostProcessConfig(
        keeps=[
            KeepConfig(tags=ALLOWED_META_TAGS),
        ]
    )

    rating: bool | RatingTagConfig = RatingTagConfig()

    common: Optional[CaptionPostProcessConfig] = None


# 検索後のフィルター (検索結果数に影響する)
class ResultPostProcessConfig(BaseModel):
    must_include: list[str] = []  # 含んではならない
    must_exclude: list[str] = []  # 含んでいなければならない

    # TODO: parent や children などの判定もする


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
class FilterConfig(BaseModel):
    score: Optional[ScoreFilterConfig] = None
    date: Optional[DateFilterConfig] = None
    age: Optional[AgeFilterConfig] = None
    tag_count: Optional[TagCountFilterConfig] = None
    filetypes: Optional[list[str]] = None

    # TODO: ソート順の対応


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

    filter: Optional[FilterConfig] = FilterConfig()


# 事前に用意した検索ワードのリストファイルを使って検索
class QueryListSubset(ScrapeSubset):
    query_list_file: str

    filter: Optional[FilterConfig] = FilterConfig()


# danbooru の post の url リストから取得する
class PostListSubset(ScrapeSubset):
    post_url_list_file: str
    # FIXME: 実装する


# 全体の設定
class ScrapeConfig(BaseModel):
    domain: AVAIABLE_DOMAINS = "danbooru.donmai.us"

    subsets: list[QuerySubset | QueryListSubset | PostListSubset]

    # サブセットで指定されなかったらこっちにフォールバックされる
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
