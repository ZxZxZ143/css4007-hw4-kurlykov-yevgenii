from decimal import Decimal, ROUND_HALF_UP, localcontext

from css4007_hw4.evaluation.parser import parse_answer


def score(execution: dict, reference: dict) -> dict:
    answer = parse_answer(execution.get("final_text")) if execution.get("status") == "completed" else None
    if answer is None:
        return {"correct": False, "unanswered": True, "category": execution.get("reason") or "format_error"}
    decimals = reference["decimals"]
    if type(decimals) is not int or not 0 <= decimals <= 12:
        raise ValueError("Reference decimals must be an integer in [0,12].")
    quantum = Decimal(1).scaleb(-decimals)
    with localcontext() as context:
        context.prec = 64
        predicted = answer.value.quantize(quantum, rounding=ROUND_HALF_UP)
        expected = Decimal(str(reference["value"])).quantize(quantum, rounding=ROUND_HALF_UP)
        delta = abs(predicted - expected)
    name_ok = answer.name == reference["answer"]
    number_ok = delta <= quantum
    category = "correct" if name_ok and number_ok else ("name_and_numeric" if not name_ok and not number_ok
                                                     else "name_mismatch" if not name_ok else "numeric_mismatch")
    return {"correct": name_ok and number_ok, "unanswered": False, "category": category,
            "name_matches": name_ok, "numeric_matches": number_ok, "rounded_prediction": str(predicted),
            "rounded_reference": str(expected), "absolute_difference": str(delta), "tolerance": str(quantum)}
