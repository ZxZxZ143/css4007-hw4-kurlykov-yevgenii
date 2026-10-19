from copy import deepcopy

from css4007_hw4.llm.client import ModelResponse


class FakeClient:
    def __init__(self, messages):
        self.responses = iter(messages)
        self.calls = []

    def complete(self, messages, tools, config):
        self.calls.append(deepcopy({"messages": messages, "tools": tools, "config": config.to_dict()}))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, ModelResponse):
            return response
        return ModelResponse(response, {"prompt_tokens": 100, "completion_tokens": 20,
                                       "prompt_tokens_details": {"cached_tokens": 0}}, config.model)


def tool_call(call_id="c1", name="calculate", arguments='{"mode":"evaluate","expression":"2+3"}'):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


def assistant(*calls):
    return {"role": "assistant", "content": None, "tool_calls": list(calls)}


def final(text="ANSWER: yes | 5"):
    return {"role": "assistant", "content": text}
