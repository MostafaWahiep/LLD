from posting import Posting


class InvertedIndex:
    def __init__(self):
        self._postings: dict[str, Posting] = {}
        self._documents: dict[str, str] = {}

    def add(
        self,
        document_id: str,
        text: str,
        terms: list[str],
    ) -> None:
        if document_id in self._documents:
            raise ValueError(f"Duplicate document ID: {document_id}")

        self._documents[document_id] = text

        for term in terms:
            lower_term: str = term.lower()
            posting: Posting = self._postings.setdefault(lower_term, Posting(lower_term))
            posting.add(document_id)

    def postings(self, term: str) -> set[str]:
        return self.get_posting(term).document_ids()

    def get_posting(self, term: str) -> Posting:
        lower_term = term.lower()
        return self._postings.get(lower_term, Posting(lower_term))

    def document_ids(self) -> set[str]:
        return set(self._documents)
