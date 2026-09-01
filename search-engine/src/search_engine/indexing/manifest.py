from pydoc import doc
import uuid
from typeid import TypeID

from search_engine.indexing.index import Index

class Manifest:
    def __init__(
        self,
        version: int,
        segments: list[TypeID],
        live_documents: dict[str, uuid.UUID],
        deleted_documents: set[uuid.UUID]
    ):
        self._version: int = version
        self._segments: list[TypeID] = segments
        self._live_documents: dict[str, uuid.UUID] = live_documents
        self._deleted_documents: set[uuid.UUID] = deleted_documents

    @classmethod
    def from_index(cls, index: Index) -> "Manifest":
        return cls(
            version=1,
            segments=index.segment_ids(),
            live_documents=Manifest.build_live_documents_map(index),
            deleted_documents=index.deleted_documents()
        )

    @staticmethod
    def build_live_documents_map(index: Index) -> dict[str, uuid.UUID]:
        document_ids = index.live_documents_ids()
        live_documents = {}

        for document_id in document_ids:
            live_documents[document_id] = index.get_internal_document_id(document_id)

        return live_documents

    def to_dict(self) -> dict:
        return {
            "version": self._version,
            "segments": self.string_segment_ids(),
            "live_documents": self.string_live_documents_ids(),
            "deleted_documents": self.string_deleted_documents()
        }

    def string_segment_ids(self) -> list[str]:
        return [str(segment_id) for segment_id in self._segments]

    def string_live_documents_ids(self) -> dict[str, str]:
        live_documents = {}
        for document_id in self._live_documents:
            live_documents[document_id] = str(self._live_documents[document_id])

        return live_documents

    def segments(self) -> list[TypeID]:
        return self._segments

    def string_deleted_documents(self) -> list[str]:
        return [str(deleted_document) for deleted_document in self._deleted_documents]

    def live_documents(self) -> dict[str, uuid.UUID]:
        return dict(self._live_documents)

    def deleted_documents(self) -> set[uuid.UUID]:
        return set(self._deleted_documents)