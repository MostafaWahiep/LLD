from search_engine.analysis import Analyzer
from search_engine.indexing.index import Index
from search_engine.querying.evaluator import QueryEvaluator
from search_engine.querying.parser import Parser
from search_engine.querying.queries import PhraseQuery, PrefixQuery, Query, TermQuery
from search_engine.results import SearchResult
from typing import Optional

class SearchEngine:
    def __init__(self, parser, analyzer, index, evaluator):
        self._parser: Parser = parser
        self._analyzer: Analyzer = analyzer
        self._index: Index = index
        self._evaluator: QueryEvaluator = evaluator
    
    def add(self, document_id: str, text: str) -> None:
        terms: list[str] = self._analyzer.analyze(text)
        self._index.add(document_id, text, terms)

    def search(self, term: str) -> list[str]:
        query: Query = TermQuery(term)
        return self._query(query)
    
    def query(self, query_str: str) -> list[str]:
        query = self._parser.parse(query_str)
        return self._query(query)

    def ranked_search(
        self,
        query: str,
        limit: Optional[int]  = None,
    ) -> list[SearchResult]:
        return self._evaluator.evaluate_ranked(query, limit)

    def prefix_search(self, prefix: str) -> list[str]:
        query: Query = PrefixQuery(prefix)
        return self._query(query)
    
    def phrase_search(self, phrase: str) -> list[str]:
        query: Query = PhraseQuery(phrase)
        return self._query(query)

    def delete(self, document_id: str) -> None:
        self._index.delete_document(document_id)

    def flush(self) -> None:
        self._index.flush()

    def merge_segments(self) -> None:
        self._index.merge_segments()
    
    def _query(self, query: Query) -> list[str]:
        matches = self._evaluator.evaluate(query)
        return sorted(ref.external_id for ref in matches)
