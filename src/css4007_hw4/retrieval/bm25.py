import math
import re
from collections import Counter

# Vocabulary normalization only: no district facts, formulas or question IDs.
ALIASES = {"residents": "population", "resident": "population", "census": "population",
           "density": "area", "covers": "area", "square": "area", "kilometres": "km",
           "kilometre": "km", "km2": "area", "schools": "school", "pupils": "pupil",
           "roads": "road", "budgets": "budget", "older": "founded", "oldest": "founded",
           "litres": "water", "megalitres": "water", "metres": "m", "price": "tariff"}
STOP = set("the a an in of and or by per for to has have is are was were which how many more less "
           "than district districts its from with what at do does on their it s".split())


def tokens(text: str) -> list[str]:
    return [ALIASES.get(w, w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.terms = [Counter(tokens(text)) for text in texts]
        self.lengths = [sum(t.values()) for t in self.terms]
        self.average = sum(self.lengths) / max(len(texts), 1) or 1
        self.df: Counter[str] = Counter()
        for terms in self.terms:
            self.df.update(terms.keys())
        self.k1, self.b = k1, b

    def score(self, query: str, index: int) -> float:
        score = 0.0
        for term in set(tokens(query)):
            count = self.terms[index][term]
            if count:
                idf = math.log(1 + (len(self.terms) - self.df[term] + 0.5) / (self.df[term] + 0.5))
                norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average)
                score += idf * count * (self.k1 + 1) / (count + norm)
        return score
