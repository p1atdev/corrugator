from __future__ import annotations


from typing import Literal, get_args

from scrape_config import (
    SearchFilterConfig,
    SortOrderConfig,
    SEARCH_RATING_TAG_ALL,
    SEARCH_RATING_ALIAS,
)
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


def score_query(min: int | None = None, max: int | None = None) -> str:
    if min is None and max is None:
        return ""
    elif min is None:
        return f"score:<={max}"
    elif max is None:
        return f"score:>={min}"
    else:
        return f"score:{min}..{max}"


def date_query(start: str | None = None, end: str | None = None) -> str:
    if start is None and end is None:
        return ""
    elif start is None:
        return f"date:<={end}"
    elif end is None:
        return f"date:>={start}"
    else:
        return f"date:{start}..{end}"


def age_query(min: Day | str | None = None, max: Day | str | None = None) -> str:
    if min is None and max is None:
        return ""
    elif min is None:
        return f"age:<={max}"
    elif max is None:
        return f"age:>={min}"
    else:
        return f"age:{min}..{max}"


def tag_count_query(min: int | None = None, max: int | None = None) -> str:
    if min is None and max is None:
        return ""
    elif min is None:
        return f"tagcount:<={max}"
    elif max is None:
        return f"tagcount:>={min}"
    else:
        return f"tagcount:{min}..{max}"


def filetype_query(filetypes: list[FILETYPE] | None = None) -> str:
    if filetypes is None:
        return ""
    if len(filetypes) == 0:
        return ""
    else:
        return f"filetype:{','.join(filetypes)}"


def search_order(order: SortOrderConfig | str | None) -> str:
    if isinstance(order, str):
        type = order
        direction = None
    elif isinstance(order, SortOrderConfig):
        type, direction = order.type, order.direction
    else:
        return ""

    if type is None:
        return ""

    query = f"order:{type}"

    if direction is not None and direction != "none":
        query += f"_{direction}"

    return query


def rating_query(
    include: list[SEARCH_RATING_TAG_ALL] | SEARCH_RATING_TAG_ALL | None = None,
    exclude: list[SEARCH_RATING_TAG_ALL] | SEARCH_RATING_TAG_ALL | None = None,
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

    include_query = f"rating:{','.join(filter_tags(include))}" if include else ""
    exclude_query = f"-rating:{','.join(filter_tags(exclude))}" if exclude else ""

    if include_query and exclude_query:
        return f"{include_query} {exclude_query}"
    elif include_query:
        return include_query
    elif exclude_query:
        return exclude_query
    else:
        return ""


def compose_query(
    base_query: str,
    filter: bool | SearchFilterConfig | None,
    fallback_filter: SearchFilterConfig,
) -> str:
    if isinstance(filter, bool):
        if filter:  # true
            filter = SearchFilterConfig()  # デフォルト値
        else:
            return base_query  # なにもしない

    query = [base_query]

    if filter is not None and filter.score is not None:
        query.append(score_query(filter.score.min, filter.score.max))
    elif fallback_filter.score is not None:
        query.append(score_query(fallback_filter.score.min, fallback_filter.score.max))

    if filter is not None and filter.date is not None:
        query.append(date_query(filter.date.start, filter.date.end))
    elif fallback_filter.date is not None:
        query.append(date_query(fallback_filter.date.start, fallback_filter.date.end))

    if filter is not None and filter.age is not None:
        query.append(age_query(filter.age.min, filter.age.max))
    elif fallback_filter.age is not None:
        query.append(age_query(fallback_filter.age.min, fallback_filter.age.max))

    if filter is not None and filter.tag_count is not None:
        query.append(tag_count_query(filter.tag_count.min, filter.tag_count.max))
    elif fallback_filter.tag_count is not None:
        query.append(
            tag_count_query(
                fallback_filter.tag_count.min, fallback_filter.tag_count.max
            )
        )

    if filter is not None and filter.filetypes is not None:
        query.append(filetype_query(filter.filetypes))
    elif fallback_filter.filetypes is not None:
        query.append(filetype_query(fallback_filter.filetypes))

    if filter is not None and filter.order is not None:
        query.append(search_order(filter.order))
    elif fallback_filter.order is not None:
        query.append(search_order(fallback_filter.order))

    if filter is not None and filter.rating is not None:
        query.append(rating_query(filter.rating.include, filter.rating.exclude))
    elif fallback_filter.rating is not None:
        query.append(
            rating_query(fallback_filter.rating.include, fallback_filter.rating.exclude)
        )

    return " ".join(query)
