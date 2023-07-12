from __future__ import annotations


from typing import Optional, Literal

from scrape_config import FilterConfig
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
    if len(filetypes) == 0:
        return ""
    else:
        return f"filetype:{','.join(filetypes)}"


def compose_query(
    base_query: str, filter: FilterConfig, fallback_filter: FilterConfig
) -> str:
    query = [base_query]

    if filter.score is not None:
        query.append(score_query(filter.score.min, filter.score.max))
    elif fallback_filter.score is not None:
        query.append(score_query(fallback_filter.score.min, fallback_filter.score.max))

    if filter.date is not None:
        query.append(date_query(filter.date.start, filter.date.end))
    elif fallback_filter.date is not None:
        query.append(date_query(fallback_filter.date.start, fallback_filter.date.end))

    if filter.age is not None:
        query.append(age_query(filter.age.min, filter.age.max))
    elif fallback_filter.age is not None:
        query.append(age_query(fallback_filter.age.min, fallback_filter.age.max))

    if filter.tag_count is not None:
        query.append(tag_count_query(filter.tag_count.min, filter.tag_count.max))
    elif fallback_filter.tag_count is not None:
        query.append(
            tag_count_query(
                fallback_filter.tag_count.min, fallback_filter.tag_count.max
            )
        )

    if filter.filetypes is not None:
        query.append(filetype_query(filter.filetypes))
    elif fallback_filter.filetypes is not None:
        query.append(filetype_query(fallback_filter.filetypes))

    return " ".join(query)
