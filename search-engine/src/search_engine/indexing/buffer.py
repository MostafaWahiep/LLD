from search_engine.documents import Document
from search_engine.indexing.posting import MutablePosting
from search_engine.indexing.segment import Segment
from search_engine.indexing.segment_reader import SegmentReads
from search_engine.indexing.trie import TrieIndex
from uuid import UUID

from typing import Callable

class Buffer(SegmentReads):
    def __init__(self, trie_factory: Callable[[], TrieIndex] = TrieIndex):
        self._trie_factory = trie_factory
        self._postings: dict[str, MutablePosting] = {}
        self._documents: dict[UUID, Document] = {}
        self._trie_index = self._trie_factory()
    
    def add(
        self,
        document: Document,
        terms: list[str],
    ) -> None:
        if document.internal_id() in self._documents:
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
        self._trie_index = self._trie_factory()
        return segment
