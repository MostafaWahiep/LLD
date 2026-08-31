"""Shared test setup; production code is never modified by the tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluator import QueryEvaluator
from index import Index
from buffer import Buffer
from query_parser import Parser
from search_engine import SearchEngine
from text_analyzer import TextAnalyzer
from trie_index import TrieIndex


def make_components():
    index = Index(Buffer(TrieIndex()))
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    engine = SearchEngine(Parser(), analyzer, index, evaluator)
    return engine, index, evaluator


def make_engine():
    return make_components()[0]


def populated_engine():
    engine = make_engine()
    engine.add("doc-1", "python search search engine")
    engine.add("doc-2", "python web framework")
    engine.add("doc-3", "distributed search engine")
    return engine
