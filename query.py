from __future__ import annotations


from typing import Optional, Literal, get_args

from scrape_config import SearchFilterConfig, SEARCH_RATING_TAG_ALL, SEARCH_RATING_ALIAS
from tags import FILETYPE


DAY_UNIT = Literal["years", "months", "weeks", "days", "hours", "minutes", "seconds"]


class Day:
    num: int
    unit: DAY_UNIT

    def __init__(self, num: int, unit: DAY_UNIT) -> None:
        self.num = num
        self.unit = unit

    def __str__(self) -> str:
        return f"{self.num}{self.unit[0]}"


def score_query(min: Optional[int] = None, max: Optional[int] = None) -> str:
    if min is None and max is None:
        return ""
    elif min is None:
        return f"score:<={max}"
    elif max is None:
        return f"score:>={min}"
    else:
        return f"score:{min}..{max}"


def date_query(start: Optional[str] = None, end: Optional[str] = None) -> str:
    if start is None and end is None:
        return ""
    elif start is None:
        return f"date:<={end}"
    elif end is None:
        return f"date:>={start}"
    else:
        return f"date:{start}..{end}"


def age_query(min: Optional[Day] = None, max: Optional[Day] = None) -> str:
    if min is None and max is None:
        return ""
    elif min is None:
        return f"age:<={max}"
    elif max is None:
        return f"age:>={min}"
    else:
        return f"age:{min}..{max}"


def tag_count_query(min: Optional[int] = None, max: Optional[int] = None) -> str:
    if min is None and max is None:
        return ""
    elif min is None:
        return f"tagcount:<={max}"
    elif max is None:
        return f"tagcount:>={min}"
    else:
        return f"tagcount:{min}..{max}"


def filetype_query(filetypes: list[FILETYPE] = None) -> str:
    if filetypes is None:
        return ""
    if len(filetypes) == 0:
        return ""
    else:
        return f"filetype:{','.join(filetypes)}"


def rating_query(
    include: Optional[list[SEARCH_RATING_TAG_ALL] | SEARCH_RATING_TAG_ALL] = None,
    exclude: Optional[list[SEARCH_RATING_TAG_ALL] | SEARCH_RATING_TAG_ALL] = None,
) -> str:
    if include is None and exclude is None:
        return ""

    include = [include] if isinstance(include, str) else include or []
    exclude = [exclude] if isinstance(exclude, str) else exclude or []

    def filter_tags(tags: list[SEARCH_RATING_TAG_ALL]) -> list[str]:
        query = set()

        for tag in tags or []:
            if tag in get_args(SEARCH_RATING_ALIAS):
                if tag == "sfw":
                    query |= set(["g", "s"])
                elif tag == "nsfw":
                    query |= set(["q", "e"])
                else:
                    raise ValueError(f"Unknown rating alias: {tag}")
            else:
                # 頭文字をとって短い記法に統一する
                query.add(tag[0])

        return list(query)

    include = f"rating:{','.join(filter_tags(include))}" if include else ""
    exclude = f"-rating:{','.join(filter_tags(exclude))}" if exclude else ""

    if include and exclude:
        return f"{include} {exclude}"
    elif include:
        return include
    elif exclude:
        return exclude
    else:
        return ""


def compose_query(
    base_query: str,
    filter: Optional[bool | SearchFilterConfig],
    fallback_filter: SearchFilterConfig,
) -> str:
    if isinstance(filter, bool):
        if filter:
            filter = SearchFilterConfig()  # デフォルト値
        else:
            return base_query  # なにもしない

    filter = fallback_filter if filter is None else filter

    query = [base_query]

    if filter.score is not None:
        query.append(score_query(filter.score.min, filter.score.max))

    if filter.date is not None:
        query.append(date_query(filter.date.start, filter.date.end))

    if filter.age is not None:
        query.append(age_query(filter.age.min, filter.age.max))

    if filter.tag_count is not None:
        query.append(tag_count_query(filter.tag_count.min, filter.tag_count.max))

    if filter.filetypes is not None:
        query.append(filetype_query(filter.filetypes))

    if filter.rating is not None:
        query.append(rating_query(filter.rating.include, filter.rating.exclude))

    return " ".join(query)
