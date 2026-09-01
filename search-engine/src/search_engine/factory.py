from search_engine.analysis import TextAnalyzer
from search_engine.engine import SearchEngine
from search_engine.indexing.index import Index
from search_engine.querying.evaluator import QueryEvaluator
from search_engine.querying.parser import Parser


def make_components() -> tuple[SearchEngine, Index, QueryEvaluator]:
    index = Index()
    analyzer = TextAnalyzer()
    evaluator = QueryEvaluator(index, analyzer)
    engine = SearchEngine(Parser(), analyzer, index, evaluator)
    return engine, index, evaluator


def make_engine() -> SearchEngine:
    return make_components()[0]
