from css4007_hw4.config import Config
from css4007_hw4.domain.models import Question
from css4007_hw4.llm.client import Client
from css4007_hw4.llm.prompts import messages
from css4007_hw4.orchestration.agent_loop import EventSink, run_loop


def direct(client: Client, question: Question, corpus: str, config: Config, *, sink: EventSink | None = None) -> dict:
    return run_loop(client, messages(question.text, "S1", corpus), config, max_calls=1, sink=sink)
