from search_engine.analysis import TextAnalyzer
from search_engine.engine import SearchEngine
from search_engine.indexing.index import Index
from search_engine.querying.evaluator import QueryEvaluator
from search_engine.querying.parser import Parser
from search_engine.indexing.codec import ManifestCodec, SegmentCodec
from search_engine.indexing.trie import TrieIndex

from pathlib import Path
import sys

def make_components() -> tuple[SearchEngine, Index, QueryEvaluator]:
    path = Path(sys.argv[0]).resolve().parent
    index = Index()
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    engine = SearchEngine(path, Parser(), analyzer, index, evaluator)
    return engine, index, evaluator


def make_engine() -> SearchEngine:
    return make_components()[0]

def _build_engine(path: Path, index: Index):
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    engine = SearchEngine(path, Parser(), analyzer, index, evaluator)
    return engine

def open_engine(
        path: Path,
        trie_factory: TrieIndex=TrieIndex
) -> SearchEngine:
    manifest = ManifestCodec.read(path)

    segments = [
        SegmentCodec.read(
            path / f"{segment_id}.json",
            trie_factory=trie_factory,
        )
        for segment_id in manifest.segments()
    ]

    index = Index.restore(
        segments,
        manifest.live_documents(),
        manifest.deleted_documents(),
        trie_factory
    )

    return _build_engine(path, index)
