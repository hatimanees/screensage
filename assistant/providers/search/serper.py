import json
import urllib.request


def web_search(query: str, api_key: str) -> str:
    """Search the web via Serper. Returns answer box + top snippets as plain text."""
    payload = json.dumps({"q": query, "num": 5}).encode()
    req = urllib.request.Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return f"Search failed: {e}"

    lines = []

    # Answer box is the highest-quality signal
    ab = data.get("answerBox", {})
    answer = ab.get("answer") or ab.get("snippet") or ""
    if answer:
        lines.append(f"[Featured Answer] {answer}")

    # Top organic results — include URL so LLM can fetch if needed
    for r in data.get("organic", [])[:4]:
        title   = r.get("title", "")
        snippet = r.get("snippet", "")
        url     = r.get("link", "")
        lines.append(f"[Result] {title}: {snippet} (url: {url})")

    return "\n".join(lines) if lines else "No results found."
