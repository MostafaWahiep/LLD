from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from search_engine.documents import Document
from search_engine.indexing.posting import FrozenPosting
from search_engine.indexing.segment_reader import SegmentReads
from search_engine.indexing.trie import TrieIndex

class Segment(SegmentReads):
    def __init__(self, postings: Mapping[str, FrozenPosting], documents, trie_index):
        self._postings: Mapping[str, FrozenPosting] = MappingProxyType(dict(postings))
        self._documents: dict[str, Document] = documents
        self._trie_index: TrieIndex = trie_index
