"""
Natural language date parser.
Converts human date expressions to datetime ranges.
"2 weeks ago", "last Tuesday", "yesterday", "March", "last month"
No external dependencies — pure Python.
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def parse_date_range(query: str, now: datetime = None) -> tuple[Optional[str], Optional[str], str]:
    """
    Extract date range from natural language query.
    Returns: (from_date_iso, to_date_iso, cleaned_query)

    cleaned_query has the date expression removed so search works on remaining terms.
    """
    now = now or datetime.utcnow()
    original_query = query
    from_dt = None
    to_dt = None

    patterns = [
        # "X days/weeks/months ago"
        (r"\b(\d+)\s+days?\s+ago\b", lambda m: _ago(now, days=int(m.group(1)))),
        (r"\b(\d+)\s+weeks?\s+ago\b", lambda m: _ago(now, weeks=int(m.group(1)))),
        (r"\b(\d+)\s+months?\s+ago\b", lambda m: _ago(now, months=int(m.group(1)))),

        # "yesterday", "today"
        (r"\byesterday\b", lambda m: _day_range(now - timedelta(days=1))),
        (r"\btoday\b", lambda m: _day_range(now)),

        # "last week", "last month", "last year"
        (r"\blast\s+week\b", lambda m: _last_week(now)),
        (r"\blast\s+month\b", lambda m: _last_month(now)),
        (r"\blast\s+year\b", lambda m: _last_year(now)),

        # "this week", "this month"
        (r"\bthis\s+week\b", lambda m: _this_week(now)),
        (r"\bthis\s+month\b", lambda m: _this_month(now)),

        # "last Monday/Tuesday/..." — most recent past occurrence
        (r"\blast\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
         lambda m: _last_weekday(now, m.group(1))),

        # "on Monday" — most recent past occurrence
        (r"\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
         lambda m: _last_weekday(now, m.group(1))),

        # Named months: "in March", "March", "last March"
        (r"\b(?:in\s+|last\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)\b",
         lambda m: _named_month(now, m.group(1))),

        # Date ranges: "past X days/weeks"
        (r"\bpast\s+(\d+)\s+days?\b", lambda m: _range_from_now(now, days=int(m.group(1)))),
        (r"\bpast\s+(\d+)\s+weeks?\b", lambda m: _range_from_now(now, weeks=int(m.group(1)))),
    ]

    for pattern, handler in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            result = handler(match)
            if result:
                from_dt, to_dt = result
                # Remove matched date expression from query
                query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()
                query = re.sub(r"\s{2,}", " ", query)
            break  # only apply first match

    return (
        from_dt.isoformat() if from_dt else None,
        to_dt.isoformat() if to_dt else None,
        query,
    )


def _ago(now, days=0, weeks=0, months=0):
    """Point in time X ago → range that whole day."""
    if months:
        # Approximate months as 30 days
        target = now - timedelta(days=months * 30)
    else:
        target = now - timedelta(days=days, weeks=weeks)
    return _day_range(target)


def _day_range(dt: datetime):
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _last_week(now):
    # Monday to Sunday of last week
    today = now.date()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)
    last_sunday = last_monday + timedelta(days=6)
    start = datetime.combine(last_monday, datetime.min.time())
    end = datetime.combine(last_sunday, datetime.max.time().replace(microsecond=0))
    return start, end


def _last_month(now):
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0)
    last_of_prev = first_of_this_month - timedelta(seconds=1)
    first_of_prev = last_of_prev.replace(day=1, hour=0, minute=0, second=0)
    return first_of_prev, last_of_prev


def _last_year(now):
    last_year = now.year - 1
    start = datetime(last_year, 1, 1)
    end = datetime(last_year, 12, 31, 23, 59, 59)
    return start, end


def _this_week(now):
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    start = datetime.combine(monday, datetime.min.time())
    return start, now


def _this_month(now):
    start = now.replace(day=1, hour=0, minute=0, second=0)
    return start, now


def _last_weekday(now, weekday_name: str):
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}
    target_weekday = days[weekday_name.lower()]
    today_weekday = now.weekday()
    days_back = (today_weekday - target_weekday) % 7
    if days_back == 0:
        days_back = 7  # "last Monday" when today is Monday = 7 days ago
    target = now - timedelta(days=days_back)
    return _day_range(target)


def _named_month(now, month_name: str):
    months = {"january": 1, "february": 2, "march": 3, "april": 4,
              "may": 5, "june": 6, "july": 7, "august": 8,
              "september": 9, "october": 10, "november": 11, "december": 12}
    month_num = months[month_name.lower()]
    year = now.year
    if month_num > now.month:
        year -= 1  # "March" when we're in February = last year's March
    import calendar
    _, last_day = calendar.monthrange(year, month_num)
    start = datetime(year, month_num, 1)
    end = datetime(year, month_num, last_day, 23, 59, 59)
    return start, end


def _range_from_now(now, days=0, weeks=0):
    start = now - timedelta(days=days, weeks=weeks)
    return start, now
