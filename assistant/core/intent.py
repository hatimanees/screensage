INTENT_MAP = {
    "page number": "word_page_number",
    "coupon": "coupon_issue",
    "refund": "refund_flow",
    "copy": "copy_paste",
    "paste": "copy_paste",
    "save": "save_file",
    "print": "print_document",
    "zoom": "zoom_in",
    "find": "find_text",
    "search": "find_text",
}


def detect_intent(query: str) -> str | None:
    q = query.lower()
    for key, intent in INTENT_MAP.items():
        if key in q:
            return intent
    return None
