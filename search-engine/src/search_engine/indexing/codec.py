from search_engine.indexing.segment import Segment
from search_engine.documents import Document, DocumentRef
from search_engine.indexing.manifest import Manifest
from search_engine.indexing.posting import FrozenPosting, MutablePosting
from search_engine.indexing.trie import TrieIndex

import json
from pathlib import Path
from uuid import UUID
from typing import Mapping, Any
from typeid import TypeID
import os
import tempfile

def write_json_atomically(destination: Path, data: Any) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            json.dump(
                data,
                temporary_file,
                indent=2,
                sort_keys=True,
            )

            temporary_file.flush()

            os.fsync(temporary_file.fileno())
    
        os.replace(temporary_path, destination)

        fsync_directory(destination.parent)

    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def fsync_directory(directory: Path) -> None:
    directory_fd = os.open(directory, os.O_RDONLY)

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)

"""
data = {
    "documents": [
        {
            "document_ref" : {
                "internal_id": "uuid",
                "external_id": "doc1"
            }
            "text": "This is the text of the document."
        },
        {
            "document_ref" : {
                "internal_id": "uuid",
                "external_id": "doc1"
            }
            "text": "This is the text of the document."
        }
    ],
    "postings": {
        "term1": {
            "uuid1": [0, 5, 10],
        },
        "term2": {
            "uuid1": [3, 8],
            "uuid2": [1, 4]
        }
    }
}
"""
class SegmentCodec:
    @staticmethod
    def write(segment: Segment, path: Path) -> None:
        segment_path = path / f"{segment.id()}.json"

        if segment_path.is_file():
            return

        if segment_path.exists():
            raise ValueError(
                f"Segment path exists but is not a file: {segment_path}"
            )

        data = SegmentCodec._serialize_segment(segment)
        write_json_atomically(segment_path, data)

    @staticmethod
    def read(path: Path, trie_factory: TrieIndex) -> Segment:
        with open(path, "r") as f:
            json_string = f.read()
        data = json.loads(json_string)
        segment_id = path.stem
        return SegmentCodec._build_segment(data, segment_id, trie_factory)

    @staticmethod
    def _serialize_segment(segment: Segment) -> dict:
        return {
            "documents": SegmentCodec._serialize_documents(segment),
            "postings": SegmentCodec._serialize_postings(segment)
        }

    @staticmethod
    def _serialize_documents(segment: Segment) -> list:
        return [
            segment.get_document(doc_id).to_dict()
            for doc_id in segment.documents()
        ]

    @staticmethod
    def _serialize_postings(segment: Segment) -> dict:
        return {
            term: SegmentCodec._serialize_posting(segment.get_posting(term))
            for term in segment.terms()
        }

    @staticmethod
    def _serialize_posting(posting: FrozenPosting) -> dict:
        return {
            str(ref.internal_id): sorted(posting.positions(ref))
            for ref in posting.document_refs()
        }

    @staticmethod
    def _build_segment(data: dict, segment_id: str, trie_factory) -> Segment:
        documents, postings = SegmentCodec._deserialize_segment(data)

        trie_index: TrieIndex = trie_factory()
        for term in postings:
            trie_index.prefix_term(term)

        return Segment(
            postings=postings,
            documents=documents,
            trie_index=trie_index,
            type_id=TypeID.from_string(segment_id)
        )

    @staticmethod
    def _deserialize_segment(data: dict) -> tuple:
        documents = SegmentCodec._deserialize_documents(data["documents"])
        postings = SegmentCodec._deserialize_postings(data["postings"], documents)
        return documents, postings

    @staticmethod
    def _deserialize_documents(data: list) -> dict[UUID, Document]:
        refs_by_id: dict[UUID, DocumentRef] = {}

        for document_data in data:
            document = Document.from_dict(document_data)
            refs_by_id[document.internal_id()] = document

        return refs_by_id

    @staticmethod
    def _deserialize_postings(data: dict, documents: dict[UUID, Document]) -> dict:
        postings: Mapping[str, FrozenPosting] = {}

        for term in data:
            posting = MutablePosting(term)
            postions_dict = data[term]

            for document_id in postions_dict:
                document_ref = documents[UUID(document_id)].document_ref
                positions = set(postions_dict[document_id])
                posting.add_positions(document_ref, positions)

            postings[term] = posting.freeze()

        return postings

"""
{
  "version": 1,
  "generation": 7,
  "segments": [
    "segment-4.json",
    "segment-6.json"
  ],
  "live_documents": {
    "doc-1": "1f16e9f5-..."
  },
  "deleted_documents": [
    "77d2ee15-..."
  ]
}
"""
class ManifestCodec:
    @staticmethod
    def write(manifest: Manifest, path: Path) -> None:
        data = manifest.to_dict()
        manifest_path = path / ("manifest.json")

        write_json_atomically(manifest_path, data)
        
    @staticmethod
    def read(path: Path) -> Manifest:
        manifest_path = path / ("manifest.json")
        with open(manifest_path, "r") as f:
            json_string = f.read()
        data = json.loads(json_string)
        return ManifestCodec._deserialize_manifest(data)

    @staticmethod
    def _deserialize_manifest(data: dict) -> Manifest:
        return Manifest(
            version=data["version"],
            segments=data["segments"],
            live_documents=ManifestCodec._deserialize_live_documents(data["live_documents"]),
            deleted_documents=ManifestCodec._deserialize_documents(data["deleted_documents"])
        )

    @staticmethod
    def _deserialize_live_documents(live_documents: dict[str, str]) -> dict[str, UUID]:
        for live_document in live_documents:
            live_documents[live_document] = UUID(live_documents[live_document])
        return live_documents

    @staticmethod
    def _deserialize_documents(deleted_documents: list[str]) -> set[UUID]:
        return set([
            UUID(deleted_document)
            for deleted_document in deleted_documents
        ])
