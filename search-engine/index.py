from posting import MutablePosting, Posting, StoredPosting
from trie_index import TrieIndex
from segment import Segment
from buffer import Buffer
from document import Document
from document_ref import DocumentRef
import uuid

class Index:
    def __init__(self, buffer):
        self._segments: list[Segment] = []
        self._buffer: Buffer = buffer
        self._live_documents: dict[str, DocumentRef] = {}
        self._deleted_documents: set[uuid.UUID] = set()
        
    def add(
        self,
        document_id: str,
        text: str,
        terms: list[str],
    ) -> None:
        if document_id in self._live_documents:
            raise ValueError(f"Duplicate document ID: {document_id}")

        document_ref = DocumentRef(
            internal_id=uuid.uuid4(),
            external_id=document_id
        )

        document = Document(
            document_ref=document_ref,
            text=text
        )

        self._live_documents[document_id] = document_ref
        self._buffer.add(document, terms)

    def postings(self, term: str) -> set[DocumentRef]:
        document_refs = self._buffer.document_refs(term)
        for segment in self._segments:
            document_refs.update(segment.document_refs(term))

        return self._filter_deleted_docs(document_refs)

    def prefix_search(self, prefix: str) -> set[DocumentRef]:
        document_refs = self._buffer.prefix_search(prefix)
        for segment in self._segments:
            document_refs.update(segment.prefix_search(prefix))

        return self._filter_deleted_docs(document_refs)

    def get_posting(self, term: str) -> MutablePosting:
        lower_term = term.lower()
        postings: list[Posting] = [self._buffer.get_posting(lower_term)]
        for segment in self._segments:
            postings.append(segment.get_posting(lower_term))

        return self._merge_postings(lower_term, postings)

    def external_document_ids(self) -> set[str]:
        return set(self._live_documents)
    
    def document_refs(self) -> set[DocumentRef]:
        return set(self._live_documents.values())

    def delete_document(self, external_id: str):
        if external_id not in self._live_documents:
            raise ValueError(f"Document {external_id} does not exist to be deleted")

        internal_key = self._live_documents[external_id].internal_id
        self._deleted_documents.add(internal_key)
        self._live_documents.pop(external_id)

    def flush(self) -> None:
        segment: Segment = self._buffer.freeze()
        self._segments.append(segment)

    def merge_segments(self) -> None:
        if len(self._segments) < 2:
            return
        
        postings: dict[str, MutablePosting] = {}
        documents: dict[uuid.UUID, Document] = {}
        trie_index: TrieIndex = TrieIndex()
        to_be_cleaned_docs: set[uuid.UUID] = set()
        terms: set[str] = set()

        for segment in self._segments:
            for posting in segment._postings.values():
                term = posting.term
                terms.add(term)
                if posting.term not in postings:
                    postings[term] = MutablePosting(term)
                for document_ref in posting.document_refs():
                    if document_ref.internal_id in self._deleted_documents:
                        continue
                    postings[term].add_positions(
                            document_ref,
                            posting.positions(document_ref),
                        )

                if postings[term].document_frequency() == 0:
                    postings.pop(term)

            for document_id in segment._documents:
                if document_id in self._deleted_documents:
                    to_be_cleaned_docs.add(document_id)
                    continue

                documents[document_id] = segment._documents[document_id]

            trie_index.merge(segment._trie_index)

        deleted_terms = terms.difference(postings)
        trie_index.delete_terms(deleted_terms)

        frozen_postings = {
            term: posting.freeze()
            for term, posting in postings.items()
        }

        new_segment = Segment(frozen_postings, documents, trie_index)
        remaining_deleted = self._deleted_documents - to_be_cleaned_docs

        self._segments = [new_segment]
        self._deleted_documents = remaining_deleted

    def _merge_postings(self, term: str, postings: list[Posting]) -> MutablePosting:
        merged_posting = MutablePosting(term)

        for posting in postings:
            for document_ref in posting.document_refs():
                if document_ref.internal_id in self._deleted_documents:
                    continue
                merged_posting.add_positions(document_ref, posting.positions(document_ref))

        return merged_posting

    def _filter_deleted_docs(self, document_refs: set[DocumentRef]) -> set[DocumentRef]:
        return {
            ref for ref in document_refs 
            if ref.internal_id not in self._deleted_documents
        }
