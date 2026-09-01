from typing import Mapping, Protocol, runtime_checkable
from search_engine.documents import Document, DocumentRef
from search_engine.indexing.posting import FrozenPosting, Posting, StoredPosting
from search_engine.indexing.trie import TrieIndex

from uuid import UUID

@runtime_checkable
class SegmentProtocol(Protocol):
    def document_refs(self, term: str) -> set[DocumentRef]:
        ...
    
    def prefix_search(self, prefix: str) -> set[DocumentRef]:
        ...

    def get_posting(self, term: str) -> Posting:
        ...

    def external_document_ids(self) -> set[str]:
        ...

    def intenral_document_ids(self) -> set[str]:
        ...

    def terms(self) -> set[str]:
        ...

    def documents(self) -> set[Document]:
        ...

    def get_document(self, document_id: str) -> Document:
        ...

class SegmentReads(SegmentProtocol):
    _postings: Mapping[str, StoredPosting]
    _documents: dict[UUID, Document]
    _trie_index: TrieIndex
    _id: str

    def document_refs(self, term: str) -> set[DocumentRef]:
        return self.get_posting(term).document_refs()

    def prefix_search(self, prefix: str) -> set[DocumentRef]:
        terms = self._trie_index.terms_with_prefix(prefix)

        result = set()
        for term in terms:
            result.update(self.document_refs(term))

        return result

    def get_posting(self, term: str) -> Posting:
        lower_term = term.lower()
        posting = self._postings.get(lower_term)
        if posting is None:
            posting = FrozenPosting(lower_term)
        return posting.view()

    def external_document_ids(self) -> set[str]:
        return set([doc.external_id() for doc in self._documents.values()])

    def intenral_document_ids(self) -> set[UUID]:
        return set(self._documents)

    def terms(self) -> set[str]:
        return set(self._postings)

    def documents(self) -> set[UUID]:
        return set(self._documents)

    def get_document(self, document_id: UUID) -> Document:
        return self._documents.get(document_id)