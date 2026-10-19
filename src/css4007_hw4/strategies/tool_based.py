from css4007_hw4.config import Config
from css4007_hw4.domain.models import Question
from css4007_hw4.llm.client import Client
from css4007_hw4.llm.prompts import messages
from css4007_hw4.orchestration.agent_loop import EventSink, run_loop
from css4007_hw4.tools.registry import Tool
from css4007_hw4.tools.schemas import tool_definitions


def tool_based(client: Client, question: Question, config: Config, registry: dict[str, Tool],
               *, vague_lookup: bool = False, sink: EventSink | None = None) -> dict:
    return run_loop(client, messages(question.text, "S3"), config,
                    tool_definitions(vague_lookup=vague_lookup), registry, sink=sink)
