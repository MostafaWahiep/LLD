from query_parser import Parser
from text_analyzer import Analyzer
from index import InvertedIndex
from evaluator import QueryEvaluator
from search_result import SearchResult
from query import Query, TermQuery
from typing import Optional

class SearchEngine:
    def __init__(self, parser, analyzer, index, evaluator):
        self._parser: Parser = parser
        self._analyzer: Analyzer = analyzer
        self._index: InvertedIndex = index
        self._evaluator: QueryEvaluator = evaluator
    
    def add(self, document_id: str, text: str) -> None:
        terms: list[str] = self._analyzer.analyze(text)
        self._index.add(document_id, text, terms)

    def search(self, term: str) -> list[str]:
        query: Query = TermQuery(term)
        return sorted(self._evaluator.evaluate(query))
    
    def query(self, query_str: str) -> list[str]:
        query = self._parser.parse(query_str)
        return sorted(self._evaluator.evaluate(query))

    def ranked_search(
        self,
        query: str,
        limit: Optional[int]  = None,
    ) -> list[SearchResult]:
        return self._evaluator.evaluate_ranked(query, limit)
