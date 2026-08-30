import re
from typing import Protocol


class Analyzer(Protocol):
    def analyze(self, text: str) -> list[str]:
        ...

class TextAnalyzer(Analyzer):
    def analyze(self, text: str) -> list[str]:
        return [
            match.group().lower()
            for match in re.finditer(r"\w+", text)
        ]
