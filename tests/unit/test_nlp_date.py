"""Tests for natural language date parsing."""

import pytest
from datetime import datetime
from capsule.search.nlp_date import parse_date_range


NOW = datetime(2024, 4, 15, 12, 0, 0)  # Fixed reference: Monday April 15 2024


def test_days_ago():
    from_dt, to_dt, cleaned = parse_date_range("invoice 3 days ago", now=NOW)
    assert from_dt is not None
    assert "3 days ago" not in cleaned
    assert "invoice" in cleaned


def test_weeks_ago():
    from_dt, to_dt, cleaned = parse_date_range("quote from Ahmed 2 weeks ago", now=NOW)
    assert from_dt is not None
    assert "quote from Ahmed" in cleaned


def test_yesterday():
    from_dt, to_dt, cleaned = parse_date_range("what did we discuss yesterday", now=NOW)
    assert from_dt is not None
    assert "yesterday" not in cleaned


def test_last_week():
    from_dt, to_dt, cleaned = parse_date_range("meeting notes last week", now=NOW)
    assert from_dt is not None
    assert to_dt is not None


def test_last_month():
    from_dt, to_dt, cleaned = parse_date_range("bank slip last month", now=NOW)
    assert from_dt is not None
    assert "last month" not in cleaned


def test_named_month():
    from_dt, to_dt, cleaned = parse_date_range("project proposal in March", now=NOW)
    assert from_dt is not None
    assert "2024-03" in from_dt


def test_last_weekday():
    from_dt, to_dt, cleaned = parse_date_range("what we decided last Tuesday", now=NOW)
    assert from_dt is not None
    assert "last Tuesday" not in cleaned


def test_no_date():
    from_dt, to_dt, cleaned = parse_date_range("quote from Ahmed", now=NOW)
    assert from_dt is None
    assert to_dt is None
    assert cleaned == "quote from Ahmed"


def test_pure_date_query():
    from_dt, to_dt, cleaned = parse_date_range("last week", now=NOW)
    assert from_dt is not None
    assert cleaned.strip() == ""
