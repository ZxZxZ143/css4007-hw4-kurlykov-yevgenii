import ast
import operator
from typing import Any

from css4007_hw4.domain.errors import ToolError, error
from css4007_hw4.tools.units import convert
from css4007_hw4.tools.validation import checked_number, fields

OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult,
           ast.Div, ast.UAdd, ast.USub)


def arithmetic(expression: str) -> float:
    if not isinstance(expression, str) or not expression.strip():
        raise ToolError("INVALID_ARGUMENTS", "expression must be a nonblank string.")
    if len(expression) > 512:
        raise ToolError("LIMIT_EXCEEDED", "Expression length exceeds 512 characters.")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise ToolError("INVALID_EXPRESSION", "Malformed arithmetic expression.") from exc
    except (MemoryError, RecursionError) as exc:
        raise ToolError("LIMIT_EXCEEDED", "Parser complexity limit exceeded.") from exc
    stack = [(tree, 1)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > 128 or depth > 16:
            raise ToolError("LIMIT_EXCEEDED", "AST exceeds 128 nodes or depth 16 (root depth 1).")
        if not isinstance(node, ALLOWED) or (isinstance(node, ast.Constant) and type(node.value) not in (int, float)):
            raise ToolError("UNSUPPORTED_EXPRESSION", "Only real literals, parentheses, unary +/- and + - * / are allowed.")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant):
            return checked_number(node.value)
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            return checked_number(-value if isinstance(node.op, ast.USub) else value)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ToolError("DIVISION_BY_ZERO", "Cannot divide by zero.")
            return checked_number(OPERATORS[type(node.op)](left, right))
        raise ToolError("UNSUPPORTED_EXPRESSION", "Unsupported expression node.")

    return visit(tree)


def calculate(**arguments: Any) -> dict[str, Any]:
    try:
        mode = arguments.get("mode")
        if mode == "evaluate":
            fields(arguments, {"mode", "expression"}, set())
            value, unit = arithmetic(arguments["expression"]), None
        elif mode == "convert":
            fields(arguments, {"mode", "value", "from_unit", "to_unit"}, {"scale"})
            value = convert(arguments["value"], arguments["from_unit"], arguments["to_unit"], arguments.get("scale", "one"))
            unit = arguments["to_unit"]
        else:
            raise ToolError("INVALID_ARGUMENTS", "mode must be evaluate or convert.")
        return {"ok": True, "mode": mode, "value": value, "unit": unit}
    except ToolError as exc:
        return exc.result()
    except (OverflowError, RecursionError, MemoryError):
        return error("LIMIT_EXCEEDED", "Numeric or computational limit exceeded.")
    except Exception:
        return error("INTERNAL_ERROR", "Calculation could not complete.")
