from unittest.mock import patch
from uuid import uuid4
import json
from urllib.error import HTTPError

from musecapsule.search import search_similar_solutions


def test_search_reports_unavailable_without_key():
    idea_id = uuid4()

    with patch("musecapsule.search.urlopen") as mocked_request:
        check = search_similar_solutions(
            idea_id=idea_id,
            query="local AI experiment inspection tools",
            api_key=None,
        )

    mocked_request.assert_not_called()
    assert check.idea_id == idea_id
    assert check.status == "unavailable"
    assert check.results == []
    assert check.reason == "Tavily API key is not configured."

def test_search_returns_results_with_sources():
    idea_id = uuid4()
    provider_response = {
        "results": [
            {
                "title": "Example Experiment Tool",
                "url": "https://example.com/experiment-tool",
                "content": "A tool for organizing local AI experiments.",
            }
        ]
    }

    with patch("musecapsule.search.urlopen") as mocked_request:
        response = mocked_request.return_value.__enter__.return_value
        response.read.return_value = json.dumps(provider_response).encode(
            "utf-8"
        )

        check = search_similar_solutions(
            idea_id=idea_id,
            query="local AI experiment tools",
            api_key="test-key",
        )

    mocked_request.assert_called_once()
    request = mocked_request.call_args.args[0]
    payload = json.loads(request.data)

    assert request.full_url == "https://api.tavily.com/search"
    assert request.get_method() == "POST"
    assert payload["query"] == "local AI experiment tools"
    assert payload["max_results"] == 3
    assert payload["search_depth"] == "basic"
    assert payload["include_answer"] is False
    assert mocked_request.call_args.kwargs["timeout"] == 20

    assert check.idea_id == idea_id
    assert check.status == "completed"
    assert check.reason is None
    assert len(check.results) == 1
    assert check.results[0].title == "Example Experiment Tool"
    assert check.results[0].url == "https://example.com/experiment-tool"
    assert check.results[0].snippet == (
        "A tool for organizing local AI experiments."
    )


def test_search_reports_provider_failure_without_retry():
    with patch(
        "musecapsule.search.urlopen",
        side_effect=HTTPError(
            url="https://api.tavily.com/search",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=None,
        ),
    ) as mocked_request:
        check = search_similar_solutions(
            idea_id=uuid4(),
            query="local AI experiment tools",
            api_key="test-key",
        )

    mocked_request.assert_called_once()
    assert check.status == "unavailable"
    assert check.results == []
    assert check.reason == "Search provider returned HTTP 429."
