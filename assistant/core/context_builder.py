def build_context(query: str, intent: str | None, knowledge: dict) -> str:
    context = ""
    if intent and intent in knowledge:
        context += f"Relevant info: {knowledge[intent]['hint']}\n"
    return context
