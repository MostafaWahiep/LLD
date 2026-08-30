from index import InvertedIndex
from text_analyzer import Analyzer
from query import AndQuery, NotQuery, OrQuery, Query, QueryVisitor, TermQuery
from search_result import SearchResult
from math import log
from typing import Optional
from collections import defaultdict

class QueryEvaluator(QueryVisitor):
    def __init__(
        self,
        index: InvertedIndex,
        analyzer: Analyzer,
    ):
        self._index = index
        self._analyzer = analyzer

    def evaluate(self, query: Query) -> set[str]:
        return query.accept(self)

    def visit_term(self, query: TermQuery) -> set[str]:
        terms: list[str] = self._analyzer.analyze(query.term)
        
        if len(terms) != 1:
            raise ValueError(
                "A term query must contain exactly one searchable word"
            )

        return self._index.postings(terms[0])

    def visit_not(self, query: NotQuery) -> set[str]:
        return set(self._index.document_ids()).difference(query.child.accept(self))
        

    def visit_and(self, query: AndQuery) -> set[str]:
        results = [child.accept(self) for child in query.children]
        return set.intersection(*results)

    def visit_or(self, query: OrQuery) -> set[str]:
        results = [child.accept(self) for child in query.children]
        return set.union(*results)

    def evaluate_ranked(self, query: str, limit: Optional[int] = None) -> list[SearchResult]:
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        terms: list[str] = self._analyzer.analyze(query)
        corpus_size = len(self._index.document_ids())
        document_scores: dict[str, float] = defaultdict(float)

        for term in terms:
            posting = self._index.get_posting(term)
            document_frequency = posting.document_frequency()

            for document_id in posting.document_ids():
                document_scores[document_id] += self.calculate_score(
                    frequency=posting.frequency(document_id),
                    num_docs_appearing=document_frequency,
                    corpus_size=corpus_size,
                )

        results = [
            SearchResult(document_id, score)
            for document_id, score in document_scores.items()
        ]

        results.sort(key=lambda result: (-result.score, result.document_id))

        if limit is not None:
            return results[:limit]

        return results

    def calculate_score(
            self,
            frequency: int,
            num_docs_appearing: int,
            corpus_size: int
        ) -> float:
        term_frequency = 1 + log(frequency)
        inverse_document_frequency = log((1+corpus_size) / (1+num_docs_appearing)) + 1
        return term_frequency * inverse_document_frequency
