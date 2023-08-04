from enum import Enum
from pydantic import BaseModel
from datetime import datetime

from typing import List, Optional


class FileEXT(str, Enum):
    JPG = "jpg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    WEBM = "webm"
    MP4 = "mp4"
    ZIP = "zip"
    AVIF = "avif"


class Status(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class VariantTypeEnum(str, Enum):
    ORIGINAL = "original"
    SAMPLE = "sample"
    THE_180_X180 = "180x180"
    THE_360_X360 = "360x360"
    THE_720_X720 = "720x720"


class Variant(BaseModel):
    type: VariantTypeEnum
    url: str
    width: int
    height: int
    file_ext: FileEXT


class MediaAsset(BaseModel):
    id: int
    created_at: str
    updated_at: str
    md5: Optional[str] = None
    file_ext: FileEXT
    file_size: int
    image_width: int
    image_height: int
    duration: Optional[float] = None
    status: Status
    file_key: Optional[str] = None
    is_public: bool
    pixel_hash: str
    variants: List[Variant] = []


class Rating(str, Enum):
    EXPLICIT = "e"
    GENERAL = "g"
    QUESTIONABLE = "q"
    SENSITIVE = "s"


class DanbooruPost(BaseModel):
    id: int
    created_at: str
    uploader_id: int
    score: int
    source: str
    rating: Rating
    image_width: int
    image_height: int
    tag_string: str
    fav_count: int
    file_ext: FileEXT
    has_children: bool
    tag_count_general: int
    tag_count_artist: int
    tag_count_character: int
    tag_count_copyright: int
    file_size: int
    up_score: int
    down_score: int
    is_pending: bool
    is_flagged: bool
    is_deleted: bool
    tag_count: int
    updated_at: str
    is_banned: bool
    has_active_children: bool
    bit_flags: int
    tag_count_meta: int
    has_large: bool
    has_visible_children: bool
    media_asset: MediaAsset
    tag_string_general: str
    tag_string_character: str
    tag_string_copyright: str
    tag_string_artist: str
    tag_string_meta: str

    md5: Optional[str] = None
    file_url: Optional[str] = None
    large_file_url: Optional[str] = None
    preview_file_url: Optional[str] = None

    last_comment_bumped_at: Optional[str] = None
    last_noted_at: Optional[str] = None
    last_commented_at: Optional[str] = None
    pixiv_id: Optional[int] = None
    parent_id: Optional[int] = None
    approver_id: Optional[int] = None
