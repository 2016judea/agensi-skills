"""
Gemini web research with Google Search grounding.

Better than plain web search for local/trade-press/fresh-market questions: it
searches live Google and returns an answer grounded in cited sources.

Usage:
    from gemini_search import grounded
    answer, sources = grounded("Who are the active value-add multifamily buyers in <city>?")

CLI:
    python3 gemini_search.py "your question"
"""
import os
import sys

# Tried in order; override with GEMINI_SEARCH_MODELS="a,b,c" when model names change.
_MODELS = [m for m in os.environ.get("GEMINI_SEARCH_MODELS", "gemini-3.7-flash,gemini-3.1-pro-preview,gemini-3.5-flash-lite").split(",") if m]


def grounded(prompt: str, model: str | None = None) -> tuple[str, list[dict]]:
    """Return (answer_text, [{title, uri}]) using Gemini + Google Search grounding."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cfg = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )
    last_err = None
    for m in ([model] if model else _MODELS):
        try:
            resp = client.models.generate_content(model=m, contents=prompt, config=cfg)
            text = resp.text or ""
            sources = []
            for cand in resp.candidates or []:
                gm = getattr(cand, "grounding_metadata", None)
                for ch in (getattr(gm, "grounding_chunks", None) or []):
                    web = getattr(ch, "web", None)
                    if web:
                        sources.append({"title": getattr(web, "title", ""), "uri": getattr(web, "uri", "")})
            # dedupe
            seen, uniq = set(), []
            for s in sources:
                if s["uri"] not in seen:
                    seen.add(s["uri"]); uniq.append(s)
            return text, uniq
        except Exception as e:  # try next model
            last_err = e
    raise RuntimeError(f"All Gemini models failed: {last_err}")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "test"
    ans, srcs = grounded(q)
    print(ans)
    print("\n--- SOURCES ---")
    for s in srcs:
        print(f"- {s['title']}: {s['uri']}")
