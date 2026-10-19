from typing import Any


class ToolError(Exception):
    def __init__(self, code: str, message: str, suggestions: list[str] | None = None):
        super().__init__(message)
        self.code, self.message, self.suggestions = code, message, suggestions

    def result(self) -> dict[str, Any]:
        return error(self.code, self.message, self.suggestions)


def error(code: str, message: str, suggestions: list[str] | None = None) -> dict[str, Any]:
    details: dict[str, Any] = {"code": code, "message": message}
    if suggestions is not None:
        details["suggestions"] = suggestions[:3]
    return {"ok": False, "error": details}
