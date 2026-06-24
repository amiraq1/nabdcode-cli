from duckduckgo_search import DDGS
from typing import List, Dict
import textwrap

def search_internet(
    query: str,
    max_results: int = 5,
    snippet_length: int = 300,
) -> str:
    """
    Search the internet using DuckDuckGo.

    Returns:
        Formatted text optimized for LLM consumption.
    """

    if not query.strip():
        return "[SYSTEM: ERROR]\nEmpty search query."

    try:
        unique_urls = set()
        collected_results: List[Dict] = []

        with DDGS(timeout=15) as ddgs:
            results = ddgs.text(
                keywords=query,
                max_results=max_results
            )

            for result in results:
                url = result.get("href", "").strip()

                if not url or url in unique_urls:
                    continue

                unique_urls.add(url)

                title = result.get("title", "No Title").strip()

                snippet = (
                    result.get("body", "")
                    .replace("\n", " ")
                    .strip()
                )

                if len(snippet) > snippet_length:
                    snippet = snippet[:snippet_length] + "..."

                collected_results.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    }
                )

        if not collected_results:
            return (
                "[SYSTEM: SEARCH]\n"
                f"No results found for: {query}"
            )

        output = [
            "[SYSTEM: SEARCH RESULTS]",
            f"Query: {query}",
            f"Results Found: {len(collected_results)}",
            ""
        ]

        for idx, item in enumerate(collected_results, start=1):
            output.extend([
                f"--- Result {idx} ---",
                f"Title: {item['title']}",
                f"URL: {item['url']}",
                f"Summary: {item['snippet']}",
                ""
            ])

        return "\n".join(output)

    except Exception as e:
        return (
            "[SYSTEM: SEARCH ERROR]\n"
            f"Query: {query}\n"
            f"Error: {type(e).__name__}: {e}"
        )
