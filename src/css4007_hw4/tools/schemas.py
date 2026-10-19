import json
from importlib.resources import files


def tool_definitions(*, vague_lookup: bool = False) -> list[dict]:
    definitions = json.loads(files("css4007_hw4.tools").joinpath("definitions.json").read_text(encoding="utf-8"))
    if vague_lookup:
        definitions[0]["function"]["description"] = "Looks things up."
    return definitions
