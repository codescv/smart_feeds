import pytest
from tools.storage import _clean_title, _clean_html_to_markdown, _extract_urls_from_markdown

def test_clean_title():
    assert _clean_title("<b>Hello</b> World") == "**Hello** World"
    assert _clean_title("  Space   ") == "Space"
    assert len(_clean_title("a" * 100)) <= 80
    assert _clean_title("Line\nBreak") == "Line Break"

def test_clean_html_to_markdown():
    html = "<h1>Title</h1><p>Body</p>"
    md = _clean_html_to_markdown(html)
    assert "**Title**" in md
    assert "Body" in md

def test_extract_urls_from_markdown():
    md = "Check [Google](https://google.com) or https://example.com"
    urls = _extract_urls_from_markdown(md)
    assert "https://google.com" in urls
    assert "https://example.com" in urls
    assert len(urls) == 2
