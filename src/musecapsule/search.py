import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError

from musecapsule.models import ExternalCheck, SimilarSolution


class TavilyResult(BaseModel):
    """The required fields of one provider search result."""

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    content: str = Field(min_length=1)


class TavilyResponse(BaseModel):
    """The provider response fields consumed by the application."""

    results: list[TavilyResult]


def search_similar_solutions(
    *,
    idea_id: UUID,
    query: str,
    api_key: str | None,
) -> ExternalCheck:
    """Run one bounded search and record its outcome.

    Return an unavailable outcome for missing configuration, transport
    failures or invalid provider responses. Do not retry automatically.

    Raises:
        ValueError: If the query is blank.
    """
    query = query.strip()
    if not query:
        raise ValueError("Search query must not be blank.")

    def unavailable(reason: str) -> ExternalCheck:
        return ExternalCheck(
            idea_id=idea_id,
            status="unavailable",
            query=query,
            reason=reason,
        )

    if not api_key or not api_key.strip():
        return unavailable("Tavily API key is not configured.")

    body = json.dumps(
        {
            "query": query,
            "search_depth": "basic",
            "max_results": 3,
            "include_answer": False,
            "include_raw_content": False,
            "auto_parameters": False,
        }
    ).encode("utf-8")

    request = Request(
        "https://api.tavily.com/search",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            raw_response = response.read()

    except HTTPError as error:
        return unavailable(f"Search provider returned HTTP {error.code}.")
    except (URLError, TimeoutError, OSError):
        return unavailable("Search request could not be completed.")

    try:
        parsed = TavilyResponse.model_validate_json(raw_response)

        results = [
            SimilarSolution(
                title=item.title,
                url=item.url,
                snippet=item.content,
            )
            for item in parsed.results[:3]
        ]
    except ValidationError:
        return unavailable("Search provider returned an invalid response.")

    return ExternalCheck(
        idea_id=idea_id,
        status="completed",
        query=query,
        results=results,
    )
