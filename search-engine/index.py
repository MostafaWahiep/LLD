from posting import Posting
from trie_index import TrieIndex

class InvertedIndex:
    def __init__(self, trie_index: TrieIndex):
        self._postings: dict[str, Posting] = {}
        self._documents: dict[str, str] = {}
        self._trie_index: TrieIndex = trie_index

    def add(
        self,
        document_id: str,
        text: str,
        terms: list[str],
    ) -> None:
        if document_id in self._documents:
            raise ValueError(f"Duplicate document ID: {document_id}")

        self._documents[document_id] = text

        for idx, term in enumerate(terms):
            lower_term: str = term.lower()
            if lower_term not in self._postings:
                self._trie_index.prefix_term(lower_term)
            posting: Posting = self._postings.setdefault(lower_term, Posting(lower_term))
            posting.add(document_id, idx)

    def postings(self, term: str) -> set[str]:
        return self.get_posting(term).document_ids()

    def prefix_search(self, prefix: str) -> set[str]:
        terms = self._trie_index.terms_with_prefix(prefix)

        result = set()
        for term in terms:
            result.update(self.postings(term))

        return result

    def get_posting(self, term: str) -> Posting:
        lower_term = term.lower()
        return self._postings.get(lower_term, Posting(lower_term))

    def document_ids(self) -> set[str]:
        return set(self._documents)
