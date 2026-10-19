from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, localcontext

from css4007_hw4.evaluation.parser import parse_answer


def vote(samples: list[dict]) -> tuple[int | None, list[dict]]:
    """Joint name/number votes; fixed six decimal places, earliest-sample ties."""
    votes = []
    for index, sample in enumerate(samples):
        answer = parse_answer(sample.get("final_text")) if sample.get("status") == "completed" else None
        if answer:
            with localcontext() as context:
                context.prec = 64
                number = answer.value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            votes.append({"sample": index, "name": answer.name, "number": str(number.copy_abs() if number == 0 else number)})
    if not votes:
        return None, []
    counts = Counter((v["name"], v["number"]) for v in votes)
    largest = max(counts.values())
    winner = next(v["sample"] for v in votes if counts[(v["name"], v["number"])] == largest)
    return winner, votes
