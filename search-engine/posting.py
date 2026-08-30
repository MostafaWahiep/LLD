from collections import defaultdict

class Posting:
    def __init__(self, term: str):
        self.term = term
        self._positions: dict[str, set[int]] = defaultdict(set)

    def add(self, document_id: str, index: int) -> None:
        self._positions[document_id].add(index)

    def document_ids(self) -> set[str]:
        return set(self._positions)

    def frequency(self, document_id: str) -> int:
        return len(self._positions.get(document_id, []))

    def positions(self, document_id: str) -> set[int]:
        return set(self._positions.get(document_id, set()))

    def document_frequency(self) -> int:
        return len(self._positions)
