"""Tests for text ingestion and cleaning."""

import pytest
from capsule.ingest.text import extract_from_string, _strip_html, _clean


def test_extract_from_string():
    result = extract_from_string("Hello world, this is a test")
    assert result["text"] == "Hello world, this is a test"


def test_strip_html():
    html = "<p>Hello <b>world</b></p><script>alert('x')</script>"
    result = _strip_html(html)
    assert "Hello" in result
    assert "world" in result
    assert "<p>" not in result
    assert "alert" not in result


def test_clean_whitespace():
    messy = "Hello    world\n\n\n\nTest"
    result = _clean(messy)
    assert "  " not in result
    assert result.count("\n") <= 2


def test_html_entities():
    html = "Price &amp; Quote &lt;15k&gt;"
    result = _strip_html(html)
    assert "&amp;" not in result
    assert "&lt;" not in result
