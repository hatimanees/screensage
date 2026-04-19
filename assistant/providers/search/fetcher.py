import urllib.request
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """Strips HTML tags and skips non-content elements."""

    _SKIP = {"script", "style", "nav", "header", "footer", "aside", "noscript"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.parts.append(text)


def fetch_url(url: str, max_chars: int = 5000) -> str:
    """Fetch a URL and return clean readable text, truncated to max_chars."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ScreenSage/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Failed to fetch URL: {e}"

    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)

    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"

    return text or "No readable content found at this URL."
