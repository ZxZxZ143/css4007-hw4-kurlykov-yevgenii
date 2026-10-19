from time import perf_counter

from css4007_hw4.config import Config
from css4007_hw4.domain.models import Question
from css4007_hw4.evaluation.voting import vote
from css4007_hw4.llm.client import Client
from css4007_hw4.llm.prompts import messages
from css4007_hw4.orchestration.agent_loop import EventSink, run_loop


def self_consistency(client: Client, question: Question, corpus: str, config: Config,
                     *, sink: EventSink | None = None) -> dict:
    started = perf_counter()
    samples = []
    for index in range(config.samples):
        def sample_sink(event: dict, sample_index: int = index) -> None:
            if sink:
                sink({**event, "sample": sample_index})
        samples.append(run_loop(client, messages(question.text, "S2", corpus), config, max_calls=1, sink=sample_sink))
    winner, votes = vote(samples)
    selected = samples[winner] if winner is not None else {}
    return {"status": "completed" if winner is not None else "unanswered",
            "reason": None if winner is not None else "no_valid_votes",
            "answer": selected.get("answer"), "final_text": selected.get("final_text"),
            "samples": samples, "votes": votes, "winning_sample": winner,
            "requests": [request for sample in samples for request in sample["requests"]],
            "tool_events": [event for sample in samples for event in sample["tool_events"]],
            "elapsed_seconds": perf_counter() - started}
