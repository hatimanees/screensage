from google import genai
from google.genai import types
from .base import LLMProvider

SYSTEM_PROMPT = """You are a desktop guidance assistant. The user is stuck and needs help.

You are given a screenshot of their screen and their spoken question.

Your goal: provide clear, numbered, step-by-step instructions to solve their problem.

You have two tools available:
- web_search: use when you are not confident about the exact steps, menu names, or feature location for this specific app or version
- fetch_url: use when a search result mentions the answer but the snippet is too short — fetch the full page for detail

Rules:
- Try to answer from your own knowledge first. Only call tools if genuinely unsure.
- Be specific: use exact menu names, button labels, keyboard shortcuts.
- If a feature is not visible on screen, tell the user exactly where to navigate.
- Final answer must be plain text numbered steps only. No markdown, no bullet points.
- Max 10 steps."""

_TOOLS = [types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="web_search",
        description="Search the web for step-by-step instructions or feature locations in an app.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="Search query, e.g. 'Google Docs insert table of contents'",
                )
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="fetch_url",
        description="Fetch the full content of a URL when a search snippet lacks enough detail.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "url": types.Schema(
                    type=types.Type.STRING,
                    description="The URL to fetch.",
                )
            },
            required=["url"],
        ),
    ),
])]


class GeminiLLM(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def analyze(self, image_path: str, query: str, context: str) -> str:
        """Legacy single-shot method kept for compatibility."""
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        prompt = f"{SYSTEM_PROMPT}\n\nUser question: {query}\n\n{context}"
        response = self._client.models.generate_content(
            model=self._model,
            contents=[prompt, image_part],
        )
        return response.text.strip()

    def analyze_with_tools(
        self,
        image_path: str,
        query: str,
        tool_executor,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        """Agentic loop: LLM decides when to call tools until it is confident."""
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

        # System prompt as the first user turn
        contents: list = [
            types.Content(role="user", parts=[
                types.Part.from_text(text=SYSTEM_PROMPT),
            ]),
            types.Content(role="model", parts=[
                types.Part.from_text(text="Understood. I'm ready to help."),
            ]),
        ]

        # Inject prior turns (text only — no screenshots)
        for prior_query, prior_response in (history or []):
            contents.append(types.Content(role="user", parts=[
                types.Part.from_text(text=prior_query),
            ]))
            contents.append(types.Content(role="model", parts=[
                types.Part.from_text(text=prior_response),
            ]))

        # Current turn: question + live screenshot
        contents.append(types.Content(role="user", parts=[
            types.Part.from_text(text=query),
            image_part,
        ]))

        max_iterations = 10
        for iteration in range(max_iterations):
            print(f"\n[llm] iteration {iteration + 1} — calling model...")
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(tools=_TOOLS),
            )

            candidate_content = response.candidates[0].content
            parts = candidate_content.parts

            function_calls = [p for p in parts if p.function_call is not None]

            if not function_calls:
                answer = response.text.strip()
                print(f"\n[llm] confident — final answer:\n{answer}")
                return answer

            # Log what the model decided to call
            for part in function_calls:
                fc = part.function_call
                print(f"[llm] tool call: {fc.name}({dict(fc.args)})")

            # Append model turn
            contents.append(candidate_content)

            # Execute each tool call and collect responses
            tool_response_parts = []
            for part in function_calls:
                fc = part.function_call
                result = tool_executor.execute(fc.name, dict(fc.args))
                print(f"[tool:{fc.name}] result:\n{result}\n")
                tool_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                )

            contents.append(types.Content(role="user", parts=tool_response_parts))

        # Max iterations hit — force a final answer from whatever was gathered
        print("\n[llm] max iterations reached — forcing final answer")
        contents.append(types.Content(role="user", parts=[
            types.Part.from_text(text="Based on all the information above, give your best answer now.")
        ]))
        final = self._client.models.generate_content(
            model=self._model,
            contents=contents,
        )
        answer = final.text.strip()
        print(f"[llm] final answer:\n{answer}")
        return answer
