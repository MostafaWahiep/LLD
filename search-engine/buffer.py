from dataclasses import dataclass
from posting import MutablePosting
from trie_index import TrieIndex
from document import Document
from segment import Segment
from segment_protocol import SegmentReads

class Buffer(SegmentReads):
    def __init__(self, trie_index: TrieIndex):
        self._postings: dict[str, MutablePosting] = {}
        self._documents: dict[str, Document] = {}
        self._trie_index: TrieIndex = trie_index
    
    def add(
        self,
        document: Document,
        terms: list[str],
    ) -> None:
        if document.external_id in self._documents:
            raise ValueError(f"Duplicate document ID: {document.external_id}")

        self._documents[document.internal_id()] = document

        for idx, term in enumerate(terms):
            lower_term: str = term.lower()
            if lower_term not in self._postings:
                self._trie_index.prefix_term(lower_term)
            posting = self._postings.setdefault(lower_term, MutablePosting(lower_term))
            posting.add(document.document_ref, idx)

    def freeze(self) -> Segment:
        segment = Segment(
            postings={term: posting.freeze() for term, posting in self._postings.items()},
            documents=self._documents,
            trie_index=self._trie_index
        )

        self._postings = {}
        self._documents = {}
        self._trie_index = TrieIndex()
        return segment
