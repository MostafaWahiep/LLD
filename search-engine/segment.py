from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from posting import FrozenPosting
from trie_index import TrieIndex
from document import Document
from segment_protocol import SegmentReads

class Segment(SegmentReads):
    def __init__(self, postings: Mapping[str, FrozenPosting], documents, trie_index):
        self._postings: Mapping[str, FrozenPosting] = MappingProxyType(dict(postings))
        self._documents: dict[str, Document] = documents
        self._trie_index: TrieIndex = trie_index
