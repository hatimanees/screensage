from providers.search.serper import web_search
from providers.search.fetcher import fetch_url


class ToolExecutor:
    def __init__(self, serper_api_key: str):
        self._serper_key = serper_api_key

    def execute(self, name: str, args: dict) -> str:
        if name == "web_search":
            if not self._serper_key:
                return "Web search is unavailable (SERPER_API_KEY not configured)."
            return web_search(args["query"], self._serper_key)
        if name == "fetch_url":
            return fetch_url(args["url"])
        return f"Unknown tool: {name}"
