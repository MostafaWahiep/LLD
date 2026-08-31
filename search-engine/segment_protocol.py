from typing import Mapping, Protocol, runtime_checkable
from document_ref import DocumentRef
from posting import Posting, FrozenPosting, StoredPosting
from document import Document
from trie_index import TrieIndex

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

class SegmentReads(SegmentProtocol):
    _postings: Mapping[str, StoredPosting]
    _documents: dict[str, Document]
    _trie_index: TrieIndex

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

    def intenral_document_ids(self) -> set[str]:
        return set(self._documents)
