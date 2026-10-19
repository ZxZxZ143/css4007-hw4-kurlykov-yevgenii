import ast
from pathlib import Path

import pytest

from css4007_hw4.tools.calculate import calculate


def test_required_product():
    assert calculate(mode="evaluate", expression="48317 * 1.0947")["value"] == pytest.approx(52892.6199)


@pytest.mark.parametrize("expression", ["__import__('os').system('echo hi')", "(1).__class__", "9**9**9",
                                        "x+1", "[1]", "True", "1j", "1//2", "2%1", "lambda:1"])
def test_unsupported(expression):
    assert calculate(mode="evaluate", expression=expression)["error"]["code"] == "UNSUPPORTED_EXPRESSION"


@pytest.mark.parametrize("expression", ["1/0", "1/(2-2)"])
def test_zero(expression):
    assert calculate(mode="evaluate", expression=expression)["error"]["code"] == "DIVISION_BY_ZERO"


@pytest.mark.parametrize("expression", ["1" * 513, "1e309", "1e15+1", "1e15*2/2", "1e-300/1e-320",
                                        "-" * 17 + "1", "+".join(["1"] * 50), "(" + "+".join(["(1+1+1+1)"] * 12) + ")"])
def test_limits(expression):
    assert calculate(mode="evaluate", expression=expression)["error"]["code"] == "LIMIT_EXCEEDED"


def test_valid_math_and_precision():
    assert calculate(mode="evaluate", expression=" -(1.5e2 + +50) / 4 ")["value"] == -50
    assert calculate(mode="evaluate", expression="37203 / 758.6 - 44675 / 921.4")["value"] == pytest.approx(0.5556561156405735)
    assert calculate(mode="evaluate", expression="1e15")["value"] == 1e15


def test_syntax():
    assert calculate(mode="evaluate", expression="(1+")["error"]["code"] == "INVALID_EXPRESSION"


@pytest.mark.parametrize("args", [{}, {"mode": "wrong"}, {"mode": "evaluate"},
                                  {"mode": "evaluate", "expression": " "}, {"mode": "evaluate", "expression": 5},
                                  {"mode": "evaluate", "expression": "1", "scale": "one"},
                                  {"mode": "evaluate", "expression": "1", "value": 1},
                                  {"mode": "convert", "value": 1},
                                  {"mode": "convert", "value": 1, "from_unit": "m", "to_unit": "m", "expression": "1"}])
def test_arguments(args):
    assert calculate(**args)["error"]["code"] == "INVALID_ARGUMENTS"


def test_no_dynamic_execution():
    root = Path(__file__).resolve().parents[1] / "src/css4007_hw4"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"eval", "exec"}
                       for n in ast.walk(tree))
