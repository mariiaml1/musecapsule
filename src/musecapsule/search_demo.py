import os
from uuid import uuid4

from musecapsule.search import search_similar_solutions


def main() -> None:
    """Run one standalone search to verify the external adapter."""
    check = search_similar_solutions(
        idea_id=uuid4(),
        query="local AI experiment tracking inspection tools",
        api_key=os.environ.get("TAVILY_API_KEY"),
    )
    print(check.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
