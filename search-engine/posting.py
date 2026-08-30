from collections import defaultdict

class Posting:
    def __init__(self, term: str):
        self.term = term
        self._term_frequencies: dict[str, int] = defaultdict(int)

    def add(self, document_id: str) -> None:
        self._term_frequencies[document_id] += 1

    def document_ids(self) -> set[str]:
        return set(self._term_frequencies)

    def frequency(self, document_id: str) -> int:
        return self._term_frequencies.get(document_id, 0)

    def document_frequency(self) -> int:
        return len(self._term_frequencies)
