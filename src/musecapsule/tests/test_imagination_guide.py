import pytest
from pydantic import ValidationError

from musecapsule.agents.imagination_guide import ExplorationQuestion


@pytest.mark.parametrize("question", ["", " ", "\t\n"])
def test_exploration_question_rejects_blank_text(question):
    with pytest.raises(ValidationError):
        ExplorationQuestion(question=question)
